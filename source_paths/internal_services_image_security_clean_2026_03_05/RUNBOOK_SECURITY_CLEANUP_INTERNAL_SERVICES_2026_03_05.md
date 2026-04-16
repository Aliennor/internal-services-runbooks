# Runbook: Security Cleanup + No LDAP/Keycloak (internal_services)

Date: 2026-03-05
Patch image (example): `docker.io/aliennor/redis-internal-services-security-clean-20260305:0.1.4`

## Goal
Apply security hardening for env/compose handling, remove LDAP/Keycloak artifacts, clean LiteLLM inline tokens (move to `.env`), keep `n8n` on `unrool/n8n-custom:v2`, and preserve rollback capability.

## 0) Build and Push Patch Image (Workstation)

```bash
cd internal_services_image_security_clean_2026_03_05

IMG="docker.io/aliennor/redis-internal-services-security-clean-20260305:0.1.4"
docker buildx build --platform linux/amd64 -t "$IMG" --push .

# Optional digest pinning
docker buildx imagetools inspect "$IMG"
```

## 1) Pull and Extract Patch on Server

```bash
IMG="docker.io/aliennor/redis-internal-services-security-clean-20260305:0.1.4"
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_security_clean_20260305"

sudo mkdir -p "$STAGE"
docker pull "$IMG"
CID=$(docker create "$IMG")
docker cp "$CID":/etc/redis/patches/. "$STAGE"/
docker rm "$CID"

find "$STAGE/$TARGET" -maxdepth 3 -type f | sort
```

## 2) Create Rollback Backup and Save It (Before Changes)

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="$ROOT/rollback_snapshots"
BACKUP_DIR="$BACKUP_ROOT/security_cleanup_${TARGET}_$STAMP"

mkdir -p "$BACKUP_DIR"

tar -C "$ROOT" -czf "$BACKUP_DIR/${TARGET}_prepatch.tgz" \
  "$TARGET/litellm" \
  "$TARGET/langfuse" \
  "$TARGET/n8n" \
  "$TARGET/observability" \
  "$TARGET/openweb-ui" \
  "$TARGET/qdrant" \
  "$TARGET/shared-postgres" \
  "$TARGET/keycloak" \
  "$TARGET/ldap" \
  2>/dev/null || true

sha256sum "$BACKUP_DIR/${TARGET}_prepatch.tgz" > "$BACKUP_DIR/SHA256SUMS.txt"

# Optional off-host backup copy
# cp -a "$BACKUP_DIR" /mnt/backup/rollback_snapshots/

