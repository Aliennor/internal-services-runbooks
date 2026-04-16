# Banka Langfuse Runbook: Dev VM On 10.11.115.108

Date: 2026-04-08

Scope:
- single-node dev path only
- `VM1=10.11.115.108`
- no passive bootstrap
- no LB
- HTTP first

Public dev names:
- `zfgasistan.yzyonetim-dev.ziraat.bank`
- `manavgat.yzyonetim-dev.ziraat.bank`
- `aykal.yzyonetim-dev.ziraat.bank`
- `mercek.yzyonetim-dev.ziraat.bank`
- `mecra.yzyonetim-dev.ziraat.bank`

Direct first-deploy IP:port access on `10.11.115.108`:
- OpenWebUI: `http://10.11.115.108:8080`
- LiteLLM: `http://10.11.115.108:4000`
- n8n: `http://10.11.115.108:5678`
- Langfuse: `http://10.11.115.108:3000`
- Ragflow: `http://10.11.115.108:8100`
- Qdrant: `http://10.11.115.108:6333`

## 0) Prerequisite

Prepare Podman first:
- `docs/banka-podman-dockerhub-registry-and-storage-runbook-2026-03-16.md`

On `10.11.115.108` verify:

```bash
podman info --format 'graphroot={{.Store.GraphRoot}} driver={{.Store.GraphDriverName}}'
docker version
docker compose version
```

## 1) Prepare The Dev Inventory

On `108` after the installer bundle has been extracted:

```bash
cd /opt/orbina/internal_services
cp ops/install/katilim/inventory.banka-dev-108.env.example ops/install/katilim/inventory.banka-dev-108.env
vim ops/install/katilim/inventory.banka-dev-108.env
```

Keep:
- `VM1_HOST=10.11.115.108`
- `VM2_HOST=127.0.0.1`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- `DIRECT_BIND_ADDRESS=0.0.0.0`

## 2) Render HA Inputs And Build The Secure Bundle

```bash
bash ops/install/katilim/render-ha-env.sh ops/install/katilim/inventory.banka-dev-108.env
sed -n '1,160p' ops/install/katilim/rendered/ha.vm1.env

bash ops/install/katilim/prepare-secure-config-bundle.sh \
  ops/install/katilim/inventory.banka-dev-108.env \
  "$PWD/banka_dev_108_secure_config_$(date +%Y%m%d_%H%M%S).tar.gz"
```

## 3) Extract The Installer Bundle On 108

On `10.11.115.108`:

```bash
ssh root@10.11.115.108
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 /output
```

## 4) Copy And Apply The Secure Bundle

From `108`:

```bash
scp ./banka_dev_108_secure_config_*.tar.gz root@10.11.115.108:/opt/orbina/incoming/
```

On `108`:

```bash
cd /opt/orbina/internal_services
LATEST_BUNDLE=$(ls -1t /opt/orbina/incoming/banka_dev_108_secure_config_*.tar.gz | head -n 1)
sudo ops/install/katilim/apply-secure-config-bundle.sh "$LATEST_BUNDLE" /opt/orbina
```

If importing Ragflow data from ZT ARF dev, complete this first:
- `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`

Upload target:
- `/opt/orbina/incoming/ragflow_volumes_export`

## 5) Install And Bootstrap

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh \
  --role active \
  --ha-env-source /opt/orbina/incoming/ha.vm1.env \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt

sudo ops/install/katilim/bootstrap-vm1-active.sh
```

Do not run:

```bash
sudo ops/install/katilim/bootstrap-vm2-passive.sh
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

## 6) Validate 108

```bash
curl -i http://127.0.0.1:18081/ready
curl -I --resolve zfgasistan.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://zfgasistan.yzyonetim-dev.ziraat.bank/
curl -fsS --resolve manavgat.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://manavgat.yzyonetim-dev.ziraat.bank/health
curl -I --resolve aykal.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://aykal.yzyonetim-dev.ziraat.bank/
curl -I --resolve mercek.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://mercek.yzyonetim-dev.ziraat.bank/
curl -I --resolve mecra.yzyonetim-dev.ziraat.bank:80:127.0.0.1 http://mecra.yzyonetim-dev.ziraat.bank/
```

Direct dev IP ports:

```bash
curl -I http://10.11.115.108:8080/
curl -fsS http://10.11.115.108:4000/health
curl -I http://10.11.115.108:5678/
curl -I http://10.11.115.108:3000/
curl -I http://10.11.115.108:8100/
curl -fsS http://10.11.115.108:6333/health
```

## 7) Optional Temporary `/etc/hosts`

```text
10.11.115.108 zfgasistan.yzyonetim-dev.ziraat.bank
10.11.115.108 manavgat.yzyonetim-dev.ziraat.bank
10.11.115.108 aykal.yzyonetim-dev.ziraat.bank
10.11.115.108 mercek.yzyonetim-dev.ziraat.bank
10.11.115.108 mecra.yzyonetim-dev.ziraat.bank
```
