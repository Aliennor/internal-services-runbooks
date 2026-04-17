# Banka Dev108 HTTPS And LiteLLM DNS Cutover

Date: 2026-04-17

Use this after the r27/r6 first install is already healthy on dev `108` with
direct HTTP/IP ports.

This runbook switches dev `108` from HTTP/IP-first bring-up to node-local HTTPS
with the certificate files already staged under `/tmp`, and it switches
LiteLLM/Langfuse public URLs back from direct IP ports to HTTPS DNS names.

Do not use this for prod `106/107`. Prod should keep node runtime HTTP-first
and terminate TLS on the load balancer.

## 1) Preconditions

Run on `10.11.115.108` as `root`.

Confirm the first-install stack is already healthy before changing URLs:

```bash
set -euo pipefail

curl -fsS http://127.0.0.1:18081/ready
curl -fsS http://127.0.0.1:4000/health
curl -I http://127.0.0.1:8080/ || true
curl -I http://127.0.0.1:3000/ || true
```

Confirm the certificate and key are staged:

```bash
ls -l /tmp/cert.pem /tmp/private.key
openssl x509 -in /tmp/cert.pem -noout -subject -issuer -dates
openssl x509 -in /tmp/cert.pem -noout -text | grep -A2 'Subject Alternative Name' || true
```

If DNS is not live yet, add temporary local resolution for validation:

```bash
grep -q 'zfgasistan-yzyonetim-dev.ziraat.bank' /etc/hosts || cat >> /etc/hosts <<'EOF'
10.11.115.108 zfgasistan-yzyonetim-dev.ziraat.bank
10.11.115.108 manavgat-yzyonetim-dev.ziraat.bank
10.11.115.108 aykal-yzyonetim-dev.ziraat.bank
10.11.115.108 mercek-yzyonetim-dev.ziraat.bank
10.11.115.108 mecra-yzyonetim-dev.ziraat.bank
EOF
```

## 2) Backup Current Config

```bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/opt/orbina/backups/dev108-https-cutover-${TS}"
mkdir -p "$BACKUP_DIR"

cp -a /etc/internal-services/ha.env "$BACKUP_DIR/ha.env"
cp -a /opt/orbina/internal_services/openweb-ui/.env "$BACKUP_DIR/openweb-ui.env"
cp -a /opt/orbina/internal_services/litellm/.env "$BACKUP_DIR/litellm.env"
cp -a /opt/orbina/internal_services/langfuse/.env "$BACKUP_DIR/langfuse.env"

if [ -f /etc/pki/tls/certs/cert.pem ]; then
  cp -a /etc/pki/tls/certs/cert.pem "$BACKUP_DIR/cert.pem"
fi
if [ -f /etc/pki/tls/private/private.key ]; then
  cp -a /etc/pki/tls/private/private.key "$BACKUP_DIR/private.key"
fi

echo "$BACKUP_DIR" > /tmp/dev108_https_cutover_last_backup_dir
echo "Backup: $BACKUP_DIR"
```

## 3) Install The `/tmp` Certificate Files

```bash
set -euo pipefail

install -m 0644 /tmp/cert.pem /etc/pki/tls/certs/cert.pem
install -m 0600 /tmp/private.key /etc/pki/tls/private/private.key
```

## 4) Switch HA And Service Env Files To HTTPS DNS

```bash
set -euo pipefail

upsert_env() {
  file="$1"
  key="$2"
  value="$3"
  if grep -q "^${key}=" "$file"; then
    sed -i "s#^${key}=.*#${key}=${value}#" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

upsert_env /etc/internal-services/ha.env PUBLIC_URL_SCHEME https
upsert_env /etc/internal-services/ha.env OPENWEBUI_NGINX_CONFIG_PATH ./nginx.generated.conf
upsert_env /etc/internal-services/ha.env NODE_TLS_CERT_SOURCE_PATH /tmp/cert.pem
upsert_env /etc/internal-services/ha.env NODE_TLS_KEY_SOURCE_PATH /tmp/private.key

upsert_env /opt/orbina/internal_services/openweb-ui/.env NGINX_CONFIG_PATH ./nginx.generated.conf

upsert_env /opt/orbina/internal_services/litellm/.env PROXY_BASE_URL https://manavgat-yzyonetim-dev.ziraat.bank

upsert_env /opt/orbina/internal_services/langfuse/.env NEXTAUTH_URL https://mercek-yzyonetim-dev.ziraat.bank
```

