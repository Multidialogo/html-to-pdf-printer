from logging import getLogger, INFO
from os import path, environ, makedirs
from json import loads, dumps
from hashlib import md5
from datetime import datetime
from urllib.parse import urlparse
# server ancora? from venv import create

import pdfkit


class App:
    LOGGER = getLogger()
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')

    def __init__(self):
        self.LOGGER.setLevel(INFO)  # Set level for AWS CloudWatch, doesn't affect Develop/local environment.

    def process(self, event: dict) -> dict:

        if not event:
            return self.error_response("Invalid 'event' parameter",
                                       "'event' parameter is null or empty")

        http_method = event.get('httpMethod')

        if not http_method or http_method != 'POST':
            wrong_value = f"'{http_method}'" if http_method else 'null or empty'
            return self.error_response('Invalid http method',
                                       f"only the 'POST' method is allowed, {wrong_value} given",
                                       event,
                                       405)

        headers = event.get('headers')

        if not headers:
            return self.error_response('Invalid header block',
                                       'header block is missing', event)

        content_type = headers.get('Content-Type')

        if not content_type or content_type != 'application/json':
            wrong_value = f"'{content_type}'" if content_type else 'null or empty'
            return self.error_response('Invalid Content-Type header',
                                       f"only the 'application/json' Content-Type header is allowed, {wrong_value} given",
                                       event,
                                       415)

        accept_header = headers.get('Accept')

        if not accept_header or accept_header != 'application/json':
            wrong_value = f"'{accept_header}'" if accept_header else 'null or empty'
            return self.error_response('Invalid Accept header',
                                       f"only the 'application/json' Accept header is allowed, {wrong_value} given",
                                       event,
                                       406)

        service_dir = headers.get('X-Caller-Service')

        if service_dir:
            service_dir = service_dir.lower().strip()

        if not service_dir:
            return self.error_response('Invalid X-caller-service header',
                                       "'X-caller-service' header is null or empty",
                                       event)

        body = event.get('body')

        if not body:
            return self.error_response('Invalid body',
                                       'body is null or empty',
                                       event)

        body = loads(event['body'])

        if not body or 'data' not in body or 'attributes' not in body['data']:
            return self.error_response('JSON API Structure',
                                       "expected 'data.attributes.htmlBody'",
                                       event)

        attributes = body['data']['attributes']

        html_body = attributes.get('htmlBody')
        html_url = attributes.get('htmlUrl')

        if not html_body and not html_url:
            return self.error_response('Invalid payload',
                                       "one of 'data.attributes.htmlBody' or 'data.attributes.htmlUrl' must be set",
                                       event)

        valid_url = True
        if html_url:
            try:
                result = urlparse(html_url)
                valid_url = all([result.scheme, result.netloc])
            except AttributeError:
                valid_url = False
        if not valid_url:
            return self.error_response('URL Content',
                                       f"'data.attributes.htmlUrl' contain invalid URL",
                                       event,
                                       422)

        pdf_bytes = b''
        try:
            if html_body:
                pdf_bytes = pdfkit.from_string(html_body, False, configuration=self.PDFKIT_CONFIG)
            elif html_url:
                pdf_bytes = pdfkit.from_url(html_url, False, configuration=self.PDFKIT_CONFIG)
        except Exception as e:
            return self.error_response("Internal Server Error",
                                       f"error generating PDF: {e}",
                                       event,
                                       500)


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
                return self.error_response("Internal Server Error",
                                           f"error saving PDF: {e}",
                                           event,
                                           500)

        return self.create_response('',200)

    def create_response(self, body, code: int) -> dict:
        return {
            'statusCode': code,
            'headers': {'Content-Type': 'application/json'},
            'isBase64Encoded': False,
            'body': dumps(body) if isinstance(body, dict) else body
        }

    def error_response(self, title: str = None, detail: str = None, event: dict = None, code: int = 400) -> dict:
        log_msg = f'The received request has generated errors: {detail}'

        if event:
            log_msg = f'{log_msg} - API GATEWAY PAYLOAD: {event}'

        if code > 499:
            self.LOGGER.critical(log_msg)
        else:
            self.LOGGER.error(log_msg)

        body = {"error": {"title": title, "detail": detail}}
        return self.create_response(body, code)


def handler(event: dict, context):
    app = App()
    return app.process(event)
