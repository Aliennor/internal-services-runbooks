# Banka Prod 106/107 Install Runbook (r37)

Date: 2026-04-17

Targets: `10.11.115.106` (active) and `10.11.115.107` (passive). HTTPS via LB, direct HTTP IP:port retained for fallback.

Images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37`
- encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7`

DNS (HTTPS via LB):

- `https://zfgasistan-yzyonetim.ziraat.bank`
- `https://manavgat-yzyonetim.ziraat.bank`
- `https://aykal-yzyonetim.ziraat.bank`
- `https://mercek-yzyonetim.ziraat.bank`
- `https://mecra-yzyonetim.ziraat.bank`

Direct fallback on `10.11.115.106`: OpenWebUI `:8080`, LiteLLM `:4000`, n8n `:5678`, Langfuse `:3000`, Ragflow `:8100`. Qdrant disabled.

Prerequisite: inter-VM SSH trust between `106` and `107` must be in place. If missing, run `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md` first.

All commands run as root on the indicated host.

## 1) Extract The Installer Bundle On 106

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37 \
  /output
```

## 2) Apply The Encrypted Config On 106

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Sanity check:

```bash
grep -E '^(PRIMARY_HOST|PEER_HOST|PUBLIC_URL_SCHEME|DIRECT_PUBLIC_BASE_HOST|LITELLM_BROWSER_URL|LANGFUSE_BROWSER_URL)=' \
  /opt/orbina/incoming/ha.vm1.env
```

Expect `PRIMARY_HOST=10.11.115.106`, `PEER_HOST=10.11.115.107`, `PUBLIC_URL_SCHEME=https`, `DIRECT_PUBLIC_BASE_HOST=10.11.115.106`.

## 3) Stage The Ragflow Export On 106

Skip if `/opt/orbina/incoming/ragflow_volumes_export/volume-names.txt` already exists. Do not stage on `107`.

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

## 4) Install And Bootstrap 106 As Active

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role active \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm1-active.sh
```

## 5) Prepare 107 With The Same Installer And Config

On `10.11.115.107`:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37 \
  /output

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Sanity check `/opt/orbina/incoming/ha.vm2.env`:

```bash
grep -E '^(PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|PUBLIC_URL_SCHEME|DIRECT_PUBLIC_BASE_HOST)=' \
  /opt/orbina/incoming/ha.vm2.env
```

Expect `PRIMARY_HOST=10.11.115.106`, `PEER_HOST=10.11.115.106`, `PASSIVE_SSH_HOST=10.11.115.106`.

## 6) Install And Bootstrap 107 As Passive

On `10.11.115.107`:

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role passive \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm2-passive.sh
```

The passive path does not run the destructive non-Ragflow reset.

## 7) Enable Sync And Validate On 106

```bash
cd /opt/orbina/internal_services
ops/install/katilim/enable-vm1-passive-sync.sh
```

Validate on `106`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl status internal-services-ha-sync-light.timer --no-pager
systemctl status internal-services-ha-sync-heavy.timer --no-pager
curl -fsS http://127.0.0.1:18081/ready
podman exec nginx-proxy nginx -t
curl -I http://127.0.0.1:4000/
curl -I http://127.0.0.1:3000/
```

Validate on `107`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -i http://127.0.0.1:18081/ready
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();"
```

Remote:

```bash
curl -I https://zfgasistan-yzyonetim.ziraat.bank/
curl -I https://manavgat-yzyonetim.ziraat.bank/
curl -I https://mercek-yzyonetim.ziraat.bank/
curl -I http://10.11.115.106:4000/
curl -I http://10.11.115.106:3000/
```

## 8) Operator Tools Shipped In The Bundle

Available under `/opt/orbina/internal_services/ops/repair/`:

- `banka-apply-ip-port-mode.sh` – switch nginx between DNS/HTTPS and direct IP:port mode.
- `banka-stack-control.sh` – start/stop/status the Banka service set without re-running bootstrap.
- `banka-reset-non-ragflow-app-state.sh` – destructively reset LiteLLM/Langfuse/N8N/OpenWebUI state while preserving Ragflow.

DNS, LB, and prod TLS paths: `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`.

Inter-VM SSH trust: `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md`.
