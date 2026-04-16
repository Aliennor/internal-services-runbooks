# Banka Dev 108 Full Runbook: Podman Setup, Ragflow Export, Install

Date: 2026-04-09

Use this when you want to bring up the dev box on `10.11.115.108` first.

Scope:
- source Ragflow data comes from the ZT ARF dev server
- target is `10.11.115.108`
- single-node only
- HTTP first
- no passive node
- no load balancer

Published images used in this runbook:
- `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21`
- `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-14-r2`

All scripts and templates used in this runbook are pulled from Docker Hub onto
the company servers.

Target install root on `108`:
- `/opt/orbina`

Target Ragflow upload path on `108`:
- `/opt/orbina/incoming/ragflow_volumes_export`

Dev names:
- `zfgasistan.yzyonetim-dev.ziraat.bank`
- `manavgat.yzyonetim-dev.ziraat.bank`
- `aykal.yzyonetim-dev.ziraat.bank`
- `mercek.yzyonetim-dev.ziraat.bank`
- `mecra.yzyonetim-dev.ziraat.bank`

Direct first-deploy access on `108`:
- OpenWebUI: `http://10.11.115.108:8080`
- LiteLLM: `http://10.11.115.108:4000`
- n8n: `http://10.11.115.108:5678`
- Langfuse: `http://10.11.115.108:3000`
- Ragflow: `http://10.11.115.108:8100`
- Qdrant: `http://10.11.115.108:6333`

## 1) Export Ragflow Data From The ZT ARF Dev Server

On the ZT ARF dev source server, pull the installer bundle from Docker Hub and
extract the script package there:

```bash
docker version
mkdir -p /opt/orbina-export-tools

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina-export-tools:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output

install -m 0755 \
  /opt/orbina-export-tools/internal_services/ops/install/katilim/export-ragflow-volumes.sh \
  /root/export-ragflow-volumes.sh
```

On the ZT ARF dev server:

```bash
docker version
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker volume ls --format '{{.Name}}' | sort | egrep 'esdata01|minio_data|mysql_data|redis_data|qdrant_data|ragflow'

cd /root
TS=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="/root/ragflow_volumes_export_${TS}"

SELECTED_VOLUME_BASES=esdata01,minio_data,mysql_data,redis_data,qdrant_data \
  /root/export-ragflow-volumes.sh "$EXPORT_DIR"

cd "$EXPORT_DIR"
ls -lh
cat volume-names.txt
test -f SHA256SUMS.txt || {
  echo "Export is incomplete: SHA256SUMS.txt is missing. Do not archive or upload this export."
  exit 1
}
cat SHA256SUMS.txt
```

If you only see `volume-names.txt` and no `SHA256SUMS.txt`, the export failed
before all volume tarballs and checksums were written. Delete that partial
export folder and rerun this section with the current installer script package:

```bash
rm -rf "$EXPORT_DIR"
```

Archive it on the ZT ARF dev server:

```bash
cd /root
EXPORT_BASENAME=$(basename "$EXPORT_DIR")
ARCHIVE_PATH="/root/${EXPORT_BASENAME}.tar.gz"
tar -C /root -czf "$ARCHIVE_PATH" "$EXPORT_BASENAME"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$ARCHIVE_PATH"
else
  shasum -a 256 "$ARCHIVE_PATH"
fi
```

Keep the ZT ARF dev server shell values `EXPORT_DIR` and `ARCHIVE_PATH`; later
steps transfer the export from that source server.

## 2) Prepare Podman On 108

SSH to the target:

```bash
ssh root@10.11.115.108
```

Run the full banka Podman bootstrap on `108`:

```bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
BACKUP=/root/podman-bootstrap-backup_$TS
NEW_GRAPHROOT=/root/docker-data/containers/storage
mkdir -p "$BACKUP"
echo "Backup dir: $BACKUP"

podman --version
podman info --format 'graphroot={{.Store.GraphRoot}} driver={{.Store.GraphDriverName}}'
podman ps -a || true
podman images || true

sudo mkdir -p /etc/containers/registries.conf.d
sudo cp -a /etc/containers/registries.conf "$BACKUP/" 2>/dev/null || true
sudo cp -a /etc/containers/registries.conf.d "$BACKUP/" 2>/dev/null || true
sudo cp -a /etc/containers/storage.conf "$BACKUP/" 2>/dev/null || true

sudo tee /etc/containers/registries.conf.d/100-banka-dockerhub.conf >/dev/null <<'EOF'
unqualified-search-registries = ["docker.io"]
short-name-mode = "enforcing"
EOF

grep -Rni "unqualified-search-registries\|short-name-mode" \
  /etc/containers/registries.conf /etc/containers/registries.conf.d 2>/dev/null || true

DRIVER=$(podman info --format '{{.Store.GraphDriverName}}')
echo "Detected storage driver: $DRIVER"

sudo mkdir -p "$NEW_GRAPHROOT"
sudo chmod 700 /root
sudo mkdir -p /root/docker-data /root/docker-data/containers
sudo chmod 700 /root/docker-data /root/docker-data/containers "$NEW_GRAPHROOT"

if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce)" != "Disabled" ]; then
  command -v semanage >/dev/null 2>&1 || sudo dnf install -y policycoreutils-python-utils
  sudo semanage fcontext -a -e /var/lib/containers/storage "$NEW_GRAPHROOT" || true
  sudo restorecon -R -v /root/docker-data
fi

sudo tee /etc/containers/storage.conf >/dev/null <<EOF
[storage]
driver = "$DRIVER"
runroot = "/run/containers/storage"
graphroot = "$NEW_GRAPHROOT"
EOF

podman info --format 'graphroot={{.Store.GraphRoot}} driver={{.Store.GraphDriverName}}'

docker --version || sudo dnf install -y podman-docker
docker --version

if docker compose version; then
  echo "docker compose is ready"
elif docker-compose --version; then
  echo "docker-compose is ready"
elif podman compose version; then
  echo "podman compose is ready"
elif podman-compose --version; then
  echo "podman-compose is ready"
else
  sudo dnf install -y podman-compose
  podman-compose --version
fi

podman pull --tls-verify=false docker.io/aliennor/alpine:3.20
podman images
sudo du -sh /root/docker-data/containers/storage
docker version
docker compose version || docker-compose --version || podman compose version || podman-compose --version
```

