# Banka Dev 108 Runtime Runbook

Date: 2026-04-16

Use this for the live Banka dev `10.11.115.108` path only.

Operator note:

- these commands assume you already switched to the target machine and, when
  needed, already became `root`
- the runbook intentionally does not repeat `sudo su -`

Scope:

- single-node only
- HTTP-first
- no passive node
- no LB in the runtime path
- Podman may already be configured
- installer tree may already be extracted
- Ragflow export archive may already be present under `/tmp`

Current images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22`
- dev encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-16-r3`

Current dev names:

- `zfgasistan-yzyonetim-dev.ziraat.bank`
- `manavgat-yzyonetim-dev.ziraat.bank`
- `aykal-yzyonetim-dev.ziraat.bank`
- `mercek-yzyonetim-dev.ziraat.bank`
- `mecra-yzyonetim-dev.ziraat.bank`

Direct first-deploy access:

- OpenWebUI: `http://10.11.115.108:8080`
- LiteLLM: `http://10.11.115.108:4000`
- n8n: `http://10.11.115.108:5678`
- Langfuse: `http://10.11.115.108:3000`
- Ragflow: `http://10.11.115.108:8100`
- Qdrant: `http://10.11.115.108:6333`

## 1) Reuse The Current Machine State

Run on `10.11.115.108`:

```bash
podman --version
docker version
docker compose version || docker-compose --version || podman compose version || podman-compose --version

test -d /opt/orbina/internal_services && echo "installer tree already extracted"
ls -ld /opt/orbina /opt/orbina/internal_services 2>/dev/null || true
podman images | egrep 'internal-services-katilim-install|internal-services-katilim-config-encrypted' || true
ls -lh /tmp/*ragflow*.tar.gz 2>/dev/null || true
```

If Podman and compose already work, do not rerun the full Podman bootstrap.

## 2) Reuse Or Extract The Installer Bundle

Run on `10.11.115.108` only if `/opt/orbina/internal_services` is missing or
you want the refreshed `r22` installer content:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22 \
  /output
```

## 3) Apply The Dev Encrypted Config

Run on `10.11.115.108`:

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-16-r3
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-16-r3 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Verify the rendered dev inputs:

```bash
grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|OPENWEBUI_PUBLIC_HOST|LITELLM_PUBLIC_HOST|LANGFUSE_PUBLIC_HOST|RAGFLOW_PUBLIC_HOST|OPENWEBUI_NGINX_CONFIG_PATH)=' \
  /opt/orbina/incoming/ha.vm1.env || true
```

Expected:

- `PRIMARY_HOST=10.11.115.108`
- `PASSIVE_SSH_HOST=127.0.0.1`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- new `*-yzyonetim-dev.ziraat.bank` hostnames

## 4) Reuse Or Stage The Ragflow Export

If `/opt/orbina/incoming/ragflow_volumes_export/volume-names.txt` already
exists, keep using it and skip this step.

If you already have a Ragflow export archive under `/tmp`, unpack it directly on
`108`:

```bash
RAGFLOW_ARCHIVE=/tmp/<your-ragflow-export>.tar.gz
mkdir -p /opt/orbina/incoming
rm -rf /opt/orbina/incoming/ragflow_volumes_export
TMP_EXTRACT_DIR=$(mktemp -d)
tar -C "$TMP_EXTRACT_DIR" -xzf "$RAGFLOW_ARCHIVE"
EXTRACTED_DIR=$(find "$TMP_EXTRACT_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)
mv "$EXTRACTED_DIR" /opt/orbina/incoming/ragflow_volumes_export
test -f /opt/orbina/incoming/ragflow_volumes_export/SHA256SUMS.txt
```

If you still need to create the export from ZT ARF dev, use:

- `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`

## 5) Install And Bootstrap Dev 108

Run on `10.11.115.108`:

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role active \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm1-active.sh
```

The refreshed `r22` bundle already includes:

- the Redis/Langfuse bootstrap fix
- the Banka dev PostgreSQL HA skip on single-node `108`
- the fixed LiteLLM `custom_auth.py` for UI/admin login

## 6) Validate Dev 108

Run on `10.11.115.108`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl --failed --no-pager || true
curl -fsS http://127.0.0.1:18081/ready
curl -I http://127.0.0.1:8080/ || true
curl -I http://127.0.0.1:4000/ || true
curl -I http://127.0.0.1:3000/ || true
curl -I http://127.0.0.1:5678/ || true
curl -I http://127.0.0.1:8100/ || true
podman logs --tail=120 litellm || true
```

Remote checks from your workstation or another server:

```bash
curl -I http://10.11.115.108:8080/
curl -I http://10.11.115.108:4000/
curl -I http://10.11.115.108:3000/
curl -I http://10.11.115.108:5678/
curl -I http://10.11.115.108:8100/
```

## 7) Notes

- Dev runtime stays HTTP-first.
- Optional node-local dev cert placement is documented only in:
  - `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`
- If you must temporarily force all public URLs to direct IP/port values, the
  separate IP/port troubleshooting patch remains available, but it is not part
  of the normal Banka runtime path.
