FROM public.ecr.aws/lambda/python:3.12

COPY src $LAMBDA_TASK_ROOT

ARG WKHTMLTOPDF_VERSION="0.12.6.1-3"
ARG WKHTMLTOPDF_PLATFORM="x86_64"
ARG WKHTMLTOPDF_SHA256="sha256:357a587c82f1c8a5faf78cebb0a387f780ca51db81d9d8350af27e0bc603524b"
ADD --checksum=$WKHTMLTOPDF_SHA256 \
    "https://github.com/wkhtmltopdf/packaging/releases/download/$WKHTMLTOPDF_VERSION/wkhtmltox-$WKHTMLTOPDF_VERSION.almalinux9.$WKHTMLTOPDF_PLATFORM.rpm" \
    /wkhtmltopdf.rpm

ARG DEV=false
RUN dnf install -y fontconfig freetype libX11 libXext libXrender libjpeg libpng openssl xorg-x11-fonts-75dpi xorg-x11-fonts-Type1 && \
    rpm -ivh /wkhtmltopdf.rpm && \
    dnf clean all && \
    rm -f /wkhtmltopdf.rpm && \
    pip install -r requirements.txt && \
    if [ $DEV = "true" ]; \
        then pip install -r requirements.dev.txt; \
        else rm test_* requirements*; \
    fi

CMD [ "app.handler" ]