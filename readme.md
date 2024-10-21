# HTML to PDF Printer API Usage

This document explains how to use the HTML to PDF Printer API provided in the app.py file of the Multidialogo repository.

## Overview

The HTML to PDF Printer is a Python web application that converts HTML documents into PDF files. It utilizes the Flask web framework to create an API endpoint that accepts HTML content and returns a PDF file.

## Prerequisites

Before using this API, ensure you have the following installed:

- Python 3.x
- Flask
- pdfkit (for converting HTML to PDF)
- wkhtmltopdf (a command-line tool used by pdfkit)

## Installation

1. Clone the repository:

   git clone https://github.com/Multidialogo/html-to-pdf-printer.git

2. Navigate to the project directory:

   cd html-to-pdf-printer

3. Install the required Python packages:

   pip install -r requirements.txt

4. Ensure wkhtmltopdf is installed on your system. You can download it from wkhtmltopdf.org and follow the installation instructions for your operating system.

## Running the Application

To run the application, execute the following command:

python src/app.py

This will start the Flask server, which listens for requests on http://127.0.0.1:5000.

### Docker quick start

```bash
docker compose build
```

```bash
docker compose run --rm test
```

```bash
docker compose run --rm app
```

## API Endpoint

### Convert HTML to PDF

- URL: /convert
- Method: POST
- Content-Type: application/json
- Accept: application/pdf

#### Request Body

The request body should follow the JSON API format, structured as follows:

{
  "data": {
    "attributes": {
      "htmlBody": "<h1>Hello, World!</h1>",
      "outputFilename": "example.pdf"
    }
  }
}

- htmlBody: A string containing the HTML content to be converted to PDF.
- outputFilename (optional): A string specifying the name of the output PDF file. If not provided, a default filename will be used.

#### Example Request Using curl

curl -X POST http://127.0.0.1:5000/convert \
-H "Content-Type: application/json" \
-d '{
  "data": {
    "attributes": {
      "htmlBody": "<h1>Hello, World!</h1>",
      "outputFilename": "example.pdf"
    }
  }
}'

#### Response

On success, the server responds with a PDF file. The response will have the following headers:

- Content-Type: application/pdf
- Content-Disposition: attachment; filename="output.pdf" (or the provided outputFilename)

#### Example Response

The response will be a PDF file download containing the converted HTML.

### Error Handling

If there is an error during the conversion process, the API will respond with a JSON object structured in dot notation as follows:

{
  "errors": {
    "title": "Error Title",
    "detail": "Error message describing the issue."
  }
}

- errors.title: A string summarizing the error type.
- errors.detail: A string providing a detailed description of the error.

## Conclusion

The HTML to PDF Printer API is a simple and effective way to convert HTML documents into PDF files using a RESTful API. By following the instructions above, you can easily integrate this functionality into your applications.
