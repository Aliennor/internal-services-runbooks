# Banka LiteLLM UI/Auth Fix

Date: 2026-04-15
Image: `docker.io/aliennor/internal-services-banka-litellm-ui-auth-fix:2026-04-15-r1`
Dev target: `10.11.115.108`
Prod target: use the same steps with `URL=http://10.11.115.106:4000`.

Fixes LiteLLM `/ui` -> `Open Admin Panel` returning 500 before login. Replaces only:
`/opt/orbina/internal_services/litellm/custom_auth.py`.

## 1. Pull/Extract

Run on `10.11.115.108`:

```bash
sudo su -
IMAGE=docker.io/aliennor/internal-services-banka-litellm-ui-auth-fix:2026-04-15-r1
podman pull --tls-verify=false "$IMAGE"
podman run --rm -v /opt/orbina:/output "$IMAGE" /output
```

## 2. Backup/Apply

```bash
sudo su -
set -eu
ROOT=/opt/orbina/internal_services
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/opt/orbina/backups/banka_litellm_ui_auth_fix_$STAMP"
mkdir -p "$BACKUP_DIR"

# backup
cp -p "$ROOT/litellm/custom_auth.py" "$BACKUP_DIR/custom_auth.py"
cp -p "$ROOT/litellm/.env" "$BACKUP_DIR/.env"
sha256sum "$ROOT/litellm/custom_auth.py" > "$BACKUP_DIR/SHA256SUMS.before"

# apply
cp -p "$ROOT/litellm/custom_auth.py.banka-ui-auth-fix" "$ROOT/litellm/custom_auth.py"
python3 -m py_compile "$ROOT/litellm/custom_auth.py"
sha256sum "$ROOT/litellm/custom_auth.py" > "$BACKUP_DIR/SHA256SUMS.after"
echo "$BACKUP_DIR"
```

## 3. URL Mode

```bash
sudo su -
set -eu
ROOT=/opt/orbina/internal_services
URL=http://10.11.115.108:4000
grep -E '^(PROXY_BASE_URL|LITELLM_PUBLIC_URL)=' "$ROOT/litellm/.env" || true

# force direct IP/port mode
sed -i "s|^PROXY_BASE_URL=.*|PROXY_BASE_URL=$URL|" "$ROOT/litellm/.env"
grep -q '^LITELLM_PUBLIC_URL=' "$ROOT/litellm/.env" \
  && sed -i "s|^LITELLM_PUBLIC_URL=.*|LITELLM_PUBLIC_URL=$URL|" "$ROOT/litellm/.env" \
  || echo "LITELLM_PUBLIC_URL=$URL" >> "$ROOT/litellm/.env"
grep -E '^(PROXY_BASE_URL|LITELLM_PUBLIC_URL)=' "$ROOT/litellm/.env"
```

## 4. Restart/Validate

```bash
sudo su -
cd /opt/orbina/internal_services/litellm

# restart LiteLLM only
CONTAINER_ENGINE=podman timeout 180 podman compose config >/tmp/banka_litellm_compose_config.txt
CONTAINER_ENGINE=podman timeout 180 podman compose down || true
CONTAINER_ENGINE=podman timeout 180 podman compose up -d

# smoke checks
podman exec litellm sh -lc 'env | sort | grep -E "PROXY_BASE_URL|LITELLM_PUBLIC_URL|PORT"'
curl -I --max-time 20 http://127.0.0.1:4000/ui || true
podman logs --tail=160 litellm
```

Open `http://10.11.115.108:4000/ui`, click `Open Admin Panel`, then use:

```bash
grep '^LITELLM_MASTER_KEY=' /opt/orbina/internal_services/litellm/.env
```

## 5. If 500 Remains

```bash
sudo su -
podman logs --tail=300 litellm
curl -v --max-time 30 http://127.0.0.1:4000/ui 2>&1 | tail -100
curl -v --max-time 30 http://127.0.0.1:4000/ui/ 2>&1 | tail -100
podman logs --tail=100 shared_postgres || true
podman exec litellm sh -lc 'python - <<PY
import os
print(os.environ.get("DATABASE_URL", "DATABASE_URL_MISSING"))
PY'
```

## 6. Rollback

Set `BACKUP_DIR` to the directory printed in step 2.

```bash
sudo su -
set -eu
ROOT=/opt/orbina/internal_services
cp -p "$BACKUP_DIR/custom_auth.py" "$ROOT/litellm/custom_auth.py"
cp -p "$BACKUP_DIR/.env" "$ROOT/litellm/.env"

cd "$ROOT/litellm"
CONTAINER_ENGINE=podman timeout 180 podman compose down || true
CONTAINER_ENGINE=podman timeout 180 podman compose up -d
```
