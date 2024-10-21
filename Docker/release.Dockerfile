FROM html_to_pdf_printer_app

RUN pip install -vvv --target=/app/vendor -r requirements.txt

RUN apt-get purge -y python3-pip python3-dev gcc g++ libgirepository1.0-dev \
    && apt-get autoremove -y

ENV FLASK_ENV="production"

EXPOSE 80

CMD ["exec", "python3", "src/app.py"]