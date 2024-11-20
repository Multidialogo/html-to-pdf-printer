FROM 823598220965.dkr.ecr.eu-west-1.amazonaws.com/amazonlinux-nginx-python:2023.6.20241031.0-1.26-3.9 AS builder

ARG WKHTMLTOPDF_VERSION="0.12.6.1-3"
ARG WKHTMLTOPDF_PLATFORM="x86_64"
ARG WKHTMLTOPDF_SHA256="sha256:357a587c82f1c8a5faf78cebb0a387f780ca51db81d9d8350af27e0bc603524b"
ADD --checksum=$WKHTMLTOPDF_SHA256 \
    "https://github.com/wkhtmltopdf/packaging/releases/download/$WKHTMLTOPDF_VERSION/wkhtmltox-$WKHTMLTOPDF_VERSION.almalinux9.$WKHTMLTOPDF_PLATFORM.rpm" \
    /wkhtmltopdf.rpm

WORKDIR /src
COPY src .
COPY nginx.conf /etc/nginx/nginx.conf

ENV EFS_MOUNT_PATH=/test

RUN dnf install -y $(cat packages.txt) && \
    rpm -ivh /wkhtmltopdf.rpm && \
    dnf clean all && \
    pip install -r requirements.txt -r requirements.dev.txt && \
    mkdir -p "$EFS_MOUNT_PATH" && \
    chown -R user:user "$EFS_MOUNT_PATH"

USER user

RUN python3 -m unittest

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]

FROM 823598220965.dkr.ecr.eu-west-1.amazonaws.com/amazonlinux-nginx-python:2023.6.20241031.0-1.26-3.9 AS production

COPY --from=builder /etc/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /wkhtmltopdf.rpm /wkhtmltopdf.rpm

WORKDIR /src
COPY --from=builder /src/app.py app.py
COPY --from=builder /src/requirements.txt requirements.txt
COPY --from=builder /src/packages.txt packages.txt

RUN dnf install -y $(cat packages.txt) && \
    rpm -ivh /wkhtmltopdf.rpm && \
    dnf clean all && \
    pip install -r requirements.txt && \
    rm /wkhtmltopdf.rpm *.txt

USER user

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]