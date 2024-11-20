ARG BASE_IMAGE=823598220965.dkr.ecr.eu-west-1.amazonaws.com/amazonlinux-nginx-python:2023.6.20241031.0-1.26-3.9

FROM $BASE_IMAGE AS builder

ARG WKHTMLTOPDF_VERSION="0.12.6.1-3"
ARG WKHTMLTOPDF_PLATFORM="x86_64"
ARG WKHTMLTOPDF_SHA256="sha256:357a587c82f1c8a5faf78cebb0a387f780ca51db81d9d8350af27e0bc603524b"
ADD --checksum=$WKHTMLTOPDF_SHA256 \
    "https://github.com/wkhtmltopdf/packaging/releases/download/$WKHTMLTOPDF_VERSION/wkhtmltox-$WKHTMLTOPDF_VERSION.almalinux9.$WKHTMLTOPDF_PLATFORM.rpm" \
    /wkhtmltopdf.rpm

COPY src/requirements.txt requirements.txt
COPY nginx.conf /etc/nginx/nginx.conf

RUN dnf install -y ca-certificates \
                   fontconfig \
                   freetype \
                   glibc \
                   libjpeg \
                   libpng \
                   libstdc++ \
                   libX11 \
                   libXext \
                   libXrender \
                   openssl \
                   xorg-x11-fonts-75dpi \
                   xorg-x11-fonts-Type1 \
                   zlib && \
    rpm -ivh /wkhtmltopdf.rpm && \
    pip install -r requirements.txt


FROM $BASE_IMAGE AS develop

WORKDIR /src
COPY src .

COPY --from=builder /etc /etc
COPY --from=builder /lib64 /lib64
COPY --from=builder /sbin /sbin
COPY --from=builder /usr /usr

ENV EFS_MOUNT_PATH=/test

RUN pip install -r requirements.dev.txt && \
    mkdir -p "$EFS_MOUNT_PATH" && \
    chown -R user:user "$EFS_MOUNT_PATH"

USER user

RUN python3 -m unittest

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]


FROM $BASE_IMAGE

COPY --from=builder /etc /etc
COPY --from=builder /lib64 /lib64
COPY --from=builder /sbin /sbin
COPY --from=builder /usr /usr

WORKDIR /src
COPY --from=develop /src/app.py app.py

USER user

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]