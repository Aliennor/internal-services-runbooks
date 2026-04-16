# Katilim 2-VM First Install Runbook

Preferred operator entrypoint:

- use `RUNBOOK_KATILIM_FULL_INSTALL_AND_HA_2026_03_10.md` for the full end-to-end process
- keep this file as the focused first-install variant

Scope:

- Source tree: `/opt/orbina/internal_services`
- Baseline snapshot: March 9 exported working server
- Nexus Docker connector: `http://zknexus.ziraatkatilim.local:8181`
- Verified on March 10, 2026:
  - `/v2/` returns Docker registry 401 over HTTP
  - the same port does not speak HTTPS
- Goal: get `VM1` serving first, then add `VM2` as passive standby

The installer assets are under:

- `ops/install/katilim`

## 0. Confirmed Katilim Docker Behavior

These results are already confirmed from the Katilim VM:

```bash
curl -vk http://zknexus.ziraatkatilim.local:8181/v2/
```

returned Docker registry `401 Unauthorized` with:

- `Docker-Distribution-Api-Version: registry/2.0`

and:

```bash
curl -vk https://zknexus.ziraatkatilim.local:8181/v2/
```

failed because this connector is plain HTTP, not HTTPS.

That means Docker must be configured with:

- `insecure-registries: ["zknexus.ziraatkatilim.local:8181"]`

before direct pulls from that host can work.

## 1. On The Workstation: Prepare Inventory

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
cp ops/install/katilim/inventory.env.example ops/install/katilim/inventory.env
```

Edit:

- `ops/install/katilim/inventory.env`

Minimum fields to set:

- `VM1_HOST`
- `VM2_HOST`
- `POSTGRES_REPLICATION_PASSWORD`
- `POSTGRES_REPLICATION_NETWORK`
- `NEXUS_USERNAME`
- `NEXUS_PASSWORD` if anonymous pull is not allowed

Recommended first-test values:

- `ENABLE_QDRANT=true`
- `ENABLE_RAGFLOW_STACK=true`
- `COPY_TLS=false`
- keep the Nexus defaults from the example inventory:
  - `NEXUS_DOCKER_REGISTRY=zknexus.ziraatkatilim.local:8181`
  - `NEXUS_DOCKER_SCHEME=http`
  - `NEXUS_REGISTRY_MIRROR_URL=http://zknexus.ziraatkatilim.local:8181`
  - `NEXUS_INSECURE_REGISTRY=true`
  - `AUTO_CONFIGURE_DOCKER_NEXUS=true`
- set `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR=/path/to/ragflow_volumes_export` if you
  already have the packaged export from the older offline deploy tooling

Why `ENABLE_RAGFLOW_STACK=true` now:

- Ragflow is part of the default Katilim install flow now
- `bootstrap-vm1-active.sh` can pull `aliennor/redis-11.03-ragflow-volumes:latest` and restore it automatically
- only set it to `false` deliberately if you want a temporary core-only install

## 2. Optional: Export Local litellm Image For Later

If you want to carry the exact current litellm image from the existing company server later:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/export-litellm-image.sh /tmp/litellm-image.tar
```

Then set:

- `LOCAL_LITELLM_IMAGE_TAR=/tmp/litellm-image.tar`

in:

- `ops/install/katilim/inventory.env`

If you do not provide a local tar yet, the installer will use the temporary
fallback source defined in:

- `ops/install/katilim/katilim-image-map.txt`

and tag it to the image name expected by the current compose file.

## 3. Transfer The Clean Snapshot To Both VMs

From the workstation:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/push-to-vms.sh ops/install/katilim/inventory.env
```

This does all of the following:

- renders `ha.vm1.env` and `ha.vm2.env`
- copies the clean `internal_services` tree to both VMs
- excludes runtime junk like `n8n_storage`, nginx logs, ragflow logs, and cache folders
- copies the HA env files to `/opt/orbina/incoming`
- copies TLS files and a local litellm tar too if configured
- copies the packaged ragflow volume export to `VM1` too if
  `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` is set

