# Katilim Prod Full Install And HA Runbook

Use this as the single operator runbook for the Katilim prod 2-VM installation.

For LB key and CSR generation, use:

- `RUNBOOK_KATILIM_LB_CERTIFICATES_AND_CSRS_2026_03_12.md`

For inter-VM SSH trust between the prod VM pair, use:

- `RUNBOOK_KATILIM_PROD_INTERVM_SSH_TRUST_2026_03_13.md`

For Windows-side prod LiteLLM reachability and API tests, use:

- `RUNBOOK_KATILIM_PROD_WINDOWS_LITELLM_TESTS_2026_03_13.md`

For VM-side prod LiteLLM validation on the installed servers, use:

- `RUNBOOK_KATILIM_PROD_VM_LITELLM_TESTS_2026_03_13.md`

For the HA sync staging retention fix on already-installed Katilim nodes, use:

- `RUNBOOK_KATILIM_HA_SYNC_STAGING_RETENTION_FIX_2026_03_16.md`

It uses the same installer and bundle flow as dev, but with the prod pair:

- `VM1=10.210.28.26`
- `VM2=10.210.28.27`
- `PROD_LB_IP=10.210.18.101`
- `POSTGRES_REPLICATION_NETWORK=10.210.28.0/24`

Prod public hostnames:

- `zfgasistan.yzyonetim.ziraatkatilim.local`
- `manavgat.yzyonetim.ziraatkatilim.local`
- `aykal.yzyonetim.ziraatkatilim.local`
- `mercek.yzyonetim.ziraatkatilim.local`

Use the shared `r21` install bundle in this runbook.

Published prod pull artifacts:

- `aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21`
- `aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1`
  - digest: `sha256:7948315dd55b50a5a7e48b48b3711d12ee58bbd0b162f291e9247f9dec32be63`

`r21` is the current shared install bundle. It carries the earlier Ragflow
MinIO amd64 and host-port fixes, the passive-sync export helper change away
from runtime `apk` installs, the Linux `shasum`/`sha256sum` fallback, and the
ClickHouse-aware passive sync behavior that briefly quiesces Langfuse
ClickHouse for a consistent export. It also moves sync staging to the
root-backed `/opt/orbina/ha-staging` default for new rendered HA env files and
adds retained-history cleanup for successful sync runs.

If Ragflow MinIO still arrives as `arm64` on a VM, the most likely cause is a
stale Nexus cache serving the old tag manifest. Force the corrected amd64
image by digest before bootstrap:

```bash
docker image rm -f aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z 2>/dev/null || true
docker pull --platform linux/amd64 aliennor/ragflow-minio@sha256:acf456514a4a67dc3b4bc1e0dd522d52b7b7afcc3614dba12b324c17759c38db
docker tag aliennor/ragflow-minio@sha256:acf456514a4a67dc3b4bc1e0dd522d52b7b7afcc3614dba12b324c17759c38db aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z
docker image inspect aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z --format '{{.Architecture}} {{.Os}}'
```

Expected result:

- `amd64 linux`

Do not reuse the dev encrypted config image tag for prod, because the prod HA
inputs and public hostnames are different.

## Quick Path

Before step `1`, set the config bundle passphrase once on each VM shell:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

If the VM layout has a small `/var` filesystem and Docker pulls fail with
`no space left on device`, move Docker storage to the root filesystem first.
Use this once per VM before Docker pulls or bootstrap:

```bash
sudo systemctl stop docker
```

```bash
sudo mkdir -p /docker-data
```

```bash
sudo rsync -aHAXx /var/lib/docker/ /docker-data/
```

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S)
```

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "data-root": "/docker-data",
  "insecure-registries": ["zknexus.ziraatkatilim.local:8181"],
  "registry-mirrors": ["http://zknexus.ziraatkatilim.local:8181"]
}
EOF
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl start docker
```

```bash
sudo systemctl status docker --no-pager -l
```

```bash
docker info | grep 'Docker Root Dir'
```

```bash
docker ps -a
```

```bash
docker volume ls
```

Do not delete `/var/lib/docker` until the VM is fully validated on the new
Docker root.

### 1. Optional: Rebuild The Prod Config Image

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
cp ops/install/katilim/inventory.prod.env.example ops/install/katilim/inventory.env
```

Edit only the real secrets and any optional paths in `ops/install/katilim/inventory.env`
if you need to regenerate the prod config image. For the normal install path,
you can skip this whole step and use the already-published prod config image.

Ragflow and LiteLLM optional assets are already supported in this kit:

- set `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` if you have the packaged Ragflow export folder
- set `LOCAL_LITELLM_IMAGE_TAR` if you want to ship a saved LiteLLM image tar instead of pulling through Nexus

Ragflow is enabled by default in the prod inventory example.

Set the passphrase in the shell you will use for the build:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

Build and push the prod-specific encrypted config image:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" bash katilim_encrypted_config_bundle_2026_03_10/build-encrypted-config-image.sh internal_services/ops/install/katilim/inventory.env aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 push
```

