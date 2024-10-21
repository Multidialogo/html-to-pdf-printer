from flask import Flask, request, send_file, jsonify
import pdfkit
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_url_path='/static')

@app.route('/convert', methods=['POST'])
def generate_pdf():
    """
    Generates a PDF from the provided HTML content in a JSON API structure.

    Returns:
        Response: A PDF file or an error message.
    """
    try:
        # Check if Content-Type is application/json
        if request.content_type != 'application/json':
            return jsonify({"error": {"title": "Content-Type", "detail": "Must be application/json"}}), 415

        # Check if Accept header is application/pdf
        if request.headers.get('Accept') != 'application/pdf':
            return jsonify({"error": {"title": "Accept", "detail": "Must be application/pdf"}}), 406

        # Extract JSON data from the POST request
        data = request.get_json()
        if not data or 'data' not in data or 'attributes' not in data['data'] or 'htmlBody' not in data['data']['attributes']:
            return jsonify({"error": {"title": "JSON API Structure", "detail": "Expected 'data.attributes.htmlBody'"}}), 400

        # Extract the HTML body from the JSON API envelope
        html_content = data['data']['attributes']['htmlBody']
        output_filename = data['data']['attributes']['outputFilename']

        # Validate the HTML content
        if not html_content:
            return jsonify({"error": {"title": "HTML Content", "detail": "data.attributes.htmlBody cannot be empty"}}), 400

        # Validate output file name
        if not output_filename:
            return jsonify({"error": {"title": "Output Filename", "detail": "data.attributes.output_filename is required"}}), 400

        # Generate the PDF from the HTML string using pdfkit
        pdf_file = BytesIO()
        pdfkit.from_string(html_content, pdf_file)

        # Move the cursor to the beginning of the BytesIO object
        pdf_file.seek(0)

        # Send the PDF as a response with Content-Type application/pdf
        return send_file(pdf_file, download_name=output_filename, as_attachment=True, mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return jsonify({"error": {"title": "Internal Server Error", "detail": str(e)}}), 500


if __name__ == '__main__':
    app.run(debug=True)
