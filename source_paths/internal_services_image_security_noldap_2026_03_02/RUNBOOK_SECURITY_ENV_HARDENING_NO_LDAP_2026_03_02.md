# Runbook: Security Hardening + Non-LDAP LiteLLM Rollout (DEV ONLY)

Date: 2026-03-02
Patch image (example tag): `docker.io/aliennor/redis-internal-services-security-noldap-20260302:0.1.0`

## Goal
Apply security `.env` hardening changes and remove LiteLLM LDAP adaptations for `internal_services_dev` only.

## 0) Build and Push Patch Image (from workstation)

```bash
cd internal_services_image_security_noldap_2026_03_02

IMG="docker.io/aliennor/redis-internal-services-security-noldap-20260302:0.1.0"
docker buildx build --platform linux/amd64 -t "$IMG" --push .
```

Optional digest pinning:

```bash
docker buildx imagetools inspect "$IMG"
```

## 1) Pull and Extract Patch on Server

```bash
IMG="docker.io/aliennor/redis-internal-services-security-noldap-20260302:0.1.0"
ROOT="/opt/orbina"
TARGET="internal_services_dev"
STAGE="$ROOT/internal_services_image_security_noldap_20260302"

sudo mkdir -p "$STAGE"
docker pull "$IMG"
CID=$(docker create "$IMG")
docker cp "$CID":/etc/redis/patches/. "$STAGE"/
docker rm "$CID"

find "$STAGE/$TARGET" -maxdepth 3 -type f | sort
```

## 2) Create Rollback Backup and Save It (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="$ROOT/rollback_snapshots"
BACKUP_DIR="$BACKUP_ROOT/security_env_noldap_${TARGET}_$STAMP"

mkdir -p "$BACKUP_DIR"

tar -C "$ROOT" -czf "$BACKUP_DIR/${TARGET}_prepatch.tgz" \
  "$TARGET/litellm" \
  "$TARGET/langfuse" \
  "$TARGET/n8n" \
  "$TARGET/observability" \
  "$TARGET/openweb-ui" \
  "$TARGET/qdrant" \
  "$TARGET/shared-postgres"

sha256sum "$BACKUP_DIR/${TARGET}_prepatch.tgz" > "$BACKUP_DIR/SHA256SUMS.txt"

# Optional off-host copy for safekeeping
# cp -a "$BACKUP_DIR" /mnt/backup/rollback_snapshots/

ls -lah "$BACKUP_DIR"
cat "$BACKUP_DIR/SHA256SUMS.txt"
```

## 3) Preflight `.env` Check (Compatibility Fill)

This rollout expects secrets in `.env`. Missing keys are auto-filled with compatibility defaults.

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
COMPAT_FILL_MISSING=1   # set 0 to fail instead of auto-fill

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

BASE="$ROOT/$TARGET"

ensure_key "$BASE/litellm/.env" LITELLM_DB_PASSWORD "<LITELLM_DB_PASSWORD>"
ensure_key "$BASE/litellm/.env" LITELLM_MASTER_KEY "sk-change-this-key"
ensure_key "$BASE/litellm/.env" LITELLM_SALT_KEY "sk-change-this-salt"
ensure_key "$BASE/litellm/.env" LANGFUSE_PUBLIC_KEY "pk-lf-change-me"
ensure_key "$BASE/litellm/.env" LANGFUSE_SECRET_KEY "sk-lf-change-me"

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

ensure_key "$BASE/n8n/.env" N8N_DB_PASSWORD "<N8N_DB_PASSWORD>"
ensure_key "$BASE/n8n/.env" N8N_BASIC_AUTH_PASSWORD "<CHANGE_THIS_PASSWORD>"

ensure_key "$BASE/observability/.env" GRAFANA_ADMIN_PASSWORD "<CHANGE_THIS_PASSWORD>"
ensure_key "$BASE/openweb-ui/.env" WEBUI_SECRET_KEY "change-this-secret-key"
ensure_key "$BASE/qdrant/.env" QDRANT_API_KEY "change-this-api-key"

ensure_key "$BASE/shared-postgres/.env" POSTGRES_PASSWORD "<CHANGE_THIS_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" N8N_DB_PASSWORD "<N8N_DB_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" LITELLM_DB_PASSWORD "<LITELLM_DB_PASSWORD>"
ensure_key "$BASE/shared-postgres/.env" LANGFUSE_DB_PASSWORD "<LANGFUSE_DB_PASSWORD>"
```

