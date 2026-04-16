# Banka Prod 106/107 One Full Runbook

Date: 2026-04-15

Use this single runbook for the banka production rollout.

Scope:
- `10.11.115.106` is VM1 active first
- `10.11.115.107` is VM2 passive later
- no load balancer at first
- HTTP first
- Podman runtime through `docker` and `docker compose`
- Ragflow data is seeded only on VM1

Banka 106/107 SSH trust runbook:

```text
/opt/orbina/internal_services/RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md
```

Published images:
- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21`
- prod encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2`

The prod encrypted config image was not regenerated for this handoff. Rebuilding
it creates new generated service secrets, so keep using `r2` unless you
intentionally want a new prod secret set and passphrase.

Verified image digests:
- installer: verify externally with `docker buildx imagetools inspect docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21`
- prod encrypted config: `sha256:6934557c4c37baf0fcba549998fc790e743bc7e690cd69ced7438e3e6cffabaa`

All scripts and templates used in this runbook are pulled from Docker Hub onto
the company servers.

Target install root:
- `/opt/orbina`

Ragflow export upload target on VM1 only:
- `10.11.115.106:/opt/orbina/incoming/ragflow_volumes_export`

Do not upload Ragflow export to:
- `10.11.115.107`

Prod names:
- `zfgasistan.yzyonetim.ziraat.bank`
- `manavgat.yzyonetim.ziraat.bank`
- `aykal.yzyonetim.ziraat.bank`
- `mercek.yzyonetim.ziraat.bank`
- `mecra.yzyonetim.ziraat.bank`

Direct first-deploy access on VM1:
- OpenWebUI: `http://10.11.115.106:8080`
- LiteLLM: `http://10.11.115.106:4000`
- n8n: `http://10.11.115.106:5678`
- Langfuse: `http://10.11.115.106:3000`
- Ragflow/Mecra: `http://10.11.115.106:8100`
- Qdrant: `http://10.11.115.106:6333`

## 1) Export Ragflow Data From The ZT ARF Dev Server

On the ZT ARF dev server, pull the installer bundle from Docker Hub and extract
the script package there:

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

## 2) Prepare Podman On VM1 106

SSH to VM1:

```bash
ssh root@10.11.115.106
```

Run:

```bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
BACKUP=/root/podman-bootstrap-backup_$TS
NEW_GRAPHROOT=/root/docker-data/containers/storage
mkdir -p "$BACKUP"

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

DRIVER=$(podman info --format '{{.Store.GraphDriverName}}')
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
docker version
docker compose version || docker-compose --version || podman compose version || podman-compose --version
```

Expected:
- `graphroot=/root/docker-data/containers/storage`
- `docker version` works
- `docker compose version`, `docker-compose --version`, `podman compose version`, or `podman-compose --version` works

## 3) Optional: Create The Prod CSR

You can do this before or after the first HTTP deployment. It is not required for the first plain-HTTP bootstrap.

On VM1 after the installer bundle has been extracted:

```bash
cd /opt/orbina/internal_services
mkdir -p ops/install/katilim/certs/generated

cp ops/install/katilim/certs/prod-lb-openssl.cnf.example \
  ops/install/katilim/certs/generated/prod-lb-openssl.cnf

vim ops/install/katilim/certs/generated/prod-lb-openssl.cnf
```

Replace:

```text
<STATE_OR_PROVINCE>
<CITY>
<COMPANY_NAME>
<UNIT_NAME>
<CONTACT_EMAIL>
```

Before the real LB exists:
- keep `IP.1 = 10.11.115.106` if the cert will be temporarily installed on VM1
- change `IP.1` to the real LB/VIP when the LB is assigned

Generate:

```bash
openssl req -new -newkey rsa:4096 -nodes \
  -keyout ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.key \
  -out ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr \
  -config ops/install/katilim/certs/generated/prod-lb-openssl.cnf

openssl req -in ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr \
  -noout -subject -text | grep -A1 "Subject Alternative Name"
```

Send only this file to the certificate team:

```text
ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr
```

Do not send the private key:

```text
ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.key
```

Full CSR notes:
- `RUNBOOK_BANKA_CSR_GENERATION_DEV_AND_PROD_2026_04_13.md`

