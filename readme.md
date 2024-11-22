# HTML to PDF Printer API Usage

This document explains how to use the HTML to PDF Printer API provided in the `app.py` file of the `src` directory.

## Overview

The HTML to PDF Printer is a Python web application that converts HTML documents or a link into PDF files.

## API Interface Documentation

This project exposes a `/download` route that returns the relative path of the generated PDF file.
The path is relative to the `X-Caller-Service` header, set by the caller, and should correspond to a directory mounted on the calling service.

### Example of a 200 Response

Below is an example of a response with a status code of 200:
```json
{
  "data": {
    "attributes": {
      "sharedFilePath": "2024/11/06/5/5d41402abc4b2a76b9719d911017c592.pdf"
    }
  }
}
```

### Requirements for the `/download` Route

The `/download` route requires that the request be formulated in a specific way in order to respond correctly.
Therefore, the following requirements must be met:
- Use only the **POST** method for the HTTP call.
- Set the `Content-Type` header to `application/json`.
- Set the `Accept` header to `application/json`.
- Populate the `X-Caller-Service` header with the name of the calling service (e.g. `MULTIDIALOGO-API`).
- Format the request body as shown below, containing either an `htmlBody` with the HTML to be converted to PDF, or an
`htmlUrl` with the URL of the resource to be converted to PDF. If both are provided, `htmlBody` will be used.

Example of the request body:
```json
{
   "data": {
      "attributes": {
         "htmlUrl": "https://www.google.it"
      }
   }
}
```

### Error Handling

In case of an error, the structure of the response is as follows:
```json
{
  "error": {
    "detail": "'X-Caller-Service' header is null or empty",
    "title": "Invalid X-Caller-Service header"
  }
}
```

### Note on the `/health-check` Route

A brief mention of the `/health-check` route, used for system purposes.

## Running the Application

The project can be run with the command `docker compose up`.
This will start the Flask server, which listens for requests on http://127.0.0.1:5000 or http://localhost:5000.

## Test

Run unit tests with the following command (use the `-v` option for more verbose output):
```
docker compose run --rm app unittest [file_name] [-v]
```
This test only checks the Python code and does not include the Nginx configuration.
To test the Nginx configuration, it is necessary to run this project as if it were in production.
To do this, you need to run the following command:
```
docker compose run -p 5000:5000 --rm app production
```
In this way, you can also test the `nginx.conf` file using an external tool like Postman.

## Coverage test

A coverage report can be obtained by running:
```
docker compose run --rm app coverage
```

## SAST (Static application security testing)

A SAST analysis can be performed by running:
```
docker compose run --rm app bandit
```