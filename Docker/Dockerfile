FROM python:3.9-slim

WORKDIR /app

ENV PYTHONPATH="${PYTHONPATH}:/app/src:/app/vendor"

COPY ./src/ ./src/

COPY ./requirements.txt .

COPY ./vendor/ ./vendor-tmp/

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --upgrade pip && pip cache purge

RUN pip install -vvv --target=/app/vendor-tmp -r requirements.txt

CMD ["exec", "python3", "src/app.py"]