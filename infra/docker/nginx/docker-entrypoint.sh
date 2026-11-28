#!/bin/sh
# Render the nginx server block from its template, then run nginx in the foreground.
# Only NEXORA_API_UPSTREAM is substituted, so nginx's own $variables stay untouched.
set -eu

upstream="${NEXORA_API_UPSTREAM:-}"
if [ -z "$upstream" ]; then
  echo "NEXORA_API_UPSTREAM is required (for example http://control-plane:8000)" >&2
  exit 64
fi

# Refuse anything that is not scheme://host[:port]: the value is written into nginx configuration.
case "$upstream" in
  http://* | https://*) ;;
  *)
    echo "NEXORA_API_UPSTREAM must start with http:// or https://" >&2
    exit 64
    ;;
esac
host_port="${upstream#*://}"
if printf '%s' "$host_port" | grep -Eqv '^[A-Za-z0-9.-]+(:[0-9]{1,5})?$'; then
  echo "NEXORA_API_UPSTREAM must be scheme://host[:port] without a path or special characters" >&2
  exit 64
fi

# shellcheck disable=SC2016 # the literal ${...} list is envsubst's own syntax, not a shell expansion
envsubst '${NEXORA_API_UPSTREAM}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -e /dev/stderr -t
exec nginx -e /dev/stderr -g 'daemon off;'
