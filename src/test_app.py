import json
import os
import sys
import unittest
from pathlib import Path

import pymupdf

from app import handler


class PDFGeneratorAPITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def test_empty_event_param(self):
        self.call_lambda_and_assert_errors({}, "Invalid 'event' parameter", "'event' parameter is null or empty")

    def test_http_method(self):
        error_title = 'Invalid http method'
        payload = self.load_api_gateway_payload()

        payload['httpMethod'] = 'GET'
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'POST' method is allowed, 'GET' given",
            405
        )

        del payload['httpMethod']
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'POST' method is allowed, null or empty given",
            405
        )

    def test_missing_header(self):
        payload = self.load_api_gateway_payload()
        payload['headers'] = None
        self.call_lambda_and_assert_errors(payload, 'Invalid header block', 'header block is missing')

    def test_content_type_header(self):
        error_title = 'Invalid Content-Type header'
        payload = self.load_api_gateway_payload()

        payload['headers']['Content-Type'] = 'text/html'
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'application/json' Content-Type header is allowed, 'text/html' given",
            415
        )

        del payload['headers']['Content-Type']
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'application/json' Content-Type header is allowed, null or empty given",
            415
        )

    def test_accept_header(self):
        error_title = 'Invalid Accept header'
        payload = self.load_api_gateway_payload()

        payload['headers']['Accept'] = 'text/html'
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'application/pdf' Accept header is allowed, 'text/html' given",
            406
        )

        del payload['headers']['Accept']
        self.call_lambda_and_assert_errors(
            payload,
            error_title,
            "only the 'application/pdf' Accept header is allowed, null or empty given",
            406
        )

    def test_x_caller_service_header(self):
        payload = self.load_api_gateway_payload()
        payload['headers']['X-Caller-Service'] = None
        self.call_lambda_and_assert_errors(
            payload,
            'Invalid X-caller-service header',
            "'X-caller-service' header is null or empty",
        )

    def test_body(self):
        payload = self.load_api_gateway_payload()

        payload['body'] = None
        self.call_lambda_and_assert_errors(payload, 'Invalid body', 'body is null or empty')

        body = {'data': {'attribute': {}}}
        payload['body'] = json.dumps(body)
        self.call_lambda_and_assert_errors(payload, 'JSON API Structure', "expected 'data.attributes.htmlBody'")

        body = {'data': {'attributes': {}}}
        payload['body'] = json.dumps(body)
        self.call_lambda_and_assert_errors(
            payload,
            'Invalid payload',
            "one of 'data.attributes.htmlBody' or 'data.attributes.htmlUrl' must be set"
        )

    def test_invalid_url(self):
        payload = self.load_api_gateway_payload()
        body = {'data': {'attributes': {'htmlUrl': 'print/my/html'}}}
        payload['body'] = json.dumps(body)
        self.call_lambda_and_assert_errors(payload, 'URL Content', "'data.attributes.htmlUrl' contain invalid URL", 422)

    def test_pdf_creation(self):
        payload = self.load_api_gateway_payload()

        body = {'data': {'attributes': {'htmlUrl': 'https://www.google.it'}}}
        payload['body'] = json.dumps(body)
        response = handler(payload, None)
        self.assertEqual(200, response['statusCode'])
        self.assertTrue(response['data']['attributes']['sharedFilePath'])

        html_content = """
        <html>
        <head>
            <style>
                h2 { color: green; text-align: left; }
            </style>
        </head>
        <body>
            <h1 style="color: red;">Hello, PDF!</h1>
            <h2>This is a subheading with inline style</h2>
            <p>This is a paragraph.</p>
        </body>
        </html>
        """
        body = {'data': {'attributes': {'htmlBody': html_content}}}
        payload['body'] = json.dumps(body)
        response = handler(payload, None)
        self.assertEqual(200, response['statusCode'])

        expected_pdf_text = 'Hello, PDF!\nThis is a subheading with inline style\nThis is a paragraph.\n'
        generated_pdf_text = ''
        with pymupdf.open(f"/test/multidialogo-api/{response['data']['attributes']['sharedFilePath']}") as pdf:
            for page in pdf:
                generated_pdf_text += page.get_text()
        self.assertEqual(expected_pdf_text, generated_pdf_text)

    def call_lambda_and_assert_errors(self, payload: dict, error_title: str, error_detail: str, error_code: int = 400):
        response = handler(payload, None)
        self.assertEqual(error_code, response['statusCode'])
        error = json.loads(response['body'])['error']
        self.assertEqual(error_title, error['title'])
        self.assertEqual(error_detail, error['detail'])

    def load_api_gateway_payload(self):
        return json.loads(Path('api-gateway-payload-template.json').read_text())
