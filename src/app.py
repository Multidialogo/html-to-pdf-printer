import atexit
import os
import shutil
import time
from datetime import datetime, timedelta
from hashlib import md5
from logging import basicConfig, getLogger, INFO
from os import path, environ, makedirs, listdir
from threading import Lock
from urllib.parse import urlparse

from flask import Flask, request
from playwright.sync_api import sync_playwright

app = Flask(__name__)

basicConfig(level=INFO)
logger = getLogger(__name__)

DEFAULT_CLEANUP_INTERVAL_SECONDS = 21600
DEFAULT_CLEANUP_LOCK_TTL_SECONDS = 1800
DEFAULT_BROWSER_MAX_AGE_SECONDS = 86400

last_cleanup_attempt_ts = 0.0
runtime_lock = Lock()
playwright_instance = None
browser_instance = None
browser_started_at = 0.0


@app.route('/health-check', methods=['GET'])
def hello():
    return "Hello, World!"


@app.route('/download', methods=['POST'])
def convert():
    efs_mount_path = environ.get('EFS_MOUNT_PATH').rstrip('/') + '/'
    try_cleanup_if_due(efs_mount_path)

    # Process the request.
    content_type = request.headers.get('content-type')

    if not content_type or content_type != 'application/json':
        wrong_value = f"'{content_type}'" if content_type else 'null or empty'
        return format_error_message('Invalid Content-Type header',
                                    f"only the 'application/json' Content-Type header is allowed, {wrong_value} given",
                                    code=415)

    accept_header = request.headers.get('accept')

    if not accept_header or accept_header != 'application/json':
        wrong_value = f"'{accept_header}'" if accept_header else 'null or empty'
        return format_error_message('Invalid Accept header',
                                    f"only the 'application/json' Accept header is allowed, {wrong_value} given",
                                    code=406)

    service_dir = request.headers.get('x-caller-service')

    if service_dir:
        service_dir = service_dir.lower().strip()

    if not service_dir:
        return format_error_message('Invalid X-Caller-Service header',
                                    "'X-Caller-Service' header is null or empty")

    body = request.get_json()

    if not body:
        return format_error_message('Invalid body', 'body is null or empty')

    if 'data' not in body or 'attributes' not in body['data']:
        return format_error_message('JSON API Structure', "expected 'data.attributes.htmlBody'", body)

    attributes = body['data']['attributes']

    html_body = attributes.get('htmlBody')
    html_url = attributes.get('htmlUrl')

    if not html_body and not html_url:
        return format_error_message('Invalid payload',
                                    "one of 'data.attributes.htmlBody' or 'data.attributes.htmlUrl' must be set",
                                    body)

    valid_url = True
    if html_url:
        try:
            result = urlparse(html_url)
            valid_url = all([result.scheme, result.netloc])
        except ValueError:
            valid_url = False
    if not valid_url:
        return format_error_message('URL Content', f"'data.attributes.htmlUrl' contain invalid URL", body, 422)

    pdf_bytes = b''
    browser_context = None
    try:
        browser = get_browser()
        browser_context = browser.new_context()
        page = browser_context.new_page()

        try:
            if html_body:
                page.set_content(html_body)
            elif html_url:
                page.goto(html_url)
        except Exception as e:
            return format_error_message("Internal Server Error", f"error while setting content or navigating: {e}",
                                        body, 500)

        try:
            page.evaluate('() => document.fonts.ready')
            pdf_bytes = page.pdf(format='A4', print_background=True)
        except Exception as e:
            return format_error_message("Internal Server Error", f"error generating PDF: {e}", body, 500)
    except Exception as e:
        return format_error_message("Internal Server Error", f"error initializing browser: {e}", body, 500)
    finally:
        if browser_context:
            try:
                browser_context.close()
            except Exception as e:
                logger.warning(f"error while closing browser context: {e}")

    service_path = path.join(efs_mount_path, service_dir)

    file_name = md5(pdf_bytes, usedforsecurity=False).hexdigest()
    date_now = datetime.now()
    return_path = path.join(date_now.strftime("%Y"), date_now.strftime("%m"), date_now.strftime("%d"),
                            file_name[0])

    makedirs(path.join(service_path, return_path), exist_ok=True)

    return_path = path.join(return_path, f'{file_name}.pdf')
    pdf_file_path = path.join(service_path, return_path)

    if not path.exists(pdf_file_path):
        try:
            with open(pdf_file_path, 'wb') as file:
                file.write(pdf_bytes)
        except IOError as e:
            return format_error_message("Internal Server Error", f"error saving PDF: {e}", body, 500)

    return {
        'data': {
            'attributes': {
                'sharedFilePath': return_path
            }
        }
    }


@app.errorhandler(405)
def method_not_allowed(e):
    wrong_value = f"'{request.method}'" if request.method else 'null or empty'
    method_allowed = 'POST' if request.path == '/download' else 'GET'
    return format_error_message(
        'Invalid http method',
        f"only the '{method_allowed}' method is allowed, {wrong_value} given",
        code=405
    )


def format_error_message(title: str, detail: str, payload: dict = None, code: int = 400):
    log_msg = f'The received request has generated errors: {detail}'

    if payload:
        log_msg = f'{log_msg} - PAYLOAD: {payload}'

    if code > 499:
        logger.critical(log_msg)
    else:
        logger.error(log_msg)

    return {"error": {"title": title, "detail": detail}}, code


