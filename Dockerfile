ARG BASE_IMAGE=823598220965.dkr.ecr.eu-west-1.amazonaws.com/amazonlinux-nginx-python:2023.6.20241031.0-1.26-3.9

FROM $BASE_IMAGE AS builder

COPY src/requirements.txt requirements.txt
COPY nginx.conf /etc/nginx/nginx.conf

RUN dnf install -y at-spi2-atk \
                   libXcomposite \
                   libXdamage \
                   libXrandr \
                   libgbm \
                   cairo \
                   alsa-lib \
                   nss && \
    pip install -r requirements.txt && \
    python3 -m playwright install --only-shell


FROM $BASE_IMAGE AS develop

WORKDIR /src
COPY src .

COPY --from=builder /etc /etc
COPY --from=builder /lib64 /lib64
COPY --from=builder /sbin /sbin
COPY --from=builder /usr /usr
COPY --from=builder /root/.cache /home/user/.cache

ENV EFS_MOUNT_PATH=/test

RUN pip install -r requirements.dev.txt && \
    mkdir -p "$EFS_MOUNT_PATH" && \
    chown -R user:user "$EFS_MOUNT_PATH"

USER user

RUN python3 -m unittest


FROM $BASE_IMAGE

COPY --from=builder /etc /etc
COPY --from=builder /lib64 /lib64
COPY --from=builder /sbin /sbin
COPY --from=builder /usr /usr
COPY --from=builder /root/.cache /home/user/.cache

WORKDIR /src
COPY --from=develop /src/app.py app.py

USER user

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]