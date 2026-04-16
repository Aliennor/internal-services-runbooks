# Banka Langfuse Runbook: VM1 Active First

Date: 2026-04-06

Scope:
- banka production path only
- `VM1=10.11.115.106`
- `VM2=10.11.115.107` reserved for passive later
- no LB yet
- HTTP first
- Podman runtime with `docker` and `docker compose` compatibility

Published installer bundle image:
- `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21`

Public prod names:
- `zfgasistan.yzyonetim.ziraat.bank` -> OpenWebUI
- `manavgat.yzyonetim.ziraat.bank` -> LiteLLM
- `aykal.yzyonetim.ziraat.bank` -> n8n
- `mercek.yzyonetim.ziraat.bank` -> Langfuse
- `mecra.yzyonetim.ziraat.bank` -> Ragflow

Direct first-deploy IP:port access on `10.11.115.106`:
- OpenWebUI: `http://10.11.115.106:8080`
- LiteLLM: `http://10.11.115.106:4000`
- n8n: `http://10.11.115.106:5678`
- Langfuse: `http://10.11.115.106:3000`
- Ragflow: `http://10.11.115.106:8100`
- Qdrant: `http://10.11.115.106:6333`

## 0) Prerequisite

Prepare Podman first:
- `docs/banka-podman-dockerhub-registry-and-storage-runbook-2026-03-16.md`

On `10.11.115.106` verify:

```bash
podman info --format 'graphroot={{.Store.GraphRoot}} driver={{.Store.GraphDriverName}}'
docker version
docker compose version
```

Expected:
- `graphroot=/root/docker-data/containers/storage`
- `docker` works
- `docker compose` works

Optional bundle extraction path on `VM1`:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 /output
```

## 1) Prepare The Inventory

On VM1 after the installer bundle has been extracted:

```bash
cd /opt/orbina/internal_services
vim ops/install/katilim/inventory.banka-ha-ready.env
```

Before first rollout, keep these defaults:
- `LOAD_BALANCER_IP=10.11.115.106`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- `DIRECT_BIND_ADDRESS=0.0.0.0`
- `ENABLE_RAGFLOW_STACK=true`

Change the secrets:
- `POSTGRES_REPLICATION_PASSWORD`
- `shared-postgres/.env`
- `langfuse/.env`
- `litellm/.env`
- `n8n/.env`
- `openweb-ui/.env`
- `observability/.env`
- `qdrant/.env`
- `ragflow/docker/.env`

## 2) Render HA Inputs

```bash
bash ops/install/katilim/render-ha-env.sh ops/install/katilim/inventory.banka-ha-ready.env
sed -n '1,160p' ops/install/katilim/rendered/ha.vm1.env
```

Confirm:
- `PRIMARY_HOST=10.11.115.106`
- `PEER_HOST=10.11.115.107`
- `OPENWEBUI_PUBLIC_HOST=zfgasistan.yzyonetim.ziraat.bank`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- direct port variables are present

## 3) Build The Secure Config Bundle

```bash
bash ops/install/katilim/prepare-secure-config-bundle.sh \
  ops/install/katilim/inventory.banka-ha-ready.env \
  "$PWD/banka_langfuse_secure_config_$(date +%Y%m%d_%H%M%S).tar.gz"
```

This bundle carries:
- live service `.env` files
- `ragflow/docker/.env`
- `incoming/ha.vm1.env`
- `incoming/ha.vm2.env`
- optional TLS files
- optional Ragflow volume export

## 4) Transfer The Tree To VM1 Only

```bash
bash ops/install/katilim/push-to-vms.sh --vm1-only ops/install/katilim/inventory.banka-ha-ready.env
scp ./banka_langfuse_secure_config_*.tar.gz root@10.11.115.106:/opt/orbina/incoming/
```

If importing Ragflow data from the ZT ARF dev server, complete this first:
- `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`

Required target path on `VM1`:
- `/opt/orbina/incoming/ragflow_volumes_export`

## 5) Apply The Secure Bundle On VM1

```bash
ssh root@10.11.115.106
cd /opt/orbina/internal_services
LATEST_BUNDLE=$(ls -1t /opt/orbina/incoming/banka_langfuse_secure_config_*.tar.gz | head -n 1)
sudo ops/install/katilim/apply-secure-config-bundle.sh "$LATEST_BUNDLE" /opt/orbina
```

## 6) Install The Active Node

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh \
  --role active \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt
```

This step now also:
- rewrites service `.env` files from `/etc/internal-services/ha.env`
- renders `openweb-ui/nginx.http-only.generated.conf`
- keeps direct IP ports enabled

## 7) Bootstrap VM1

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

This auto-restores Ragflow export data if:
- `/opt/orbina/incoming/ragflow_volumes_export/volume-names.txt` exists

## 8) Validate VM1

Readiness:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Named HTTP routes from `VM1`:

```bash
curl -I --resolve zfgasistan.yzyonetim.ziraat.bank:80:127.0.0.1 http://zfgasistan.yzyonetim.ziraat.bank/
curl -fsS --resolve manavgat.yzyonetim.ziraat.bank:80:127.0.0.1 http://manavgat.yzyonetim.ziraat.bank/health
curl -I --resolve aykal.yzyonetim.ziraat.bank:80:127.0.0.1 http://aykal.yzyonetim.ziraat.bank/
curl -I --resolve mercek.yzyonetim.ziraat.bank:80:127.0.0.1 http://mercek.yzyonetim.ziraat.bank/
curl -I --resolve mecra.yzyonetim.ziraat.bank:80:127.0.0.1 http://mecra.yzyonetim.ziraat.bank/
```

Direct first-deploy IP ports:

```bash
curl -I http://10.11.115.106:8080/
curl -fsS http://10.11.115.106:4000/health
curl -I http://10.11.115.106:5678/
curl -I http://10.11.115.106:3000/
curl -I http://10.11.115.106:8100/
curl -fsS http://10.11.115.106:6333/health
```

## 9) Optional Temporary `/etc/hosts`

If you want to test the final names before real DNS:

```text
10.11.115.106 zfgasistan.yzyonetim.ziraat.bank
10.11.115.106 manavgat.yzyonetim.ziraat.bank
10.11.115.106 aykal.yzyonetim.ziraat.bank
10.11.115.106 mercek.yzyonetim.ziraat.bank
10.11.115.106 mecra.yzyonetim.ziraat.bank
```

## 10) Next Step Later

When `10.11.115.107` is ready:
- `RUNBOOK_BANKA_LANGFUSE_ACTIVE_PASSIVE_LB_CUTOVER_2026_04_06.md`

When DNS/LB/TLS is ready:
- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`