def delete_directory(dir_path: str):
    try:
        shutil.rmtree(dir_path)
        logger.info(f"The directory '{dir_path}' was removed successfully.")
    except Exception as e:
        logger.warning(f"Error while deleting the directory '{dir_path}': {e}.")


def get_int_env(name: str, default: int) -> int:
    value = environ.get(name)

    if value is None:
        return default

    try:
        parsed_value = int(value)
        if parsed_value < 0:
            raise ValueError()
        return parsed_value
    except ValueError:
        logger.warning(f"Invalid value '{value}' for env '{name}', using default '{default}'.")
        return default


def try_cleanup_if_due(efs_mount_path: str):
    global last_cleanup_attempt_ts

    interval_seconds = get_int_env('CLEANUP_INTERVAL_SECONDS', DEFAULT_CLEANUP_INTERVAL_SECONDS)
    now_ts = time.time()

    with runtime_lock:
        if interval_seconds > 0 and (now_ts - last_cleanup_attempt_ts) < interval_seconds:
            return
        # Update attempt timestamp also for skipped/failed cleanups to avoid aggressive retries.
        last_cleanup_attempt_ts = now_ts

    lock_file_path = path.join(efs_mount_path, '.cleanup.lock')
    lock_ttl_seconds = get_int_env('CLEANUP_LOCK_TTL_SECONDS', DEFAULT_CLEANUP_LOCK_TTL_SECONDS)
    lock_acquired = False

    try:
        lock_acquired = acquire_cleanup_lock(lock_file_path, lock_ttl_seconds)
        if not lock_acquired:
            return

        cleanup_old_files(efs_mount_path)
    except Exception as e:
        logger.warning(f"Error while running scheduled cleanup: {e}")
    finally:
        if lock_acquired:
            release_cleanup_lock(lock_file_path)


def cleanup_old_files(efs_mount_path: str):
    cutoff_date = datetime.now() - timedelta(days=30)
    for service in listdir(efs_mount_path):
        service_path = path.join(efs_mount_path, service)
        if path.isdir(service_path):
            for year in listdir(service_path):
                if not year.isdigit():
                    continue

                year_path = path.join(service_path, year)

                if path.isdir(year_path):
                    int_year = int(year)
                    if int_year < cutoff_date.year:
                        delete_directory(year_path)
                    elif int_year == cutoff_date.year:
                        for month in listdir(year_path):
                            if not month.isdigit():
                                continue

                            month_path = path.join(year_path, month)

                            if path.isdir(month_path):
                                int_month = int(month)
                                if int_month < cutoff_date.month:
                                    delete_directory(month_path)
                                elif int_month == cutoff_date.month:
                                    for day in listdir(month_path):
                                        if not day.isdigit():
                                            continue

                                        day_path = path.join(month_path, day)

                                        if path.isdir(day_path):
                                            if int(day) < cutoff_date.day:
                                                delete_directory(day_path)


def acquire_cleanup_lock(lock_file_path: str, lock_ttl_seconds: int) -> bool:
    ensure_stale_lock_is_removed(lock_file_path, lock_ttl_seconds)

    try:
        fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as lock_file:
            lock_file.write(str(int(time.time())))
        return True
    except FileExistsError:
        return False
    except OSError as e:
        logger.warning(f"Error while acquiring cleanup lock '{lock_file_path}': {e}.")
        return False


def ensure_stale_lock_is_removed(lock_file_path: str, lock_ttl_seconds: int):
    if lock_ttl_seconds <= 0:
        return

    try:
        lock_age_seconds = time.time() - path.getmtime(lock_file_path)
    except FileNotFoundError:
        return
    except OSError as e:
        logger.warning(f"Error while checking cleanup lock age '{lock_file_path}': {e}.")
        return

    if lock_age_seconds <= lock_ttl_seconds:
        return

    try:
        os.remove(lock_file_path)
        logger.info(f"Removed stale cleanup lock '{lock_file_path}'.")
    except FileNotFoundError:
        return
    except OSError as e:
        logger.warning(f"Error while removing stale cleanup lock '{lock_file_path}': {e}.")


def release_cleanup_lock(lock_file_path: str):
    try:
        os.remove(lock_file_path)
    except FileNotFoundError:
        return
    except OSError as e:
        logger.warning(f"Error while releasing cleanup lock '{lock_file_path}': {e}.")


def get_browser():
    global playwright_instance
    global browser_instance
    global browser_started_at

    with runtime_lock:
        if browser_instance:
            max_age = get_int_env('BROWSER_MAX_AGE_SECONDS', DEFAULT_BROWSER_MAX_AGE_SECONDS)
            if max_age > 0 and (time.time() - browser_started_at) >= max_age:
                logger.info("Browser max age reached, restarting.")
                _close_browser_unlocked()
            else:
                return browser_instance

        playwright_instance = sync_playwright().start()
        browser_instance = playwright_instance.chromium.launch(headless=True)
        browser_started_at = time.time()
        return browser_instance


def close_browser():
    with runtime_lock:
        _close_browser_unlocked()


def _close_browser_unlocked():
    global playwright_instance
    global browser_instance
    global browser_started_at

    if browser_instance:
        try:
            browser_instance.close()
        except Exception as e:
            logger.warning(f"Error while closing browser instance: {e}.")
        browser_instance = None

    if playwright_instance:
        try:
            playwright_instance.stop()
        except Exception as e:
            logger.warning(f"Error while stopping playwright instance: {e}.")
        playwright_instance = None

    browser_started_at = 0.0


atexit.register(close_browser)
