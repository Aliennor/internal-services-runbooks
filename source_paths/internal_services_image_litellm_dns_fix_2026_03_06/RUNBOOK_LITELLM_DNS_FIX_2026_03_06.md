# Runbook: LiteLLM DNS Admin UI Fix

Date: 2026-03-06
Patch image: `docker.io/aliennor/redis-internal-services-litellm-dns-fix-20260306:0.1.0`

## Goal
Fix the LiteLLM reverse-proxy behavior so `/ui` stays on the DNS hostname instead of redirecting users to the raw IP:port.

## 0) Build and Push Patch Image

```bash
cd internal_services_image_litellm_dns_fix_2026_03_06

IMG="docker.io/aliennor/redis-internal-services-litellm-dns-fix-20260306:0.1.0"
docker buildx build --platform linux/amd64 -t "$IMG" --push .
```

## 1) Pull and Extract Patch on Server

```bash
IMG="docker.io/aliennor/redis-internal-services-litellm-dns-fix-20260306:0.1.0"
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_litellm_dns_fix_20260306"

mkdir -p "$STAGE"
docker pull "$IMG"
CID=$(docker create "$IMG")
docker cp "$CID":/etc/redis/patches/. "$STAGE"/
docker rm "$CID"

find "$STAGE/$TARGET" -maxdepth 3 -type f | sort
```

## 2) Backup Current nginx.conf

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$ROOT/rollback_snapshots/litellm_dns_fix_$STAMP"

mkdir -p "$BACKUP_DIR"
cp -a "$ROOT/$TARGET/openweb-ui/nginx.conf" "$BACKUP_DIR/nginx.conf.prepatch"
sha256sum "$BACKUP_DIR/nginx.conf.prepatch" > "$BACKUP_DIR/SHA256SUMS.txt"

ls -lah "$BACKUP_DIR"
cat "$BACKUP_DIR/SHA256SUMS.txt"
```

## 3) Apply Patch

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_litellm_dns_fix_20260306"

cp -a "$STAGE/$TARGET/openweb-ui/nginx.conf" "$ROOT/$TARGET/openweb-ui/nginx.conf"
```

## 4) Validate and Restart openweb-ui Stack

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
D="$ROOT/$TARGET/openweb-ui"

(cd "$D" && docker compose -f docker-compose.yml config >/dev/null)
(cd "$D" && docker compose -f docker-compose.yml up -d)
```

## 5) Smoke Checks

```bash
curl -kI https://manavgat.yzyonetim-dev.zb/ui/
curl -kI https://manavgat.yzyonetim-dev.zb/
docker logs --since 5m nginx-proxy 2>&1 | tail -n 50
```

## 6) Rollback

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BACKUP_DIR="/opt/orbina/rollback_snapshots/litellm_dns_fix_YYYYmmdd_HHMMSS"

cp -a "$BACKUP_DIR/nginx.conf.prepatch" "$ROOT/$TARGET/openweb-ui/nginx.conf"
(cd "$ROOT/$TARGET/openweb-ui" && docker compose -f docker-compose.yml up -d)
```

## Notes
- This patch only changes `openweb-ui/nginx.conf`.
- It does not touch `.env`, LiteLLM config, LDAP settings, or any other service files.
- If other devices still cannot access the DNS names after this, that is likely DNS/network reachability outside the app stack.
