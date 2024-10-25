import io
import json
import unittest

from pdfminer.high_level import extract_text

from app import app  # Import the Flask app from your app.py


class PDFGeneratorAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up the test client and expectations directory."""
        self.app = app.test_client()
        self.app.testing = True

    # def test_convert_with_styles(self):
    #     """Test PDF generation with inline, tag, and external CSS."""
    #     html_content = """
    #     <html>
    #     <head>
    #         <link rel="stylesheet" type="text/css" href="http://127.0.0.1:5000/static/styles.css">
    #         <style>
    #             h2 { color: green; text-align: left; }
    #         </style>
    #     </head>
    #     <body>
    #         <h1 style="color: red;">Hello, PDF!</h1>
    #         <h2>This is a subheading with inline style</h2>
    #         <p>This is a paragraph.</p>
    #     </body>
    #     </html>
    #     """
    #
    #     expected_pdf_text = 'Hello,\tPDF!\n\nThis\tis\ta\tsubheading\twith\tinline\tstyle\n\nThis\tis\ta\tparagraph.\n\n\x0c'
    #
    #     response = self.app.post(
    #         '/convert',
    #         headers={
    #             'Content-Type': 'application/json',
    #             'Accept': 'application/pdf'
    #         },
    #         data=json.dumps({
    #             "data": {
    #                 "attributes": {
    #                     "htmlBody": html_content,
    #                     "outputFilename": "example.pdf"
    #                 }
    #             }
    #         })
    #     )
    #
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.content_type, 'application/pdf')
    #
    #     self.assertEqual(expected_pdf_text, extract_text(io.BytesIO(response.data)))
    #
    # def test_invalid_content_type(self):
    #     """Test response for invalid Content-Type."""
    #     response = self.app.post(
    #         '/convert',
    #         headers={'Content-Type': 'text/plain'},
    #         data=json.dumps({"data": {"attributes": {"htmlBody": "<html></html>"}}})
    #     )
    #     self.assertEqual(response.status_code, 415)
    #     self.assertIn('Content-Type must be application/json', response.get_data(as_text=True))
    #
    # def test_invalid_accept_header(self):
    #     """Test response for invalid Accept header."""
    #     response = self.app.post(
    #         '/convert',
    #         headers={
    #             'Content-Type': 'application/json',
    #             'Accept': 'text/html'
    #         },
    #         data=json.dumps({
    #             "data": {
    #                 "attributes": {
    #                     "htmlBody": "<html><body><h1>Hello, PDF!</h1></body></html>"
    #                 }
    #             }
    #         })
    #     )
    #     self.assertEqual(response.status_code, 406)
    #     self.assertIn('Accept header must be application/pdf', response.get_data(as_text=True))
    #
    # def test_invalid_json_structure(self):
    #     """Test response for invalid JSON structure."""
    #     response = self.app.post(
    #         '/convert',
    #         headers={'Content-Type': 'application/json'},
    #         data=json.dumps({"invalid_key": "value"})
    #     )
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn('Invalid JSON API structure. Expected', response.get_data(as_text=True))
    #
    # def test_invalid_html(self):
    #     """Test response for invalid HTML content."""
    #     response = self.app.post(
    #         '/convert',
    #         headers={
    #             'Content-Type': 'application/json',
    #             'Accept': 'application/pdf'
    #         },
    #         data=json.dumps({
    #             "data": {
    #                 "attributes": {
    #                     "htmlBody": "<html><body><h1>Invalid HTML"
    #                 }
    #             }
    #         })
    #     )
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn('Invalid HTML content', response.get_data(as_text=True))
    #
    # def test_missing_html_body(self):
    #     """Test response for missing htmlBody attribute."""
    #     response = self.app.post(
    #         '/convert',
    #         headers={'Content-Type': 'application/json'},
    #         data=json.dumps({
    #             "data": {
    #                 "attributes": {}
    #             }
    #         })
    #     )
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn('Invalid JSON API structure. Expected', response.get_data(as_text=True))

    def test_empty_html_body(self):
        """Test response for empty htmlBody attribute."""
        response = self.app.post(
            '/convert',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/pdf'
            },
            data=json.dumps({
                "data": {
                    "attributes": {
                        "htmlBody": ""
                    }
                }
            })
        )
        print(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid HTML content', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