Expected:
- `graphroot=/root/docker-data/containers/storage`
- `docker version` works through Podman compatibility
- `docker compose version`, `docker-compose --version`, `podman compose version`, or `podman-compose --version` works
- `podman pull --tls-verify=false docker.io/aliennor/alpine:3.20` succeeds

Optional compose smoke test on `108` before the installer uses the ports:

```bash
sudo mkdir -p /root/podman-compose-test
sudo tee /root/podman-compose-test/compose.yml >/dev/null <<'EOF'
services:
  web:
    image: docker.io/aliennor/nginx:1.27-alpine
    ports:
      - "18080:80"
EOF

cd /root/podman-compose-test
if docker compose version >/dev/null 2>&1; then
  docker compose up -d
  docker compose ps
  curl -I http://127.0.0.1:18080
  docker compose down
elif docker-compose --version >/dev/null 2>&1; then
  docker-compose up -d
  docker-compose ps
  curl -I http://127.0.0.1:18080
  docker-compose down
elif podman compose version >/dev/null 2>&1; then
  podman compose up -d
  podman compose ps
  curl -I http://127.0.0.1:18080
  podman compose down
else
  podman-compose up -d
  podman-compose ps
  curl -I http://127.0.0.1:18080
  podman-compose down
fi
```

## 3) Optional: Create The Dev CSR

You can do this before or after the HTTP-first install. It is not required for
the first plain-HTTP bootstrap. If you need it, generate it on `108` after the
installer bundle is extracted in section 4.

On `108`, after section 4:

```bash
cd /opt/orbina/internal_services
mkdir -p ops/install/katilim/certs/generated

cp ops/install/katilim/certs/dev-lb-openssl.cnf.example \
  ops/install/katilim/certs/generated/dev-108-openssl.cnf

vim ops/install/katilim/certs/generated/dev-108-openssl.cnf
```

After replacing the placeholder identity fields, generate the CSR:

```bash
openssl req -new -newkey rsa:4096 -nodes \
  -keyout ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.key \
  -out ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.csr \
  -config ops/install/katilim/certs/generated/dev-108-openssl.cnf
```

The dev CSR covers:

```text
zfgasistan.yzyonetim-dev.ziraat.bank
manavgat.yzyonetim-dev.ziraat.bank
aykal.yzyonetim-dev.ziraat.bank
mercek.yzyonetim-dev.ziraat.bank
mecra.yzyonetim-dev.ziraat.bank
10.11.115.108
```

The CSR details above are enough for the first dev CSR. The broader CSR runbook
is still packaged for reference, but it is not required to complete this dev
install flow.

## 4) Extract The Shared Installer Bundle On 108

On `108`:

```bash
mkdir -p /opt/orbina

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output
```

## 5) Extract The Encrypted Config Image On 108

On `108`:

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-14-r2
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-14-r2 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Remove macOS residual files after the installer and encrypted config extraction:

```bash
find /opt/orbina -name '.DS_Store' -type f -delete
find /opt/orbina -name '._*' -type f -delete
find /opt/orbina -name '__MACOSX' -type d -prune -exec rm -rf {} +
```

This restores:
- `/opt/orbina/internal_services/shared-postgres/.env`
- `/opt/orbina/internal_services/langfuse/.env`
- `/opt/orbina/internal_services/litellm/.env`
- `/opt/orbina/internal_services/n8n/.env`
- `/opt/orbina/internal_services/openweb-ui/.env`
- `/opt/orbina/internal_services/observability/.env`
- `/opt/orbina/internal_services/qdrant/.env`
- `/opt/orbina/internal_services/ragflow/docker/.env`
- `/opt/orbina/incoming/ha.vm1.env`
- `/opt/orbina/incoming/ha.vm2.env`

## 6) Transfer The Ragflow Export To 108

