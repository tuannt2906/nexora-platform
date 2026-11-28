# syntax=docker/dockerfile:1
#
# NEXORA web (static SPA behind nginx). Build context = REPOSITORY ROOT:
#   docker build -f infra/docker/web.Dockerfile --build-arg GIT_SHA=<sha> -t <registry>/web:<sha> .
#
# Base images use EXACT version tags (never a floating tag). The immutable @sha256 digest pin is
# applied/verified by the CI release workflow, not hand-written here.

# ---- stage 1: build the static bundle ---------------------------------------------------
FROM node:24.22.3-alpine3.24 AS build
WORKDIR /app

# Lockfile first so the dependency layer is cached until dependencies change.
COPY apps/web/package.json apps/web/package-lock.json apps/web/.npmrc ./
RUN npm ci --no-audit --no-fund

COPY apps/web/ ./
RUN npm run build

# ---- stage 2: unprivileged nginx --------------------------------------------------------
FROM nginxinc/nginx-unprivileged:1.30.6-alpine

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="nexora-web" \
      org.opencontainers.image.description="NEXORA Control Plane web console" \
      org.opencontainers.image.revision="${GIT_SHA}"

# Apply OS security fixes published after the base image was built. Trade-off: a rebuild is
# not bit-for-bit reproducible, but it never ships known-fixable CVEs (the CI scan enforces it).
USER root
RUN apk upgrade --no-cache \
 && apk add --no-cache --upgrade nginx \
 && nginx -v

# Control Plane address used by the /api/ reverse proxy (override at runtime).
ENV NEXORA_API_UPSTREAM=http://control-plane:8000

COPY --chmod=0644 infra/docker/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=0644 infra/docker/nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build --chmod=0755 /app/dist /usr/share/nginx/html

# Runs as the image's non-root user (uid 101). Listens on 8080 (no privileged port).
# Read-only root filesystem: mount writable emptyDir/tmpfs volumes at /tmp (pid file and
# nginx temp dirs) and /etc/nginx/conf.d (the entrypoint renders the template there).
EXPOSE 8080

# Explicit non-root user (uid 101 is `nginx` in nginx-unprivileged).
USER 101

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
