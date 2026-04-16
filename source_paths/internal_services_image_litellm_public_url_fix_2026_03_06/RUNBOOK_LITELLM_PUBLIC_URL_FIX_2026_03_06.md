# Runbook: LiteLLM Public URL Fix

Date: 2026-03-06
Patch image: `docker.io/aliennor/redis-internal-services-litellm-public-url-fix-20260306:0.2.1`

## Goal
Fix the LiteLLM admin UI so `/ui` and `/ui/login` stay on the DNS hostname instead of redirecting users to the raw IP:port.

## 0) Build and Push Patch Image

```bash
cd internal_services_image_litellm_public_url_fix_2026_03_06

IMG="docker.io/aliennor/redis-internal-services-litellm-public-url-fix-20260306:0.2.1"
docker buildx build --platform linux/amd64 -t "$IMG" --push .
```

## 1) Pull and Extract Patch on Server

```bash
IMG="docker.io/aliennor/redis-internal-services-litellm-public-url-fix-20260306:0.2.1"
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_litellm_public_url_fix_20260306"

mkdir -p "$STAGE"
docker pull "$IMG"
CID=$(docker create "$IMG")
docker cp "$CID":/etc/redis/patches/. "$STAGE"/
docker rm "$CID"

find "$STAGE/$TARGET" -maxdepth 3 -type f | sort
```

## 2) Backup Current Files

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$ROOT/rollback_snapshots/litellm_public_url_fix_$STAMP"

mkdir -p "$BACKUP_DIR"
cp -a "$ROOT/$TARGET/openweb-ui/nginx.conf" "$BACKUP_DIR/nginx.conf.prepatch"
cp -a "$ROOT/$TARGET/litellm/docker-compose.yml" "$BACKUP_DIR/litellm-docker-compose.prepatch"
cp -a "$ROOT/$TARGET/litellm/.env" "$BACKUP_DIR/litellm.env.prepatch"
sha256sum "$BACKUP_DIR/nginx.conf.prepatch" > "$BACKUP_DIR/SHA256SUMS.txt"
sha256sum "$BACKUP_DIR/litellm-docker-compose.prepatch" >> "$BACKUP_DIR/SHA256SUMS.txt"
sha256sum "$BACKUP_DIR/litellm.env.prepatch" >> "$BACKUP_DIR/SHA256SUMS.txt"

ls -lah "$BACKUP_DIR"
cat "$BACKUP_DIR/SHA256SUMS.txt"
```

## 3) Apply Patch

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_litellm_public_url_fix_20260306"

cp -a "$STAGE/$TARGET/openweb-ui/nginx.conf" "$ROOT/$TARGET/openweb-ui/nginx.conf"
cp -a "$STAGE/$TARGET/litellm/docker-compose.yml" "$ROOT/$TARGET/litellm/docker-compose.yml"
cp -a "$STAGE/$TARGET/litellm/.env.example" "$ROOT/$TARGET/litellm/.env.example"
```

## 4) Normalize LiteLLM Public URL in .env

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
ENVF="$ROOT/$TARGET/litellm/.env"

sed -i '/^PROXY_BASE_URL[:=]/d' "$ENVF"
sed -i '/^PROXY_LOGOUT_URL[:=]/d' "$ENVF"
sed -i '/^GENERIC_[A-Z0-9_]*[:=]/d' "$ENVF"
printf '\nPROXY_BASE_URL=https://manavgat.yzyonetim-dev.zb\n' >> "$ENVF"
chmod 600 "$ENVF"

tail -n 10 "$ENVF"
```

## 5) Validate and Restart Stacks

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
OW="$ROOT/$TARGET/openweb-ui"
LIT="$ROOT/$TARGET/litellm"

(cd "$OW" && docker compose -f docker-compose.yml config >/dev/null)
(cd "$LIT" && docker compose -f docker-compose.yml config >/dev/null)
(cd "$LIT" && docker compose -f docker-compose.yml up -d)
(cd "$OW" && docker compose -f docker-compose.yml up -d)
```

## 6) Smoke Checks

```bash
curl -kI https://manavgat.yzyonetim-dev.zb/ui/
curl -kI https://manavgat.yzyonetim-dev.zb/ui
curl -ks https://manavgat.yzyonetim-dev.zb/ | head -n 20
docker logs --since 5m litellm 2>&1 | tail -n 50
docker logs --since 5m nginx-proxy 2>&1 | tail -n 50
```

## 7) Rollback

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BACKUP_DIR="/opt/orbina/rollback_snapshots/litellm_public_url_fix_YYYYmmdd_HHMMSS"

cp -a "$BACKUP_DIR/nginx.conf.prepatch" "$ROOT/$TARGET/openweb-ui/nginx.conf"
cp -a "$BACKUP_DIR/litellm-docker-compose.prepatch" "$ROOT/$TARGET/litellm/docker-compose.yml"
cp -a "$BACKUP_DIR/litellm.env.prepatch" "$ROOT/$TARGET/litellm/.env"
(cd "$ROOT/$TARGET/litellm" && docker compose -f docker-compose.yml up -d)
(cd "$ROOT/$TARGET/openweb-ui" && docker compose -f docker-compose.yml up -d)
```

## Notes
- This patch changes `openweb-ui/nginx.conf` and `litellm/docker-compose.yml`.
- The runbook rewrites `PROXY_BASE_URL` inside `litellm/.env` and removes stale `PROXY_LOGOUT_URL` / `GENERIC_*` auth lines left from the old keycloak-based setup.
- If other devices still cannot access the DNS names after this, that is outside the app stack and should be checked with DNS/network tests from their devices.
