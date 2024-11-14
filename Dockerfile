FROM 823598220965.dkr.ecr.eu-west-1.amazonaws.com/amazonlinux:2023.6.20241031.0

ARG WKHTMLTOPDF_VERSION="0.12.6.1-3"
ARG WKHTMLTOPDF_PLATFORM="x86_64"
ARG WKHTMLTOPDF_SHA256="sha256:357a587c82f1c8a5faf78cebb0a387f780ca51db81d9d8350af27e0bc603524b"
ADD --checksum=$WKHTMLTOPDF_SHA256 \
    "https://github.com/wkhtmltopdf/packaging/releases/download/$WKHTMLTOPDF_VERSION/wkhtmltox-$WKHTMLTOPDF_VERSION.almalinux9.$WKHTMLTOPDF_PLATFORM.rpm" \
    /wkhtmltopdf.rpm

WORKDIR /src
COPY src .
COPY nginx.conf /etc/nginx/nginx.conf

ARG EFS_MOUNT_PATH
ENV EFS_MOUNT_PATH=$EFS_MOUNT_PATH

ARG DEV=false
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
                   zlib \
                   python-pip \
                   nginx && \
    rpm -ivh /wkhtmltopdf.rpm && \
    dnf clean all && \
    rm /wkhtmltopdf.rpm && \
    pip install -r requirements.txt && \
    touch /run/nginx.pid && \
    adduser \
        --no-create-home \
        --shell /usr/sbin/nologin \
        user && \
    chown -R user:user /var/log/nginx && \
    chown -R user:user /var/lib/nginx && \
    chown -R user:user /run/nginx.pid

USER user

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]