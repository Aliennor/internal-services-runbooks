# Banka Dev 108 Install Runbook (r34)

Date: 2026-04-17

Target: `10.11.115.108` (single-node dev, HTTPS + direct fallback).

Images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r34`
- encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`

DNS (HTTPS):

- `https://zfgasistan-yzyonetim-dev.ziraat.bank`
- `https://manavgat-yzyonetim-dev.ziraat.bank`
- `https://aykal-yzyonetim-dev.ziraat.bank`
- `https://mercek-yzyonetim-dev.ziraat.bank`
- `https://mecra-yzyonetim-dev.ziraat.bank`

Direct fallback on `10.11.115.108`: OpenWebUI `:8080`, LiteLLM `:4000`, n8n `:5678`, Langfuse `:3000`, Ragflow `:8100`. Qdrant disabled.

All commands run on `10.11.115.108` as root.

## 1) Extract The Installer Bundle

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r34
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r34 \
  /output
```

Skip if `/opt/orbina/internal_services` already holds the r34 tree.

## 2) Apply The Encrypted Config

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

Sanity check the rendered env:

```bash
grep -E '^(PRIMARY_HOST|PUBLIC_URL_SCHEME|DIRECT_PUBLIC_BASE_HOST|LITELLM_BROWSER_URL|LANGFUSE_BROWSER_URL)=' \
  /opt/orbina/incoming/ha.vm1.env
```

Expect `PRIMARY_HOST=10.11.115.108`, `PUBLIC_URL_SCHEME=https`, `DIRECT_PUBLIC_BASE_HOST=10.11.115.108`, LiteLLM/Langfuse browser URLs on `*-yzyonetim-dev.ziraat.bank`.

## 3) Stage The Ragflow Export

Skip if `/opt/orbina/incoming/ragflow_volumes_export/volume-names.txt` already exists.

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

To produce a fresh export, see `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`.

## 4) Install And Bootstrap

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role active \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm1-active.sh
```

Bootstrap pre-cleans old containers, resets non-Ragflow app state, restores Ragflow data when present, starts RAGFlow (`elasticsearch` + `cpu` profiles), and recreates nginx with host-published upstreams. Readiness/smoke checks are advisory; set `STRICT_INSTALL_HEALTH_CHECKS=true` to make them fatal.

## 5) Validate

Local on `108`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -fsS http://127.0.0.1:18081/ready
curl -I http://127.0.0.1:4000/
curl -I http://127.0.0.1:3000/
podman exec nginx-proxy nginx -t
curl -kI --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://manavgat-yzyonetim-dev.ziraat.bank/
curl -kI --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 https://mercek-yzyonetim-dev.ziraat.bank/
```

Remote:

```bash
curl -kI https://zfgasistan-yzyonetim-dev.ziraat.bank/
curl -kI https://manavgat-yzyonetim-dev.ziraat.bank/
curl -kI https://mercek-yzyonetim-dev.ziraat.bank/
```

## 6) Operator Tools Shipped In The Bundle

Available under `/opt/orbina/internal_services/ops/repair/`:

- `banka-apply-ip-port-mode.sh` – switch nginx between DNS/HTTPS and direct IP:port mode.
- `banka-stack-control.sh` – start/stop/status the Banka service set without re-running bootstrap.
- `banka-reset-non-ragflow-app-state.sh` – destructively reset LiteLLM/Langfuse/N8N/OpenWebUI state while preserving Ragflow.

Sample LiteLLM env: `/opt/orbina/internal_services/litellm/.env.banka-108-example`.
