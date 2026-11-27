# syntax=docker/dockerfile:1

# ---- builder: build the wheel from the source tree ----
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /src
RUN pip install build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY controlplane ./controlplane
RUN python -m build --wheel --outdir /dist

# ---- final: install aeon-core[runtime] from the wheel only ----
FROM python:3.12-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    # Needed inside the container: the port is published to the host, so the
    # process must bind 0.0.0.0. Publish it only on 127.0.0.1 (see compose.yaml)
    # and keep the token set.
    AEON_RUNTIME_ALLOW_REMOTE=1
COPY --from=builder /dist/*.whl /tmp/wheels/
RUN pip install "$(ls /tmp/wheels/*.whl)[runtime]" && rm -rf /tmp/wheels
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin aeon \
    && mkdir /data && chown aeon:aeon /data
USER 10001:10001
WORKDIR /data
VOLUME /data
EXPOSE 8787
# Any HTTP answer from /health counts as alive (401/403 when a token is enforced).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys,urllib.request as u,urllib.error as e\ntry:\n u.urlopen('http://127.0.0.1:8787/health',timeout=4)\nexcept e.HTTPError as x:\n sys.exit(0 if x.code in (401,403) else 1)\nexcept Exception:\n sys.exit(1)"]
ENTRYPOINT ["aeon"]
CMD ["runtime", "start", "--host", "0.0.0.0", "--port", "8787"]
