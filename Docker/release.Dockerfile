FROM html_to_pdf_printer_app

ENV FLASK_ENV=production

ENV PYTHONUNBUFFERED=1

COPY ./requirements-release.txt .

RUN pip install -vvv --target=/app/vendor -r requirements-release.txt

RUN apt-get purge -y python3-pip python3-dev gcc g++ \
    && apt-get autoremove -y

EXPOSE 5000

# then expose 5000 as 80
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

