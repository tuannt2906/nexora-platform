# syntax=docker/dockerfile:1
#
# NEXORA web (static SPA behind nginx). Build context = REPOSITORY ROOT:
#   docker build -f infra/docker/web.Dockerfile --build-arg GIT_SHA=<sha> -t <registry>/web:<sha> .
#
# Base images use EXACT version tags (never a floating tag). The release workflow records the
# resolved @sha256 digests (release/base-images.txt) for provenance.
#
# nginx comes from Alpine's own package repository (not the nginx-unprivileged image): the
# distribution ships security fixes for it quickly, whereas the upstream image is rebuilt only
# occasionally and was found to contain fixable HIGH/CRITICAL CVEs (Trivy gate in CI).

# ---- stage 1: build the static bundle ---------------------------------------------------
FROM node:24.22.3-alpine3.24 AS build
WORKDIR /app

# Lockfile first so the dependency layer is cached until dependencies change.
COPY apps/web/package.json apps/web/package-lock.json apps/web/.npmrc ./
RUN npm ci --no-audit --no-fund

COPY apps/web/ ./
RUN npm run build

# ---- stage 2: unprivileged nginx --------------------------------------------------------
FROM alpine:3.24.4

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="nexora-web" \
      org.opencontainers.image.description="NEXORA Control Plane web console" \
      org.opencontainers.image.revision="${GIT_SHA}"

# uid/gid 101 first so the nginx package reuses them (Kubernetes manifests run as 101).
RUN addgroup -S -g 101 nginx \
 && adduser -S -D -H -u 101 -G nginx -s /sbin/nologin nginx \
 && apk upgrade --no-cache \
 && apk add --no-cache nginx gettext-envsubst \
 && rm -rf /etc/nginx/http.d /etc/nginx/conf.d \
 && mkdir -p /etc/nginx/conf.d /etc/nginx/snippets /etc/nginx/templates /usr/share/nginx/html \
 && chown 101:101 /etc/nginx/conf.d \
 && nginx -v

# Control Plane address used by the /api/ reverse proxy (override at runtime).
ENV NEXORA_API_UPSTREAM=http://control-plane:8000

COPY --chmod=0644 infra/docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=0644 infra/docker/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=0644 infra/docker/nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --chmod=0755 infra/docker/nginx/docker-entrypoint.sh /docker-entrypoint.sh
COPY --from=build --chmod=0755 /app/dist /usr/share/nginx/html

# Listens on 8080 (no privileged port) as a non-root user. Read-only root filesystem: mount
# writable emptyDir/tmpfs volumes at /tmp (pid file, nginx temp dirs) and /etc/nginx/conf.d
# (the entrypoint renders the server block there).
EXPOSE 8080
STOPSIGNAL SIGQUIT
USER 101

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