Keep these LiteLLM values internal; do not change them to HTTPS DNS:

```bash
grep -E '^(LANGFUSE_BASE_URL|LANGFUSE_HOST|PROXY_BASE_URL)=' /opt/orbina/internal_services/litellm/.env
```

Expected:

- `LANGFUSE_BASE_URL=http://langfuse-web:3000`
- `LANGFUSE_HOST=http://langfuse-web:3000`
- `PROXY_BASE_URL=https://manavgat-yzyonetim-dev.ziraat.bank`

## 5) Regenerate Nginx Config And Restart Affected Services

```bash
set -euo pipefail

cd /opt/orbina/internal_services

ops/install/katilim/render-openwebui-nginx.sh \
  --env-file /etc/internal-services/ha.env \
  --out-dir /opt/orbina/internal_services/openweb-ui

cd /opt/orbina/internal_services/openweb-ui
podman compose -f docker-compose.yml up -d

cd /opt/orbina/internal_services/litellm
podman compose -f docker-compose.yml up -d

cd /opt/orbina/internal_services/langfuse
podman compose -f docker-compose.yaml up -d
```

## 6) Validate HTTPS

Validate nginx config and HA readiness:

```bash
podman exec nginx-proxy nginx -t
podman exec nginx-proxy wget -qO- http://127.0.0.1:8081/health
curl -fsS http://127.0.0.1:18081/ready
```

Validate HTTPS DNS routes locally:

```bash
curl -kI --resolve zfgasistan-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://zfgasistan-yzyonetim-dev.ziraat.bank/
curl -kI --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://manavgat-yzyonetim-dev.ziraat.bank/
curl -kI --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://mercek-yzyonetim-dev.ziraat.bank/
curl -kI --resolve aykal-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://aykal-yzyonetim-dev.ziraat.bank/
curl -kI --resolve mecra-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://mecra-yzyonetim-dev.ziraat.bank/
```

Validate LiteLLM and Langfuse public URL envs:

```bash
grep -E '^PROXY_BASE_URL=' /opt/orbina/internal_services/litellm/.env
grep -E '^NEXTAUTH_URL=' /opt/orbina/internal_services/langfuse/.env

podman logs --tail=120 litellm || true
podman logs --tail=120 langfuse-web || true
```

Expected:

- `PROXY_BASE_URL=https://manavgat-yzyonetim-dev.ziraat.bank`
- `NEXTAUTH_URL=https://mercek-yzyonetim-dev.ziraat.bank`
- nginx answers on `443`
- HA readiness remains `200`

If the cert is self-signed and not trusted by the client, browser/curl may still
warn unless the CA is trusted. That is separate from the service cutover.

## 7) Rollback To HTTP/IP-First

Run this if HTTPS cutover breaks login or service health:

```bash
set -euo pipefail

BACKUP_DIR="$(cat /tmp/dev108_https_cutover_last_backup_dir)"
test -d "$BACKUP_DIR"

cp -a "$BACKUP_DIR/ha.env" /etc/internal-services/ha.env
cp -a "$BACKUP_DIR/openweb-ui.env" /opt/orbina/internal_services/openweb-ui/.env
cp -a "$BACKUP_DIR/litellm.env" /opt/orbina/internal_services/litellm/.env
cp -a "$BACKUP_DIR/langfuse.env" /opt/orbina/internal_services/langfuse/.env

cd /opt/orbina/internal_services
ops/install/katilim/render-openwebui-nginx.sh \
  --env-file /etc/internal-services/ha.env \
  --out-dir /opt/orbina/internal_services/openweb-ui

cd /opt/orbina/internal_services/openweb-ui
podman compose -f docker-compose.yml up -d

cd /opt/orbina/internal_services/litellm
podman compose -f docker-compose.yml up -d

cd /opt/orbina/internal_services/langfuse
podman compose -f docker-compose.yaml up -d

curl -fsS http://127.0.0.1:18081/ready
curl -fsS http://127.0.0.1:4000/health
```