## 4) Apply Patch Files (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
STAGE="$ROOT/internal_services_image_security_noldap_20260302"

cp -a "$STAGE/$TARGET/." "$ROOT/$TARGET/"
```

## 5) Remove LDAP LiteLLM Artifacts (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"

rm -f "$ROOT/$TARGET/litellm/custom_auth.ldap-observability.py"
rm -f "$ROOT/$TARGET/litellm/custom_logging_callback.ldap-observability.py"
rm -f "$ROOT/$TARGET/litellm/docker-compose.ldap-observability.yml"
rm -f "$ROOT/$TARGET/litellm/litellm_config.ldap-observability.yaml"
rm -f "$ROOT/$TARGET/litellm/.env.ldap-observability.example"
```

## 6) Secure `.env` File Permissions (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"

for F in \
  "$ROOT/$TARGET/litellm/.env" \
  "$ROOT/$TARGET/langfuse/.env" \
  "$ROOT/$TARGET/n8n/.env" \
  "$ROOT/$TARGET/observability/.env" \
  "$ROOT/$TARGET/openweb-ui/.env" \
  "$ROOT/$TARGET/qdrant/.env" \
  "$ROOT/$TARGET/shared-postgres/.env"; do
  [ -f "$F" ] && chmod 600 "$F"
done
```

## 7) Validate Compose Before Restart (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
BASE="$ROOT/$TARGET"

check_compose() {
  D="$1"; C="$2"
  [ -f "$D/$C" ] || return 0
  (cd "$D" && docker compose -f "$C" config >/dev/null)
  echo "OK: $D/$C"
}

check_compose "$BASE/litellm" docker-compose.yml
check_compose "$BASE/langfuse" docker-compose.yml
check_compose "$BASE/langfuse" docker-compose.yaml
check_compose "$BASE/n8n" docker-compose.yml
check_compose "$BASE/observability" docker-compose.yml
check_compose "$BASE/openweb-ui" docker-compose.yml
check_compose "$BASE/qdrant" docker-compose.yaml
check_compose "$BASE/shared-postgres" docker-compose.yml
```

## 8) Restart Affected Services (DEV)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
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

## 9) Post-Deploy Smoke Checks

```bash
# LiteLLM
curl -fsS http://127.0.0.1:4000/health && echo "LiteLLM OK"

# Langfuse
curl -fsS http://127.0.0.1:3001 >/dev/null && echo "Langfuse OK"

# OpenWebUI
curl -kfsS https://127.0.0.1/ >/dev/null && echo "OpenWebUI OK"

# Recent app errors
for C in litellm langfuse-web openwebui n8n; do
  docker logs --since 5m "$C" 2>&1 | grep -Ei "error|exception|fatal|traceback" || true
done
```

## 10) Rollback (Restore Saved DEV Snapshot)

```bash
ROOT="/opt/orbina"
TARGET="internal_services_dev"
BACKUP_DIR="/opt/orbina/rollback_snapshots/security_env_noldap_${TARGET}_YYYYmmdd_HHMMSS"

# Verify backup integrity before restore
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS.txt)

# Restore files
tar -C "$ROOT" -xzf "$BACKUP_DIR/${TARGET}_prepatch.tgz"

# Restart restored services
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
- This package is intentionally DEV-only (`internal_services_dev`).
- `openwebui-test` is intentionally excluded.
- LiteLLM remains non-LDAP (CSV-based auth flow).
- Compatibility fill in Step 3 prevents breakage; rotate secrets after rollout.