ls -lah "$BACKUP_DIR"
cat "$BACKUP_DIR/SHA256SUMS.txt"
```

## 3) Preflight `.env` Compatibility Fill (No Downtime Surprises)

This step keeps your existing keys working and fills only missing required keys.

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BASE="$ROOT/$TARGET"
COMPAT_FILL_MISSING=1   # set 0 to fail when key is missing

ensure_key() {
  FILE="$1"; KEY="$2"; VAL="$3"
  [ -f "$FILE" ] || return 0
  grep -Eq "^${KEY}=" "$FILE" && return 0
  if [ "$COMPAT_FILL_MISSING" = "1" ]; then
    echo "${KEY}=${VAL}" >> "$FILE"
    echo "[compat-fill] $FILE -> $KEY"
  else
    echo "[missing] $FILE -> $KEY"
    exit 1
  fi
}

# 3.1) Extract existing inline LiteLLM gateway tokens from old litellm_config.yaml (if present)
TMPTOK=$(mktemp)
awk '
  /^[[:space:]]*api_base:/ { base=$0 }
  /^[[:space:]]*api_key:[[:space:]]*eyJ/ {
    token=$2
    if (base ~ /apps\.prod\.ai\.zb/ && prod == "") prod=token
    if (base ~ /apps\.dev\.ai\.zb/ && dev == "") dev=token
  }
  END {
    if (prod != "") print "PROD=" prod
    if (dev != "") print "DEV=" dev
  }
' "$BASE/litellm/litellm_config.yaml" > "$TMPTOK" 2>/dev/null || true

PROD_TOKEN=""
DEV_TOKEN=""
[ -f "$TMPTOK" ] && source "$TMPTOK" || true
[ -n "${PROD:-}" ] && PROD_TOKEN="$PROD"
[ -n "${DEV:-}" ] && DEV_TOKEN="$DEV"
rm -f "$TMPTOK"

# 3.2) Ensure required keys for litellm
ensure_key "$BASE/litellm/.env" LITELLM_DB_PASSWORD "<LITELLM_DB_PASSWORD>"
ensure_key "$BASE/litellm/.env" LITELLM_MASTER_KEY "sk-change-this-key"
ensure_key "$BASE/litellm/.env" LITELLM_SALT_KEY "sk-change-this-salt"
ensure_key "$BASE/litellm/.env" LANGFUSE_PUBLIC_KEY "pk-lf-change-me"
ensure_key "$BASE/litellm/.env" LANGFUSE_SECRET_KEY "sk-lf-change-me"

if [ -n "$PROD_TOKEN" ]; then
  ensure_key "$BASE/litellm/.env" ZIR_TECH_GATEWAY_API_KEY_PROD "$PROD_TOKEN"
else
  ensure_key "$BASE/litellm/.env" ZIR_TECH_GATEWAY_API_KEY_PROD "replace-with-prod-token"
fi

if [ -n "$DEV_TOKEN" ]; then
  ensure_key "$BASE/litellm/.env" ZIR_TECH_GATEWAY_API_KEY_DEV "$DEV_TOKEN"
else
  ensure_key "$BASE/litellm/.env" ZIR_TECH_GATEWAY_API_KEY_DEV "replace-with-dev-token"
fi

# 3.3) Ensure langfuse .env exists + required keys
if [ ! -f "$BASE/langfuse/.env" ]; then
  cat > "$BASE/langfuse/.env" <<'EOL'
NEXTAUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://langfuse_user:<LANGFUSE_DB_PASSWORD>@shared_postgres:5432/langfuse
SALT=mysalt
ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
CLICKHOUSE_PASSWORD=clickhouse
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=<MINIO_SECRET>
LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY=<MINIO_SECRET>
LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY=<MINIO_SECRET>
REDIS_AUTH=<REDIS_AUTH>
NEXTAUTH_SECRET=<NEXTAUTH_SECRET>
MINIO_ROOT_PASSWORD=<MINIO_SECRET>
EOL
fi

ensure_key "$BASE/langfuse/.env" NEXTAUTH_URL "http://localhost:3000"
ensure_key "$BASE/langfuse/.env" DATABASE_URL "postgresql://langfuse_user:<LANGFUSE_DB_PASSWORD>@shared_postgres:5432/langfuse"
ensure_key "$BASE/langfuse/.env" SALT "mysalt"
ensure_key "$BASE/langfuse/.env" ENCRYPTION_KEY "0000000000000000000000000000000000000000000000000000000000000000"
ensure_key "$BASE/langfuse/.env" CLICKHOUSE_PASSWORD "clickhouse"
ensure_key "$BASE/langfuse/.env" LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY "<MINIO_SECRET>"
ensure_key "$BASE/langfuse/.env" LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY "<MINIO_SECRET>"
ensure_key "$BASE/langfuse/.env" LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY "<MINIO_SECRET>"
ensure_key "$BASE/langfuse/.env" REDIS_AUTH "<REDIS_AUTH>"
ensure_key "$BASE/langfuse/.env" NEXTAUTH_SECRET "<NEXTAUTH_SECRET>"
ensure_key "$BASE/langfuse/.env" MINIO_ROOT_PASSWORD "<MINIO_SECRET>"

# 3.4) Ensure required keys in other apps
ensure_key "$BASE/n8n/.env" N8N_DB_PASSWORD "<N8N_DB_PASSWORD>"
ensure_key "$BASE/n8n/.env" N8N_BASIC_AUTH_PASSWORD "<CHANGE_THIS_PASSWORD>"
ensure_key "$BASE/observability/.env" GRAFANA_ADMIN_PASSWORD "<CHANGE_THIS_PASSWORD>"
ensure_key "$BASE/openweb-ui/.env" WEBUI_SECRET_KEY "change-this-secret-key"
ensure_key "$BASE/qdrant/.env" QDRANT_API_KEY "change-this-api-key"

ensure_key "$BASE/shared-postgres/.env" POSTGRES_PASSWORD "<CHANGE_THIS_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" N8N_DB_PASSWORD "<N8N_DB_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" LITELLM_DB_PASSWORD "<LITELLM_DB_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" LANGFUSE_DB_NAME "langfuse"
ensure_key "$BASE/shared-postgres/.env" LANGFUSE_DB_USER "langfuse_user"
ensure_key "$BASE/shared-postgres/.env" LANGFUSE_DB_PASSWORD "<LANGFUSE_DB_PASSWORD>"
```

## 4) Apply Patch Files

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
STAGE="$ROOT/internal_services_image_security_clean_20260305"