## 4) Extract Installer And Prod Encrypted Config On VM1 106

On VM1:

```bash
ssh root@10.11.115.106
mkdir -p /opt/orbina

if [ -d /opt/orbina/internal_services/ops/install/katilim/certs/generated ]; then
  TS=$(date +%Y%m%d_%H%M%S)
  mkdir -p "/root/orbina-generated-certs-backup_$TS"
  cp -a /opt/orbina/internal_services/ops/install/katilim/certs/generated \
    "/root/orbina-generated-certs-backup_$TS/"
fi

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output

find /opt/orbina -name '._*' -delete
find /opt/orbina -name '.DS_Store' -delete

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE

grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|CONTAINER_ENGINE|CONTAINER_TLS_VERIFY)=' \
  /opt/orbina/incoming/ha.vm1.env || true
```

If the existing `r2` prod config pack does not print `CONTAINER_ENGINE` or
`CONTAINER_TLS_VERIFY`, continue. The `r18` installer scripts default to
`podman` and `CONTAINER_TLS_VERIFY=false`.

This restores:
- `/opt/orbina/internal_services/.../.env`
- `/opt/orbina/internal_services/ragflow/docker/.env`
- `/opt/orbina/incoming/ha.vm1.env`
- `/opt/orbina/incoming/ha.vm2.env`

## 5) Transfer Ragflow Export To VM1 106

Preferred path: on the ZT ARF dev server, copy the export directly to VM1.
This avoids any dependency on an operator-side machine reaching both servers.

```bash
TARGET_HOST=10.11.115.106
EXPORT_DIR="${EXPORT_DIR:-/root/ragflow_volumes_export_<timestamp>}"

test -d "$EXPORT_DIR"
ssh root@"$TARGET_HOST" "mkdir -p /opt/orbina/incoming/ragflow_volumes_export"
rsync -a "${EXPORT_DIR}/" root@"$TARGET_HOST":/opt/orbina/incoming/ragflow_volumes_export/
```

If direct ZT ARF dev -> VM1 SSH/rsync is not allowed, move `$ARCHIVE_PATH`
through your approved internal file-transfer route, place it on VM1, and
extract it there:

```bash
ARCHIVE_PATH=/root/ragflow_volumes_export_<timestamp>.tar.gz
mkdir -p /tmp/ragflow-import
tar -xzf "$ARCHIVE_PATH" -C /tmp/ragflow-import
EXPORT_FOLDER=$(find /tmp/ragflow-import -maxdepth 1 -type d -name 'ragflow_volumes_export_*' | head -n 1)

mkdir -p /opt/orbina/incoming/ragflow_volumes_export
rsync -a "${EXPORT_FOLDER}/" /opt/orbina/incoming/ragflow_volumes_export/
```

Verify on VM1:

```bash
ssh root@10.11.115.106
ls -lh /opt/orbina/incoming/ragflow_volumes_export
cat /opt/orbina/incoming/ragflow_volumes_export/volume-names.txt
```

Do this before bootstrap. `bootstrap-vm1-active.sh` auto-restores from this path.

## 6) Install And Bootstrap VM1 Active

On VM1:

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

## 7) Validate VM1 Active

On VM1:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
docker ps --format 'table {{.Names}}\t{{.Status}}'

