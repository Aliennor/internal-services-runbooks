# Runbook: Online Install (Server Can `docker pull`)

## Goal
Install the stack on a new server using Docker registry pulls, while still transferring:
- local-only images (for example `litellm` image not available in hub)
- ragflow/qdrant data volumes

## Scripts
- `install_online_with_pull.sh`
- `export_local_images.sh`
- `export_selected_volumes.sh`
- `restore_selected_volumes.sh`

## 1) Copy toolkit to target server
Copy `offline_deploy/` folder to target server and run from there.

Prerequisites on target server:
- Docker engine + `docker compose`
- Internet egress to registries
- Registry auth if needed (`docker login`)

## 2) On source server: export local-only image(s) and ragflow volumes
Export litellm image from local Docker cache:
```bash
cd /path/to/offline_deploy
chmod +x *.sh
./export_local_images.sh /opt/orbina/local-only-images.tar
```

Export ragflow/qdrant related volumes:
```bash
./export_selected_volumes.sh /opt/orbina/ragflow_volumes_export
```

Default exported volume bases:
- `esdata01`
- `minio_data`
- `mysql_data`
- `redis_data`
- `qdrant_data`

Then transfer to target server:
- `/opt/orbina/local-only-images.tar`
- `/opt/orbina/ragflow_volumes_export/`
- `offline_deploy/`

## 3) On target server: run installer (hybrid pull + local image tar)
```bash
cd /path/to/offline_deploy
chmod +x *.sh
sudo SOURCE_IMAGE=aliennor/redis-02.03-internal:latest \
  LOCAL_IMAGES_TAR=/opt/orbina/local-only-images.tar \
  ./install_online_with_pull.sh /opt/orbina/internal_services
```

This will:
- pull source image and extract `/etc/redis/internal_services`
- load local-only images from `LOCAL_IMAGES_TAR` first (if provided)
- pull required service images (except forced local-only patterns)
- auto-generate self-signed TLS if missing
- install helper scripts under `/opt/orbina/internal_services/scripts`
- install systemd units if `systemctl` and installer file exist

## 4) On target server: restore ragflow volumes
```bash
cd /path/to/offline_deploy
sudo ./restore_selected_volumes.sh /opt/orbina/ragflow_volumes_export
```

## 5) Start stack
Core:
```bash
sudo /opt/orbina/internal_services/scripts/start_stack.sh /opt/orbina/internal_services
```

Full (with ragflow + qdrant + ragflow_mcp):
```bash
sudo /opt/orbina/internal_services/scripts/start_stack_with_ragflow.sh /opt/orbina/internal_services
```

## Common options

Skip observability:
```bash
INCLUDE_OBSERVABILITY=false ./install_online_with_pull.sh /opt/orbina/internal_services
```

Core-only (no ragflow stack):
```bash
INCLUDE_RAGFLOW_STACK=false ./install_online_with_pull.sh /opt/orbina/internal_services
```

Include optional ragflow profile images too:
```bash
INCLUDE_RAGFLOW_OPTIONAL_IMAGES=true ./install_online_with_pull.sh /opt/orbina/internal_services
```

Skip systemd unit install:
```bash
INSTALL_SYSTEMD_UNITS=false ./install_online_with_pull.sh /opt/orbina/internal_services
```

Auto-start after install:
```bash
AUTO_START=true START_WITH_RAGFLOW=true ./install_online_with_pull.sh /opt/orbina/internal_services
```

Disable self-signed generation:
```bash
GENERATE_SELF_SIGNED_TLS=false ./install_online_with_pull.sh /opt/orbina/internal_services
```

Change forced local-only image patterns:
```bash
FORCE_LOCAL_IMAGE_PATTERNS='harbor.tool.zb/devops-images/berriai/litellm-database:*,my-registry.local/private/*' \
  LOCAL_IMAGES_TAR=/opt/orbina/local-only-images.tar \
  ./install_online_with_pull.sh /opt/orbina/internal_services
```

Export specific local images explicitly:
```bash
./export_local_images.sh /opt/orbina/local-only-images.tar \
  harbor.tool.zb/devops-images/berriai/litellm-database:main-latest-10-02-2026-certs
```

## Notes
- Optional ragflow profile images (`opensearch`, `infinity`, `sandbox`, `kibana`, `oceanbase`) are excluded by default.
- HTTPS works with self-signed certs immediately; browser warns until CA-signed cert is installed.
- If systemd is available, installer will install service units by default.
- Default forced local-only pattern already includes litellm private image:
  - `harbor.tool.zb/devops-images/berriai/litellm-database:*`
