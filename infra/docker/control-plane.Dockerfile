# syntax=docker/dockerfile:1.7
#
# NEXORA Control Plane image. Build context = repository root:
#   docker build -f infra/docker/control-plane.Dockerfile --build-arg GIT_SHA=$(git rev-parse HEAD) .
#
# Base image pinning: an exact patch tag is used here. The release workflow resolves the
# @sha256 digest of this tag at build time and records it in the release artifacts
# (release/base-images.txt) for provenance. Never replace this with a floating tag.

# ---------------------------------------------------------------- builder
FROM python:3.15.1-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# 1) third-party dependencies: ONLY from the hash-pinned lock file.
COPY requirements/prod.txt requirements/prod.txt
RUN pip install --require-hashes --no-cache-dir -r requirements/prod.txt

# 2) first-party packages: no dependency resolution, everything is already locked.
COPY packages/nexora-core packages/nexora-core
COPY packages/nexora-modules packages/nexora-modules
COPY services/control-plane services/control-plane
RUN pip install --no-cache-dir --no-deps \
      ./packages/nexora-core \
      ./packages/nexora-modules \
      ./services/control-plane

# ---------------------------------------------------------------- runtime
FROM python:3.15.1-slim-bookworm AS runtime

ARG GIT_SHA=unknown
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR=/tmp \
    NEXORA_GIT_SHA=${GIT_SHA}

LABEL org.opencontainers.image.title="nexora-control-plane" \
      org.opencontainers.image.revision="${GIT_SHA}"

RUN groupadd --system --gid 10001 nexora \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin nexora

COPY --from=builder /opt/venv /opt/venv

USER 10001:10001
WORKDIR /tmp
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "nexora_control_plane.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--proxy-headers"]
