import random
import string
import unittest
from datetime import datetime, timedelta
from hashlib import md5
from os import path, environ, makedirs
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
        efs_mount_path = environ.get('EFS_MOUNT_PATH').rstrip('/') + '/'
        self.service_path = f"{efs_mount_path}{self.headers['X-Caller-Service'].lower()}"

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
            'error while setting content or navigating: Page.goto: net::ERR_NAME_NOT_RESOLVED at http://sito.molto/bello\nCall log:\n  - navigating to "http://sito.molto/bello", waiting until "load"\n',
            500
        )

    @patch('app.open', new_callable=mock_open)
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
        with pymupdf.open(f'{self.service_path}/{shared_file_path}') as pdf:
            for page in pdf:
                generated_pdf_text += page.get_text()
        self.assertEqual(expected_pdf_text, generated_pdf_text)

    def test_pdf_deleting(self):
        today_date = datetime.now()
        cutoff_date = today_date - timedelta(days=30)

        old_year_date = f'{cutoff_date.year - 1}/{cutoff_date.month}/{cutoff_date.day}'
        old_year_date = self.create_random_pdf(old_year_date)
        self.assertTrue(path.isfile(old_year_date))

        old_month_date = f'{cutoff_date.year}/{cutoff_date.month - 1}/{cutoff_date.day}'
        old_month_date = self.create_random_pdf(old_month_date)
        self.assertTrue(path.isfile(old_month_date))

        old_day_date = f'{cutoff_date.year}/{cutoff_date.month}/{cutoff_date.day - 1}'
        old_day_date = self.create_random_pdf(old_day_date)
        self.assertTrue(path.isfile(old_day_date))

        actual_date_file_path = f'{today_date.year}/{today_date.month}/{today_date.day}'
        actual_date_file_path = self.create_random_pdf(actual_date_file_path)
        self.assertTrue(path.isfile(actual_date_file_path))

        self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'https://www.google.it'}}}
        )

        self.assertFalse(path.isfile(old_year_date))
        self.assertFalse(path.isfile(old_month_date))
        self.assertFalse(path.isfile(old_day_date))
        self.assertTrue(path.isfile(actual_date_file_path))

    @patch('shutil.rmtree')
    def test_error_during_pdf_deleting(self, mock_rmtree):
        today_date = datetime.now()
        cutoff_date = today_date - timedelta(days=30)

        old_year_date = f'{cutoff_date.year - 1}/{cutoff_date.month}/{cutoff_date.day}'
        old_year_date = self.create_random_pdf(old_year_date)
        self.assertTrue(path.isfile(old_year_date))

        mock_rmtree.side_effect = OSError('delete error')
        self.app.post(
            self.route,
            headers=self.headers,
            json={'data': {'attributes': {'htmlUrl': 'https://www.google.it'}}}
        )
        self.assertTrue(path.isfile(old_year_date))

    def assert_errors(self, response: Response, error_title: str, error_detail: str, error_code: int = 400):
        self.assertEqual(error_code, response.status_code)
        error = response.json['error']
        self.assertEqual(error_title, error['title'])
        self.assertEqual(error_detail, error['detail'])

    def create_random_pdf(self, date_path: str, length: int = 30):
        letters = string.ascii_letters + string.digits + string.punctuation
        contents = ''.join(random.choice(letters) for _ in range(length))
        file_name = md5(contents.encode('utf-8'), usedforsecurity=False).hexdigest()
        random_path = f'{self.service_path}/{date_path}/{file_name[0]}'
        makedirs(random_path)
        random_file_path = f'{random_path}/{file_name}.pdf'
        with open(random_file_path, 'w') as file:
            file.write(contents)
        return random_file_path