curl -I http://10.11.115.106:8080/
curl -fsS http://10.11.115.106:4000/health
curl -I http://10.11.115.106:5678/
curl -I http://10.11.115.106:3000/
curl -I http://10.11.115.106:8100/
curl -fsS http://10.11.115.106:6333/health
```

Hostname checks from VM1:

```bash
curl -I --resolve zfgasistan.yzyonetim.ziraat.bank:80:127.0.0.1 http://zfgasistan.yzyonetim.ziraat.bank/
curl -fsS --resolve manavgat.yzyonetim.ziraat.bank:80:127.0.0.1 http://manavgat.yzyonetim.ziraat.bank/health
curl -I --resolve aykal.yzyonetim.ziraat.bank:80:127.0.0.1 http://aykal.yzyonetim.ziraat.bank/
curl -I --resolve mercek.yzyonetim.ziraat.bank:80:127.0.0.1 http://mercek.yzyonetim.ziraat.bank/
curl -I --resolve mecra.yzyonetim.ziraat.bank:80:127.0.0.1 http://mecra.yzyonetim.ziraat.bank/
```

Expected:
- `/ready` returns `200`
- LiteLLM `/health` returns success
- Qdrant `/health` returns success
- Ragflow/Mecra answers on `:8100`

## 8) Optional Temporary `/etc/hosts`

On your client machine before real DNS exists:

```text
10.11.115.106 zfgasistan.yzyonetim.ziraat.bank
10.11.115.106 manavgat.yzyonetim.ziraat.bank
10.11.115.106 aykal.yzyonetim.ziraat.bank
10.11.115.106 mercek.yzyonetim.ziraat.bank
10.11.115.106 mecra.yzyonetim.ziraat.bank
```

## 9) Stop Here If VM2 Is Not Ready Yet

At this point production can run from VM1 only.

Do not point traffic to VM2 before the passive bootstrap and validation below.

## 10) Prepare Podman On VM2 107 Later

SSH to VM2:

```bash
ssh root@10.11.115.107
```

Run the same Podman setup block from section 2 on VM2. Then verify:

```bash
podman info --format 'graphroot={{.Store.GraphRoot}} driver={{.Store.GraphDriverName}}'
docker version
docker compose version || docker-compose --version || podman compose version || podman-compose --version
```

## 11) Extract Installer And Prod Encrypted Config On VM2 107

On VM2:

```bash
mkdir -p /opt/orbina

if [ -d /opt/orbina/internal_services/ops/install/katilim/certs/generated ]; then
  TS=$(date +%Y%m%d_%H%M%S)
  mkdir -p "/root/orbina-generated-certs-backup_$TS"
  cp -a /opt/orbina/internal_services/ops/install/katilim/certs/generated \
    "/root/orbina-generated-certs-backup_$TS/"
fi

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output

find /opt/orbina -name '._*' -delete
find /opt/orbina -name '.DS_Store' -delete

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE

grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|CONTAINER_ENGINE|CONTAINER_TLS_VERIFY)=' \
  /opt/orbina/incoming/ha.vm2.env || true
```

If the existing `r2` prod config pack does not print `CONTAINER_ENGINE` or
`CONTAINER_TLS_VERIFY`, continue. The `r18` installer scripts default to
`podman` and `CONTAINER_TLS_VERIFY=false`.

Do not upload the Ragflow export to VM2.

## 12) Install And Bootstrap VM2 Passive

On VM2:

```bash
sudo su -
cd /opt/orbina/internal_services

bash ops/install/katilim/install-node.sh \
  --role passive \
  --ha-env-source /opt/orbina/incoming/ha.vm2.env \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

bash ops/install/katilim/bootstrap-vm2-passive.sh
```

Important:
- Run install/bootstrap commands from a root login shell (`sudo su -`).
- Do not prefix these script calls with `sudo` after entering root shell.

## 13) Enable Sync On VM1

On VM1:

```bash
ssh root@10.11.115.106
sudo su -
cd /opt/orbina/internal_services
bash ops/install/katilim/enable-vm1-passive-sync.sh
```

## 14) Validate Active/Passive

On VM1:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
systemctl status internal-services-ha-sync-light.timer --no-pager
systemctl status internal-services-ha-sync-heavy.timer --no-pager
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();"
```

Expected:
- `/ready` is `200`
- `pg_is_in_recovery()` is `f`
- sync timers are active on VM1

On VM2:

```bash
ssh root@10.11.115.107
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
systemctl status internal-services-ha-sync-light.timer --no-pager || true
systemctl status internal-services-ha-sync-heavy.timer --no-pager || true
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();"
```

Expected:
- `/ready` is `503`
- `pg_is_in_recovery()` is `t`
- sync timers are not active on VM2

## 15) LB And TLS Later

Until the LB exists:
- keep DNS or `/etc/hosts` pointed at `10.11.115.106`
- do not route traffic to `10.11.115.107`

When LB/TLS is ready:
- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`

Recommended model:
- terminate TLS on the LB
- forward HTTP from LB to active nginx on port `80`
- keep `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`

Node-local nginx TLS fallback is also documented in:
- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`
