FROM node:22-bookworm-slim AS dashboard
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim-bookworm AS package
WORKDIR /build
COPY pyproject.toml LICENSE ./
COPY src/ src/
RUN python -m pip wheel . --no-deps --wheel-dir /wheels

FROM python:3.13-slim-bookworm
WORKDIR /opt/governloom
COPY requirements.lock /tmp/requirements.lock
COPY --from=package /wheels/ /tmp/wheels/
RUN python -m pip install --no-cache-dir -r /tmp/requirements.lock /tmp/wheels/*.whl \
    && groupadd --gid 10001 governloom && useradd --uid 10001 --gid 10001 --no-create-home governloom \
    && mkdir -p /data && chown governloom:governloom /data
COPY --from=dashboard /build/web/dist/ /opt/governloom/web/dist/
ENV GOVERNLOOM_DB=sqlite:////data/collector.db \
    GOVERNLOOM_WEBHOOK_SECRETS=/data/secrets \
    GOVERNLOOM_AUTH_MODE=operators \
    GOVERNLOOM_WEB_DIST=/opt/governloom/web/dist \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2).read()"]
CMD ["python", "-m", "uvicorn", "governloom.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