cp -a "$STAGE/$TARGET/." "$ROOT/$TARGET/"
```

## 5) Remove LDAP/Keycloak Artifacts

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BASE="$ROOT/$TARGET"

rm -rf "$BASE/keycloak" "$BASE/ldap"
rm -f "$BASE/litellm/docker-compose-keycloak.yml"
rm -f "$BASE/litellm/custom_auth_backup.py"
rm -f "$BASE/litellm/.env.bak_"* "$BASE/litellm/docker-compose.yml.bak_"* 2>/dev/null || true
```

## 6) Secure `.env` Permissions

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BASE="$ROOT/$TARGET"

for F in \
  "$BASE/litellm/.env" \
  "$BASE/langfuse/.env" \
  "$BASE/n8n/.env" \
  "$BASE/observability/.env" \
  "$BASE/openweb-ui/.env" \
  "$BASE/qdrant/.env" \
  "$BASE/shared-postgres/.env"; do
  [ -f "$F" ] && chmod 600 "$F"
done
```

## 7) Validate Compose Before Restart

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BASE="$ROOT/$TARGET"

check_compose() {
  D="$1"; C="$2"
  [ -f "$D/$C" ] || return 0
  (cd "$D" && docker compose -f "$C" config >/dev/null)
  echo "OK: $D/$C"
}

check_compose "$BASE/shared-postgres" docker-compose.yml
check_compose "$BASE/langfuse" docker-compose.yaml
check_compose "$BASE/litellm" docker-compose.yml
check_compose "$BASE/qdrant" docker-compose.yaml
check_compose "$BASE/n8n" docker-compose.yml
check_compose "$BASE/observability" docker-compose.yml
check_compose "$BASE/openweb-ui" docker-compose.yml
```

## 8) Restart Affected Services

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BASE="$ROOT/$TARGET"

restart_dir() {
  D="$1"
  [ -f "$D/docker-compose.yml" ] || [ -f "$D/docker-compose.yaml" ] || return 0
  if [ -f "$D/docker-compose.yml" ]; then
    (cd "$D" && docker compose -f docker-compose.yml up -d)
  else
    (cd "$D" && docker compose -f docker-compose.yaml up -d)
  fi
}

restart_dir "$BASE/shared-postgres"
restart_dir "$BASE/langfuse"
restart_dir "$BASE/litellm"
restart_dir "$BASE/qdrant"
restart_dir "$BASE/n8n"
restart_dir "$BASE/observability"
restart_dir "$BASE/openweb-ui"
```

## 9) Smoke Checks

```bash
# LiteLLM
curl -fsS http://127.0.0.1:4000/health && echo "LiteLLM OK"

# Langfuse
curl -fsS http://127.0.0.1:5000 >/dev/null && echo "Langfuse OK"

# OpenWebUI through nginx
curl -kfsS https://127.0.0.1/ >/dev/null && echo "OpenWebUI OK"

# Quick error scan
for C in litellm langfuse-web openwebui n8n shared_postgres; do
  docker logs --since 5m "$C" 2>&1 | grep -Ei "error|exception|fatal|traceback" || true
done
```

## 10) Rollback (Restore Saved Snapshot)

```bash
ROOT="/opt/orbina"
TARGET="internal_services"
BACKUP_DIR="/opt/orbina/rollback_snapshots/security_cleanup_${TARGET}_YYYYmmdd_HHMMSS"

# Verify snapshot first
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS.txt)

# Restore
[ -f "$BACKUP_DIR/${TARGET}_prepatch.tgz" ] && tar -C "$ROOT" -xzf "$BACKUP_DIR/${TARGET}_prepatch.tgz"

# Restart after restore
for S in shared-postgres langfuse litellm qdrant n8n observability openweb-ui; do
  D="$ROOT/$TARGET/$S"
  [ -d "$D" ] || continue
  if [ -f "$D/docker-compose.yml" ]; then
    (cd "$D" && docker compose -f docker-compose.yml up -d)
  elif [ -f "$D/docker-compose.yaml" ]; then
    (cd "$D" && docker compose -f docker-compose.yaml up -d)
  fi
done
```

## Notes
- `openweb-ui` is included only for `.env` secret hardening. Its LDAP-related settings are intentionally preserved.
- `openweb-ui/nginx.conf` also includes a LiteLLM reverse-proxy fix so `/ui` stays on the DNS hostname instead of redirecting clients to raw IP:port.
- `openwebui-test` is intentionally not touched in this patch.
- `n8n` image remains `aliennor/n8n-oracle:2.4.6-thickfix2`.
- LiteLLM inline gateway tokens are removed from config and loaded from `.env`.
- If your target folder is `internal_services_dev`, set `TARGET="internal_services_dev"` in all steps.
