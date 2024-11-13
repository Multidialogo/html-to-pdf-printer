from datetime import datetime
from hashlib import md5
from logging import getLogger, INFO
from os import path, environ, makedirs
from urllib.parse import urlparse

import pdfkit
from flask import Flask, request

# FIXME: Aggiungere i log!!!!!
# https://morrislin1017.medium.com/flask-use-watchtower-to-stream-log-to-aws-cloudwatch-913477022c21
# https://binli.hashnode.dev/send-logs-to-aws-cloudwatch-in-python


app = Flask(__name__)

pdfkit_config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')


@app.route('/', methods=['GET'])
def hello():
    return "Hello, World!"


@app.route('/download', methods=['POST'])
def convert():
    content_type = request.headers.get('content-type')

    if not content_type or content_type != 'application/json':
        wrong_value = f"'{content_type}'" if content_type else 'null or empty'
        return format_error_message('Invalid Content-Type header',
                                    f"only the 'application/json' Content-Type header is allowed, {wrong_value} given",
                                    415)

    accept_header = request.headers.get('accept')

    if not accept_header or accept_header != 'application/json':
        wrong_value = f"'{accept_header}'" if accept_header else 'null or empty'
        return format_error_message('Invalid Accept header',
                                    f"only the 'application/json' Accept header is allowed, {wrong_value} given", 406)

    service_dir = request.headers.get('x-caller-service')

    if service_dir:
        service_dir = service_dir.lower().strip()

    if not service_dir:
        return format_error_message('Invalid X-Caller-Service header',
                                    "'X-Caller-Service' header is null or empty")

    body = request.get_json()

    if not body:
        return format_error_message('Invalid body', 'body is null or empty')

    if not body or 'data' not in body or 'attributes' not in body['data']:
        return format_error_message('JSON API Structure', "expected 'data.attributes.htmlBody'")

    attributes = body['data']['attributes']

    html_body = attributes.get('htmlBody')
    html_url = attributes.get('htmlUrl')

    if not html_body and not html_url:
        return format_error_message('Invalid payload',
                                    "one of 'data.attributes.htmlBody' or 'data.attributes.htmlUrl' must be set")

    valid_url = True
    if html_url:
        try:
            result = urlparse(html_url)
            valid_url = all([result.scheme, result.netloc])
        except ValueError:
            valid_url = False
    if not valid_url:
        return format_error_message('URL Content', f"'data.attributes.htmlUrl' contain invalid URL", 422)

    pdf_bytes = b''
    try:
        if html_body:
            pdf_bytes = pdfkit.from_string(html_body, False, configuration=pdfkit_config)
        elif html_url:
            pdf_bytes = pdfkit.from_url(html_url, False, configuration=pdfkit_config)
    except Exception as e:
        return format_error_message("Internal Server Error", f"error generating PDF: {e}", 500)

    efs_mount_path = environ.get('EFS_MOUNT_PATH').rstrip('/') + '/'
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
            return format_error_message("Internal Server Error", f"error saving PDF: {e}", 500)

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
    method_allowed = 'GET' if request.path == '/' else 'POST'
    return format_error_message(
        'Invalid http method',
        f"only the '{method_allowed}' method is allowed, {wrong_value} given",
        405
    )


def format_error_message(title: str, detail: str, code: int = 400):
    return {"error": {"title": title, "detail": detail}}, code