### 2. On `VM1`

```bash
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo sh -c 'printf "%s\n" "{\"insecure-registries\":[\"zknexus.ziraatkatilim.local:8181\"],\"registry-mirrors\":[\"http://zknexus.ziraatkatilim.local:8181\"]}" > /etc/docker/daemon.json'
sudo systemctl restart docker
curl -vk http://zknexus.ziraatkatilim.local:8181/v2/
docker login zknexus.ziraatkatilim.local:8181
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 /output
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh
curl -fsS http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
sudo ops/install/katilim/smoke-test-active.sh
docker ps
unset CONFIG_BUNDLE_PASSPHRASE
```

### 3. Test Through Prod Hostnames

Map these hosts temporarily to `10.210.18.101`:

- `zfgasistan.yzyonetim.ziraatkatilim.local`
- `manavgat.yzyonetim.ziraatkatilim.local`
- `aykal.yzyonetim.ziraatkatilim.local`
- `mercek.yzyonetim.ziraatkatilim.local`

If the prod LB is not routing yet, map them temporarily to `10.210.28.26`.

Then test:

- `http://zfgasistan.yzyonetim.ziraatkatilim.local`
- `http://manavgat.yzyonetim.ziraatkatilim.local`
- `http://aykal.yzyonetim.ziraatkatilim.local`
- `http://mercek.yzyonetim.ziraatkatilim.local`

### 4. On `VM2`

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo sh -c 'printf "%s\n" "{\"insecure-registries\":[\"zknexus.ziraatkatilim.local:8181\"],\"registry-mirrors\":[\"http://zknexus.ziraatkatilim.local:8181\"]}" > /etc/docker/daemon.json'
sudo systemctl restart docker
curl -vk http://zknexus.ziraatkatilim.local:8181/v2/
docker login zknexus.ziraatkatilim.local:8181
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 /output
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
docker ps
unset CONFIG_BUNDLE_PASSPHRASE
```

### 5. Enable Sync On `VM1`

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

### 6. Ragflow And LiteLLM Optional Inputs

If `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` was set in the inventory before the config image was built:

- the packaged Ragflow export is already carried into `/opt/orbina/incoming/ragflow_volumes_export`
- `bootstrap-vm1-active.sh` restores it automatically on `VM1`

If you are not copying the export folder, leave this in the inventory instead:

- `RAGFLOW_EXPORT_IMAGE=aliennor/redis-11.03-ragflow-volumes:latest`
- `RAGFLOW_EXPORT_IMAGE_PATH=/etc/redis/ragflow_volumes_export`

Then `bootstrap-vm1-active.sh` pulls the export image and restores it automatically.

### 6A. Apply Ragflow To An Already-Installed Core-Only Prod Server

If a prod server was installed earlier with `ENABLE_RAGFLOW_STACK=false`, bring it forward like this on `VM1`:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 /output
unset CONFIG_BUNDLE_PASSPHRASE
sudo sed -i.bak 's/^ENABLE_RAGFLOW_STACK=.*/ENABLE_RAGFLOW_STACK=true/' /etc/internal-services/ha.env
cd /opt/orbina/internal_services
sudo ops/install/katilim/pull-ragflow-volume-export-image.sh /opt/orbina/incoming/ragflow_volumes_export aliennor/redis-11.03-ragflow-volumes:latest /etc/redis/ragflow_volumes_export
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
sudo ops/ha/stop-active.sh || true
sudo ops/ha/start-single-node-fallback.sh
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'ragflow|mcp|qdrant'
```

If `LOCAL_LITELLM_IMAGE_TAR` was set in the inventory before the config image was built:

- the tar is already carried into `/opt/orbina/incoming/litellm-image.tar`
- `install-node.sh` loads it automatically before image pulls

Otherwise LiteLLM is pulled through Nexus from:

- `zknexus.ziraatkatilim.local:8181/berriai/litellm:main-latest`

and tagged to the compose-expected name automatically.

## Reference

For the broader Katilim install and HA behavior, use:

- `RUNBOOK_KATILIM_FULL_INSTALL_AND_HA_2026_03_10.md`

This prod runbook exists only to pin the prod IPs and prod hostname set.