If you prefer transferring one tarball instead of `rsync`:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/prepare-transfer-tarball.sh ops/install/katilim/inventory.env
```

Then copy the tarball to each VM, unpack it under `/opt/orbina`, and make sure:

- `/opt/orbina/internal_services`
- `/opt/orbina/incoming`

exist before continuing.

## 4. Install And Start `VM1` First

SSH to `VM1` and run:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

What this does:

- installs `/etc/internal-services/ha.env` from `/opt/orbina/incoming/ha.vm1.env`
- installs systemd units
- copies TLS certs from `/opt/orbina/incoming` if present, otherwise generates a self-signed cert
- writes `/etc/docker/daemon.json` for the Katilim Nexus connector when enabled
- restarts Docker if the daemon config changed
- validates `http://zknexus.ziraatkatilim.local:8181/v2/`
- pulls and tags images so the current compose files stay unchanged
- restores `/opt/orbina/incoming/ragflow_volumes_export` automatically if it is present
- starts `VM1` in active single-node fallback mode
- creates the Postgres replication role and slot
- runs the active smoke test

At this point `VM1` is the working server even if `VM2` is still absent.

## 5. Validate `VM1` Locally

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/smoke-test-active.sh
curl -fsS http://127.0.0.1:18081/ready
```

## 6. Validate `VM1` From Your Browser

The current nginx config still serves these hostnames:

- `zfgasistan.yzyonetim-dev.zb`
- `manavgat.yzyonetim-dev.zb`
- `aykal.yzyonetim-dev.zb`
- `mercek.yzyonetim-dev.zb`

For a quick test from your workstation, add temporary hosts entries pointing to
`VM1`:

```text
<VM1_IP> zfgasistan.yzyonetim-dev.zb
<VM1_IP> manavgat.yzyonetim-dev.zb
<VM1_IP> aykal.yzyonetim-dev.zb
<VM1_IP> mercek.yzyonetim-dev.zb
```

Then open:

- `https://zfgasistan.yzyonetim-dev.zb`
- `https://manavgat.yzyonetim-dev.zb`
- `https://aykal.yzyonetim-dev.zb`
- `https://mercek.yzyonetim-dev.zb`

If the cert is self-signed, the browser warning is expected during first test.

## 7. Optional: Manual Ragflow Restore Override

If you skipped the automatic transfer or want to rerun the restore manually:

Copy that folder to `VM1`, for example:

- `/opt/orbina/incoming/ragflow_volumes_export`

Then restore it:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
```

If you want to turn ragflow on after the core apps are confirmed:

1. Edit:
   - `/etc/internal-services/ha.env`
2. Change:
   - `ENABLE_RAGFLOW_STACK=true`
3. Restart the active node flow:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/stop-active.sh || true
sudo ops/ha/start-single-node-fallback.sh
```

## 8. Install And Start `VM2`

SSH to `VM2` and run:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

This installs the passive HA env, prepares images, seeds PostgreSQL from
`VM1`, and starts the standby node.

## 9. Enable Volume Sync From `VM1` To `VM2`

Back on `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

This performs the initial full sync and then enables the periodic sync timers.

## 10. Manual Promotion Later

If `VM1` fails later and `VM2` must be promoted:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/promote-passive.sh
```

## 11. Safe Fallback If HA Is Not Ready

If anything in the 2-VM flow is not ready, `VM1` can keep serving by itself:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/start-single-node-fallback.sh
curl -fsS http://127.0.0.1:18081/ready
```

That is the safe fallback mode for first installation testing.

## 12. Important Notes

- The Katilim image map assumes the Katilim Nexus Docker connector can serve
  the host and namespace layout used in:
  - `ops/install/katilim/katilim-image-map.txt`
- The source side of that file now uses `__NEXUS_DOCKER_REGISTRY__` and is
  resolved automatically from the rendered HA env.
- If direct pulls from the connector still return `unauthorized`, add
  `NEXUS_USERNAME` and `NEXUS_PASSWORD` to the inventory and rerun the install
  step so Docker logs into Nexus first.
- The current compose files are intentionally kept unchanged. The installer
  pulls and tags images so the running stack still uses the exact image names
  already referenced in the snapshot.
