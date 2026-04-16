# Katilim Pull-Bundle And Install Runbook

Preferred operator entrypoint:

- use `internal_services/RUNBOOK_KATILIM_FULL_INSTALL_AND_HA_2026_03_10.md` for the full end-to-end process
- keep this file as the delivery-method-specific variant

Use this flow when you want the servers to receive one prepared install image
first, then apply the secure config bundle and continue installation.

Important Katilim Nexus behavior confirmed on March 10, 2026:

- `http://zknexus.ziraatkatilim.local:8181/v2/` is a valid Docker registry endpoint
- the same host:port does not speak HTTPS
- Docker therefore needs `insecure-registries` for that host:port before direct pulls work

## Quick Path

Workstation:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
cp ops/install/katilim/inventory.env.example ops/install/katilim/inventory.env
# edit ops/install/katilim/inventory.env
bash ops/install/katilim/prepare-secure-config-bundle.sh \
  ops/install/katilim/inventory.env \
  /tmp/katilim-secure-config.tar.gz
scp /tmp/katilim-secure-config.tar.gz root@VM1:/opt/orbina/incoming/
scp /tmp/katilim-secure-config.tar.gz root@VM2:/opt/orbina/incoming/
```

On `VM1`:

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "insecure-registries": ["zknexus.ziraatkatilim.local:8181"],
  "registry-mirrors": ["http://zknexus.ziraatkatilim.local:8181"]
}
EOF
sudo systemctl restart docker
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r19
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r19 /output
cd /opt/orbina/internal_services
sudo ops/install/katilim/apply-secure-config-bundle.sh /opt/orbina/incoming/katilim-secure-config.tar.gz /opt/orbina
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

On `VM2`:

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "insecure-registries": ["zknexus.ziraatkatilim.local:8181"],
  "registry-mirrors": ["http://zknexus.ziraatkatilim.local:8181"]
}
EOF
sudo systemctl restart docker
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
cd /opt/orbina/internal_services
sudo ops/install/katilim/apply-secure-config-bundle.sh /opt/orbina/incoming/katilim-secure-config.tar.gz /opt/orbina
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

Back on `VM1` after `VM2` is ready:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

## Artifacts

Pullable install image:

- build context:
  - `internal_services_image_2026_03_09/katilim_install_bundle_2026_03_10`
- default image name:
  - `aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17`

Separate secure artifacts:

- secure config bundle from:
  - `internal_services/ops/install/katilim/prepare-secure-config-bundle.sh`
- optional local litellm image tar
- optional ragflow volume export directory

## 1. On The Workstation: Build The Install Image

Local build only:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/build-bundle-image.sh aliennor katilim-2vm-2026-03-10-r17 load
```

Push to Docker Hub:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/build-bundle-image.sh aliennor katilim-2vm-2026-03-10-r17 push
```

## 2. On The Workstation: Build The Secure Config Bundle

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
cp ops/install/katilim/inventory.env.example ops/install/katilim/inventory.env
# edit inventory.env first
bash ops/install/katilim/prepare-secure-config-bundle.sh \
  ops/install/katilim/inventory.env \
  /tmp/katilim-secure-config.tar.gz
```

This bundle contains:

- current service `.env` files
- `incoming/ha.vm1.env`
- `incoming/ha.vm2.env`
- optional TLS files
- optional local litellm image tar if configured
- optional `incoming/ragflow_volumes_export/` if
  `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` is set

Do not push this bundle to Docker Hub.

## 3. On Each VM: Pull And Extract The Install Tree

On `VM1` and `VM2`:

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "insecure-registries": ["zknexus.ziraatkatilim.local:8181"],
  "registry-mirrors": ["http://zknexus.ziraatkatilim.local:8181"]
}
EOF
sudo systemctl restart docker
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
```

If the mirrored Docker Hub pull still does not work, use the tar fallback
instead:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/export-bundle-image.sh \
  aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 \
  /tmp/internal-services-katilim-install.tar.gz
scp /tmp/internal-services-katilim-install.tar.gz root@VM1:/opt/orbina/incoming/
scp /tmp/internal-services-katilim-install.tar.gz root@VM2:/opt/orbina/incoming/
```

Then on each VM:

```bash
docker load -i /opt/orbina/incoming/internal-services-katilim-install.tar.gz
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
```

## 4. Copy The Secure Config Bundle To Each VM

From the workstation:

```bash
scp /tmp/katilim-secure-config.tar.gz root@VM1:/opt/orbina/incoming/
scp /tmp/katilim-secure-config.tar.gz root@VM2:/opt/orbina/incoming/
```

On each VM:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/apply-secure-config-bundle.sh /opt/orbina/incoming/katilim-secure-config.tar.gz /opt/orbina
```

## 5. Start `VM1` First

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

At this point `VM1` should be the working server.

## 6. Ragflow Volume Export

If you set `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` before building the secure bundle,
the packaged export is already inside:

- `/opt/orbina/incoming/ragflow_volumes_export`

and `bootstrap-vm1-active.sh` restores it automatically before starting the
active stack.

If you want to copy it separately instead:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/push-ragflow-volume-export.sh \
  /path/to/ragflow_volumes_export \
  VM1_IP \
  /opt/orbina/incoming/ragflow_volumes_export \
  ops/install/katilim/inventory.env
```

Then on `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
```

Expected folder contents from the older scripts:

- `volume-names.txt`
- `SHA256SUMS.txt`
- `esdata01*.tar.gz`
- `minio_data*.tar.gz`
- `mysql_data*.tar.gz`
- `redis_data*.tar.gz`
- `qdrant_data*.tar.gz`

## 7. Install `VM2`

On `VM2`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

## 8. Enable Sync From `VM1`

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

## 9. Browser Validation

Temporarily map these hosts to `VM1`:

- `zfgasistan.yzyonetim-dev.zb`
- `manavgat.yzyonetim-dev.zb`
- `aykal.yzyonetim-dev.zb`
- `mercek.yzyonetim-dev.zb`

Then validate the applications.

## 10. Fallback

If HA is not ready, keep `VM1` running alone:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/start-single-node-fallback.sh
```
