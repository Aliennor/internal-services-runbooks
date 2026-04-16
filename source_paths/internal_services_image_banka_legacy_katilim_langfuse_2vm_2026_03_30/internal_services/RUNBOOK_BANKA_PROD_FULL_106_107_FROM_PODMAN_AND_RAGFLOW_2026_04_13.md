# Banka Prod 106/107 Runtime Runbook

Date: 2026-04-16

Use this for the live Banka production path only.

Operator note:

- these commands assume you already switched to the target machine and, when
  needed, already became `root`
- the runbook intentionally does not repeat `sudo su -`

Scope:

- `10.11.115.106` comes up first as the active node
- `10.11.115.107` is added later as the passive node
- runtime stays HTTP-first
- Ragflow data is seeded only on `106`
- Podman may already be configured
- installer trees may already be extracted
- Ragflow export archive may already be staged under `/tmp`

Current images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22`
- prod encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-16-r3`

Current prod names:

- `zfgasistan-yzyonetim.ziraat.bank`
- `manavgat-yzyonetim.ziraat.bank`
- `aykal-yzyonetim.ziraat.bank`
- `mercek-yzyonetim.ziraat.bank`
- `mecra-yzyonetim.ziraat.bank`

Direct first-deploy access on `106`:

- OpenWebUI: `http://10.11.115.106:8080`
- LiteLLM: `http://10.11.115.106:4000`
- n8n: `http://10.11.115.106:5678`
- Langfuse: `http://10.11.115.106:3000`
- Ragflow: `http://10.11.115.106:8100`
- Qdrant: `http://10.11.115.106:6333`

## 1) Reuse The Current Machine State

Run on both `106` and `107`:

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

## 2) Ensure Inter-VM SSH Trust

Before preparing `107`, complete:

- `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md`

## 3) Reuse Or Extract The Installer On 106

Run on `10.11.115.106` only if `/opt/orbina/internal_services` is missing or
you want the refreshed `r22` content:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22 \
  /output
```

## 4) Apply The Prod Encrypted Config On 106

Run on `10.11.115.106`:

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-16-r3
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-16-r3 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Verify the rendered active inputs:

```bash
grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|OPENWEBUI_PUBLIC_HOST|LITELLM_PUBLIC_HOST|LANGFUSE_PUBLIC_HOST|RAGFLOW_PUBLIC_HOST|OPENWEBUI_NGINX_CONFIG_PATH)=' \
  /opt/orbina/incoming/ha.vm1.env || true
```

Expected:

- `PRIMARY_HOST=10.11.115.106`
- `PEER_HOST=10.11.115.107`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- new `*-yzyonetim.ziraat.bank` hostnames

## 5) Reuse Or Stage The Ragflow Export On 106

If `/opt/orbina/incoming/ragflow_volumes_export/volume-names.txt` already
exists on `106`, keep using it and skip this step.

If you already have a Ragflow export archive under `/tmp` on `106`, unpack it
there directly:

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

Do not stage the Ragflow export on `107`.

## 6) Install And Bootstrap 106 As Active

Run on `10.11.115.106`:

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role active \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm1-active.sh
```

The refreshed `r22` bundle already includes:

- the Redis/Langfuse bootstrap fix
- the fixed LiteLLM `custom_auth.py` for UI/admin login
- the current HTTP-first nginx generation path

## 7) Prepare 107 With The Same Installer And Config

Run on `10.11.115.107`:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-16-r22 \
  /output

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-16-r3
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-16-r3 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Verify the rendered passive inputs:

```bash
grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|OPENWEBUI_PUBLIC_HOST|LITELLM_PUBLIC_HOST|LANGFUSE_PUBLIC_HOST|RAGFLOW_PUBLIC_HOST|OPENWEBUI_NGINX_CONFIG_PATH)=' \
  /opt/orbina/incoming/ha.vm2.env || true
```

Expected:

- `PRIMARY_HOST=10.11.115.106`
- `PEER_HOST=10.11.115.106`
- `PASSIVE_SSH_HOST=10.11.115.106`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`

## 8) Install And Bootstrap 107 As Passive

Run on `10.11.115.107`:

```bash
cd /opt/orbina/internal_services

ops/install/katilim/install-node.sh \
  --role passive \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

ops/install/katilim/bootstrap-vm2-passive.sh
```

## 9) Enable Sync On 106 And Validate

Enable sync on `106`:

```bash
cd /opt/orbina/internal_services
ops/install/katilim/enable-vm1-passive-sync.sh
```

Validate on `106`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl status internal-services-ha-sync-light.timer --no-pager || true
systemctl status internal-services-ha-sync-heavy.timer --no-pager || true
curl -fsS http://127.0.0.1:18081/ready
curl -I http://127.0.0.1:8080/ || true
curl -I http://127.0.0.1:4000/ || true
curl -I http://127.0.0.1:3000/ || true
curl -I http://127.0.0.1:5678/ || true
curl -I http://127.0.0.1:8100/ || true
podman logs --tail=120 litellm || true
```

Validate on `107`:

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -i http://127.0.0.1:18081/ready || true
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();" || true
```

Remote checks from another machine:

```bash
curl -I http://10.11.115.106:8080/
curl -I http://10.11.115.106:4000/
curl -I http://10.11.115.106:3000/
curl -I http://10.11.115.106:5678/
curl -I http://10.11.115.106:8100/
```

## 10) Notes

- Production runtime stays HTTP-first.
- Future LB traffic should be:
  - `HTTPS client -> LB -> HTTP :80 on 106/107`
- Do not place the prod certificate and private key on `106` or `107` for the
  canonical runtime path.
- DNS, LB, and optional dev cert placement live only in:
  - `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`
