import base64
import json
import logging

import pdfkit
from flask import Flask, request

class HtmlToPdf:

    LOGGER = logging.getLogger()

    def __init__(self):
        self.LOGGER.setLevel(logging.INFO)  # Set level for AWS CloudWatch, doesn't affect Develop/local environment.

    def process(self, event: dict, context):

        errors_strs = []
        error_msg = 'New request received contains errors: '

        if event and event['httpMethod'] != 'POST':
            errors_strs.append(f"only the POST method is allowed {event['httpMethod']} given")

        try:
            # Check if Content-Type is application/json
            if request.content_type != 'application/json':
                return self.error_response("Content-Type", "Must be application/json", 415)

            # Check if Accept header is application/pdf
            if request.headers.get('Accept') != 'application/pdf':
                return self.error_response("Accept", "Must be application/pdf", 406)

            # Extract JSON data from the POST request
            data = request.get_json()
            if not data or 'data' not in data or 'attributes' not in data['data']:
                return self.error_response("JSON API Structure", "Expected 'data.attributes.htmlBody'")

            attributes = data['data']['attributes']

            # Extract the HTML body from the JSON API envelope
            html_body = attributes.get('htmlBody')
            html_url = attributes.get('htmlUrl')

            # Validate the HTML content
            if not html_body and not html_url:
                return self.error_response("HTML Content",
                                      "one of data.attributes.htmlBody or data.attributes.htmlUrl must be set")

            output_filename = attributes.get('outputFilename')

            # Validate output file name
            if not output_filename:
                return self.error_response("Output Filename", "data.attributes.output_filename is required", 400)

            pdf_bytes = b''
            if html_body:
                pdf_bytes = pdfkit.from_string(html_body, False)
            elif html_url:
                pdf_bytes = pdfkit.from_url(html_url, False)

            # Send the PDF as a response with Content-Type application/pdf
            response = self.create_response(
                200,
                base64.b64encode(pdf_bytes).decode('utf-8'), # TODO: Is necessary to encode in base64
                'application/pdf',
                True
            )
            # response['headers']['content-disposition'] = f"attachment; filename={output_filename}"
            return response

        except Exception as e:
            logging.error(f"Error generating PDF: {e}")
            return self.error_response("Internal Server Error", str(e), 500)

    def create_response(
            self,
            code: int = 200,
            body=None,
            content_type: str = 'application/json',
            base64_encoded: bool = False
    ):
        response = {
            'statusCode': code,
            'headers': {'Content-Type': content_type},
            'isBase64Encoded': base64_encoded,
        }
        if body is not None:
            response['body'] = json.dumps(body) if isinstance(body, dict) else body

        return response

    def error_response(self, title: str = None, detail: str = None, code: int = 400):
        body = {"error": {"title": title, "detail": detail}}
        return self.create_response(code, body)


def handler(event: dict, context):
    html_pdf = HtmlToPdf()
    return html_pdf.process(event, context)
