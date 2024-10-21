FROM html_to_pdf_printer_app

ENV PYTHONPATH="${PYTHONPATH}:/app/test"

COPY ./test/ ./test

COPY ./requirements-test.txt .

COPY ./vendor-test/ /app/vendor-tmp/

RUN pip install -vvv --target=/app/vendor-tmp -r requirements-test.txt

CMD ["exec", "python3", "-m", "unittest", "discover", "-s", "test"]