Preferred path: on the ZT ARF dev source server, copy the export directly to
`108`.

```bash
TARGET_HOST=10.11.115.108
EXPORT_DIR="${EXPORT_DIR:-/root/ragflow_volumes_export_<timestamp>}"

test -d "$EXPORT_DIR"
ssh root@"$TARGET_HOST" "mkdir -p /opt/orbina/incoming/ragflow_volumes_export"
rsync -a "${EXPORT_DIR}/" root@"$TARGET_HOST":/opt/orbina/incoming/ragflow_volumes_export/
```

If direct ZT ARF dev -> `108` SSH/rsync is not allowed, move
`$ARCHIVE_PATH` through your approved internal file-transfer route, place it on
`108`, and extract it there:

```bash
ARCHIVE_PATH=/root/ragflow_volumes_export_<timestamp>.tar.gz
mkdir -p /tmp/ragflow-import
tar -xzf "$ARCHIVE_PATH" -C /tmp/ragflow-import
EXPORT_FOLDER=$(find /tmp/ragflow-import -maxdepth 1 -type d -name 'ragflow_volumes_export_*' | head -n 1)

mkdir -p /opt/orbina/incoming/ragflow_volumes_export
rsync -a "${EXPORT_FOLDER}/" /opt/orbina/incoming/ragflow_volumes_export/
```

Remove macOS residual files again after the Ragflow export transfer/extract:

```bash
find /opt/orbina/incoming/ragflow_volumes_export -name '.DS_Store' -type f -delete
find /opt/orbina/incoming/ragflow_volumes_export -name '._*' -type f -delete
find /opt/orbina/incoming/ragflow_volumes_export -name '__MACOSX' -type d -prune -exec rm -rf {} +
```

Verify on `108`:

```bash
ssh root@10.11.115.108
ls -lh /opt/orbina/incoming/ragflow_volumes_export
cat /opt/orbina/incoming/ragflow_volumes_export/volume-names.txt
```

Do this before bootstrap. `bootstrap-vm1-active.sh` auto-restores from this path.

## 7) Install And Bootstrap On 108

On `108`:

```bash
sudo su -
cd /opt/orbina/internal_services

bash ops/install/katilim/install-node.sh \
  --role active \
  --ha-env-source /opt/orbina/incoming/ha.vm1.env \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

bash ops/install/katilim/bootstrap-vm1-active.sh
```

Important:
- Run install/bootstrap commands from a root login shell (`sudo su -`).
- Do not prefix these script calls with `sudo` after entering root shell.
- Installer `banka-langfuse-2026-04-15-r21` adds a default 900 second compose timeout (`1200` seconds for the Langfuse systemd unit). If startup cannot complete, the bootstrap exits and prints `ps` plus last logs instead of hanging forever.
- To change the compose timeout for a slow first start, run for example `export CONTAINER_COMPOSE_TIMEOUT_SECONDS=1800` before `bootstrap-vm1-active.sh`.
- For the standalone dev `108` flow, `VM2_HOST=127.0.0.1`, so the bootstrap skips PostgreSQL HA replication setup. That replication setup is only required for the later two-VM prod active/passive path.

Do not run on `108`:

```bash
bash ops/install/katilim/bootstrap-vm2-passive.sh
bash ops/install/katilim/enable-vm1-passive-sync.sh
```

## 8) Validate The Dev Stack

On `108`:

```bash
curl -i http://127.0.0.1:18081/ready
curl -I http://10.11.115.108:8080/
curl -fsS http://10.11.115.108:4000/health
curl -I http://10.11.115.108:5678/
curl -I http://10.11.115.108:3000/
curl -I http://10.11.115.108:8100/
curl -fsS http://10.11.115.108:6333/health
```

If you want hostname checks from the VM itself:

```bash
curl -I --resolve zfgasistan.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://zfgasistan.yzyonetim-dev.ziraat.bank/
curl -fsS --resolve manavgat.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://manavgat.yzyonetim-dev.ziraat.bank/health
curl -I --resolve aykal.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://aykal.yzyonetim-dev.ziraat.bank/
curl -I --resolve mercek.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://mercek.yzyonetim-dev.ziraat.bank/
curl -I --resolve mecra.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://mecra.yzyonetim-dev.ziraat.bank/
```

Expected:
- `/ready` returns `200`
- OpenWebUI, n8n, Langfuse, and Ragflow answer over HTTP
- LiteLLM `/health` returns success
- Qdrant `/health` returns success

## 9) Optional `/etc/hosts` On Your Client Machine

```text
10.11.115.108 zfgasistan.yzyonetim-dev.ziraat.bank
10.11.115.108 manavgat.yzyonetim-dev.ziraat.bank
10.11.115.108 aykal.yzyonetim-dev.ziraat.bank
10.11.115.108 mercek.yzyonetim-dev.ziraat.bank
10.11.115.108 mecra.yzyonetim-dev.ziraat.bank
```

## 10) Stop Point

This file is the single runbook for the dev `108` install path. Do not switch to
the older dev, Podman, or Ragflow-only runbooks unless you are debugging a
specific failed section.
