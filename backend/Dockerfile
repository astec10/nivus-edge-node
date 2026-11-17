FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ARG NIVUS_RUNTIME_UID=12001
ARG NIVUS_RUNTIME_GID=12001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 NIVUS_DB_PATH=/data/nivus.db NIVUS_JWT_SECRET_FILE=/run/secrets/jwt_secret NIVUS_PROVIDER_ENCRYPTION_KEY_FILE=/run/secrets/provider_encryption_key
RUN groupadd --system --gid "${NIVUS_RUNTIME_GID}" nivus && useradd --system --uid "${NIVUS_RUNTIME_UID}" --gid nivus --home-dir /nonexistent --shell /usr/sbin/nologin nivus && mkdir -p /app /data /tmp && chown "${NIVUS_RUNTIME_UID}:${NIVUS_RUNTIME_GID}" /data /tmp
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt
COPY --chown=${NIVUS_RUNTIME_UID}:${NIVUS_RUNTIME_GID} backend/ /app/
USER ${NIVUS_RUNTIME_UID}:${NIVUS_RUNTIME_GID}
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
