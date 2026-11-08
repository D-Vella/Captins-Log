#!/bin/sh
set -e

# Generate TLS cert on first run (only if not already present)
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
  echo "Generating self-signed TLS certificate..."
  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
      -subj "/CN=melody" \
      -addext "subjectAltName=DNS:melody,DNS:melody.local,DNS:localhost,IP:192.168.0.119,IP:127.0.0.1"
fi

alembic upgrade head
exec "$@"
