import unittest
from unittest.mock import mock_open, patch

import pymupdf
from flask import Response

from app import app, logger


class PDFGeneratorAPITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True
        cls.route = '/download'

    def setUp(self):
        logger.disabled = True
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Caller-Service': 'MULTIDIALOGO-API',
        }

    def test_health_check(self):
        health_check_route = '/health-check'
        response = self.app.get(health_check_route)
        self.assertEqual(200, response.status_code)
        self.assertEqual(b'Hello, World!', response.data)

        # This test is not so necessary.
        response = self.app.post(health_check_route)
        self.assert_errors(
            response,
            'Invalid http method',
            "only the 'GET' method is allowed, 'POST' given",
            405
        )

    def test_http_method(self):
        response = self.app.get(self.route)
        self.assert_errors(
            response,
            'Invalid http method',
            "only the 'POST' method is allowed, 'GET' given",
            405
        )

    def test_content_type_header(self):
        error_title = 'Invalid Content-Type header'
        response = self.app.post(self.route, headers={'Content-Type': 'text/html'})
        self.assert_errors(
            response,
            error_title,
            "only the 'application/json' Content-Type header is allowed, 'text/html' given",
            415
        )

        response = self.app.post(self.route)
        self.assert_errors(
            response,
            error_title,
            "only the 'application/json' Content-Type header is allowed, null or empty given",
            415
        )

    def test_accept_header(self):
        error_title = 'Invalid Accept header'

        self.headers['Accept'] = 'text/html'
        response = self.app.post(self.route, headers=self.headers)
        self.assert_errors(
            response,
            error_title,
            "only the 'application/json' Accept header is allowed, 'text/html' given",
            406
        )

        del self.headers['Accept']
        response = self.app.post(self.route, headers=self.headers)
        self.assert_errors(
            response,
            error_title,
            "only the 'application/json' Accept header is allowed, null or empty given",
            406
        )

    def test_x_caller_service_header(self):
        self.headers['X-Caller-Service'] = ''
        response = self.app.post(self.route, headers=self.headers)
        self.assert_errors(
            response,
            'Invalid X-Caller-Service header',
            "'X-Caller-Service' header is null or empty"
        )

    def test_body(self):
        response = self.app.post(self.route, headers=self.headers, json={})
        self.assert_errors(response, 'Invalid body', 'body is null or empty')

        response = self.app.post(self.route, headers=self.headers, json={'data': {'house': {}}})
        self.assert_errors(response, 'JSON API Structure', "expected 'data.attributes.htmlBody'")

        response = self.app.post(self.route, headers=self.headers, json={'data': {'attributes': {}}})
        self.assert_errors(
            response,
            'Invalid payload',
            "one of 'data.attributes.htmlBody' or 'data.attributes.htmlUrl' must be set"
        )

    def test_invalid_url(self):
        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'print/my/html'}}}
        )
        self.assert_errors(response, 'URL Content', "'data.attributes.htmlUrl' contain invalid URL", 422)

        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': '//[oops'}}}
        )
        self.assert_errors(response, 'URL Content', "'data.attributes.htmlUrl' contain invalid URL", 422)

        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'http://sito.molto/bello'}}}
        )
        self.assert_errors(
            response,
            'Internal Server Error',
            'error generating PDF: wkhtmltopdf reported an error:\nExit with code 1 due to network error: HostNotFoundError\n',
            500
        )

    @patch('builtins.open', new_callable=mock_open)
    def test_file_write_exception(self, mock_file):
        mock_file().write.side_effect = IOError('write error')
        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'https://www.google.it'}}}
        )
        self.assert_errors(
            response,
            'Internal Server Error',
            'error saving PDF: write error',
            500
        )

    def test_pdf_creation(self):
        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'https://www.google.it'}}}
        )
        self.assertEqual(200, response.status_code)
        shared_file_path = response.json['data']['attributes']['sharedFilePath']
        self.assertTrue(shared_file_path)

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
        response = self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlBody': html_content}}}
        )
        self.assertEqual(200, response.status_code)

        expected_pdf_text = 'Hello, PDF!\nThis is a subheading with inline style\nThis is a paragraph.\n'
        generated_pdf_text = ''
        shared_file_path = response.json['data']['attributes']['sharedFilePath']
        with pymupdf.open(f"/test/multidialogo-api/{shared_file_path}") as pdf:
            for page in pdf:
                generated_pdf_text += page.get_text()
        self.assertEqual(expected_pdf_text, generated_pdf_text)

    def assert_errors(self, response: Response, error_title: str, error_detail: str, error_code: int = 400):
        self.assertEqual(error_code, response.status_code)
        error = response.json['error']
        self.assertEqual(error_title, error['title'])
        self.assertEqual(error_detail, error['detail'])
