FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EFS_MOUNT_PATH=/test \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY src/requirements.txt /tmp/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        nginx \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && python3 -m playwright install-deps chromium \
    && python3 -m playwright install --only-shell chromium \
    && groupadd --system user \
    && useradd --system --gid user --create-home --home-dir /home/user user \
    && mkdir -p /run/nginx /var/lib/nginx /var/log/nginx "$EFS_MOUNT_PATH" "$PLAYWRIGHT_BROWSERS_PATH" \
    && touch /run/nginx.pid \
    && chown -R user:user /run/nginx /var/lib/nginx /var/log/nginx "$EFS_MOUNT_PATH" "$PLAYWRIGHT_BROWSERS_PATH" \
    && chown user:user /run/nginx.pid \
    && rm -rf /var/lib/apt/lists/*

COPY nginx.conf /etc/nginx/nginx.conf

FROM base AS develop

WORKDIR /src
COPY src/ .

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && pip install --no-cache-dir -r requirements.dev.txt \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p "$EFS_MOUNT_PATH" \
    && chown -R user:user "$EFS_MOUNT_PATH"

USER user

RUN python3 -m unittest

FROM base

WORKDIR /src
COPY --from=develop /src/app.py app.py

USER user

CMD ["sh", "-c", "nginx && gunicorn -b 0.0.0.0:8888 app:app"]
