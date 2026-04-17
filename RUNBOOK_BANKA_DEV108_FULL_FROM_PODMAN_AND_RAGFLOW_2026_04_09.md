# Banka Dev 108 Runtime Runbook

Date: 2026-04-16

Use this for the live Banka dev `10.11.115.108` path only.

Operator note:

- these commands assume you already switched to the target machine and, when needed, already became `root`
- the runbook intentionally does not repeat `sudo su -`

Scope:

- single-node only
- dev defaults to HTTPS on the nginx endpoints while keeping direct HTTP IP:port access exposed
- no passive node
- no LB in the runtime path
- Podman may already be configured
- installer tree may already be extracted
- Ragflow export archive may already be present under `/tmp`

Current images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r30`
- dev encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`

Current dev names:

- `zfgasistan-yzyonetim-dev.ziraat.bank`
- `manavgat-yzyonetim-dev.ziraat.bank`
- `aykal-yzyonetim-dev.ziraat.bank`
- `mercek-yzyonetim-dev.ziraat.bank`
- `mecra-yzyonetim-dev.ziraat.bank`

Direct fallback access:

- OpenWebUI: `http://10.11.115.108:8080`
- LiteLLM: `http://10.11.115.108:4000`
- n8n: `http://10.11.115.108:5678`
- Langfuse: `http://10.11.115.108:3000`
- Ragflow: `http://10.11.115.108:8100`
- Qdrant: disabled by default; ignore qdrant health unless explicitly enabled

Expected default HTTPS DNS access:

- `https://zfgasistan-yzyonetim-dev.ziraat.bank`
- `https://manavgat-yzyonetim-dev.ziraat.bank`
- `https://aykal-yzyonetim-dev.ziraat.bank`
- `https://mercek-yzyonetim-dev.ziraat.bank`
- `https://mecra-yzyonetim-dev.ziraat.bank`

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
you want the refreshed `r30` installer content:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r30
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r30 \
  /output
```

## 3) Apply The Dev Encrypted Config

Run on `10.11.115.108`:

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Verify the rendered dev inputs:

```bash
grep -E '^(NODE_ROLE|PRIMARY_HOST|PASSIVE_SSH_HOST|OPENWEBUI_PUBLIC_HOST|LITELLM_PUBLIC_HOST|LANGFUSE_PUBLIC_HOST|RAGFLOW_PUBLIC_HOST|PUBLIC_URL_SCHEME|DIRECT_PUBLIC_BASE_SCHEME|DIRECT_PUBLIC_BASE_HOST|LITELLM_BROWSER_URL|LANGFUSE_BROWSER_URL|OPENWEBUI_NGINX_CONFIG_PATH|RESET_NON_RAGFLOW_ON_FIRST_ACTIVE_BOOTSTRAP|PRE_CLEAN_INSTALL_ATTEMPT)=' \
  /opt/orbina/incoming/ha.vm1.env || true
```

Expected:

- `PRIMARY_HOST=10.11.115.108`
- `PASSIVE_SSH_HOST=127.0.0.1`
- `PUBLIC_URL_SCHEME=https`
- `DIRECT_PUBLIC_BASE_SCHEME=http`
- `DIRECT_PUBLIC_BASE_HOST=10.11.115.108`
- `LITELLM_BROWSER_URL=https://manavgat-yzyonetim-dev.ziraat.bank`
- `LANGFUSE_BROWSER_URL=https://mercek-yzyonetim-dev.ziraat.bank`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf`
- `RESET_NON_RAGFLOW_ON_FIRST_ACTIVE_BOOTSTRAP=true`
- `PRE_CLEAN_INSTALL_ATTEMPT=true`
- installer copies `/tmp/cert.pem` and `/tmp/private.key` when present; otherwise it generates self-signed fallback cert files under `/etc/pki/tls`
- qdrant is not part of the default health path

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

The refreshed `r30` bundle now does all of this in the canonical path:

- pre-cleans leftover containers and failed compose state from earlier tries
- uses the Banka full nginx config by default
- performs a one-time destructive reset for all non-Ragflow app state
- recreates non-Ragflow DBs and users from zero during startup
- preserves and restores Ragflow data when the export is present
- starts RAGFlow with the required `elasticsearch` and `cpu` Compose profiles before nginx/OpenWebUI
- treats RAGFlow as mandatory but keeps readiness/smoke checks advisory by default; set `STRICT_INSTALL_HEALTH_CHECKS=true` only when you want failed health probes to stop the install
- disables qdrant by default
- writes HTTPS browser URLs for LiteLLM and Langfuse while keeping `http://10.11.115.108:4000` and `http://10.11.115.108:3000` available as direct fallback
- includes the Redis/Langfuse bootstrap fix
- includes the fixed LiteLLM `custom_auth.py` for UI/admin login

## 6) Validate Dev 108

Run on `10.11.115.108`:

```bash
test -f /var/lib/internal-services-ha/banka_non_ragflow_reset_complete
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl --failed --no-pager || true
curl -fsS http://127.0.0.1:18081/ready
curl -I http://127.0.0.1:4000/ || true
curl -I http://127.0.0.1:3000/ || true
podman exec nginx-proxy nginx -t
podman exec nginx-proxy wget -qO- http://127.0.0.1:8081/health
curl -kI --resolve zfgasistan-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://zfgasistan-yzyonetim-dev.ziraat.bank/
curl -kI --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://manavgat-yzyonetim-dev.ziraat.bank/
curl -kI --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://mercek-yzyonetim-dev.ziraat.bank/
curl -I http://127.0.0.1:5678/ || true
curl -I http://127.0.0.1:8100/ || true
podman ps --format '{{.Names}}' | grep -E '(^|-)ragflow-cpu(-|$)' || true
podman logs --tail=120 litellm || true
```

Remote checks from your workstation or another server:

```bash
curl -kI https://zfgasistan-yzyonetim-dev.ziraat.bank/
curl -kI https://manavgat-yzyonetim-dev.ziraat.bank/
curl -kI https://mercek-yzyonetim-dev.ziraat.bank/
curl -I http://10.11.115.108:5678/
curl -I http://10.11.115.108:8100/
```

## 7) Notes

- Dev now defaults to HTTPS DNS/browser URLs and the full nginx config.
- The direct IP:port URLs above remain available as the fallback bring-up path.
- Direct IP and service ports remain useful for fallback and debugging.
- `observability-cadvisor` may still restart on Podman with Docker/containerd discovery errors; that does not block `:18081/ready`.
- The non-Ragflow fresh reset is one-shot; later reruns of the active bootstrap do not wipe again once the marker exists.
