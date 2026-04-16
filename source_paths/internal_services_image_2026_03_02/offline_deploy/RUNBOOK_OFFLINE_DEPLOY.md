# Runbook: Offline Deployment Bundle for `redis-02.03-internal`

## Scope
This runbook creates a transferable ZIP on an internet-connected machine, then installs and starts the same stack on an air-gapped company server.

Stack included:
- `shared-postgres`
- `langfuse`
- `litellm`
- `n8n`
- `openweb-ui`
- `observability`
- logrotate helper image `aliennor/internal-services-logrotate:0.1.0`

Source image for filesystem extraction:
- `aliennor/redis-02.03-internal:latest`

## A) Internet-connected machine (prepare transfer ZIP)

1. Go to toolkit directory.
```bash
cd /path/to/offline_deploy
```

2. Build the offline bundle.
```bash
chmod +x prepare_offline_bundle.sh
./prepare_offline_bundle.sh
```

Optional (smaller file, slower):
```bash
COMPRESS_IMAGES_TAR=true ./prepare_offline_bundle.sh
```

3. Output files will be created in current directory:
- `internal_services_offline_bundle_<timestamp>/`
- `internal_services_offline_bundle_<timestamp>.zip`

4. Copy the ZIP to company server (USB/SCP over approved path).

## B) Air-gapped company server (install)

1. Extract ZIP.
```bash
unzip internal_services_offline_bundle_<timestamp>.zip
cd internal_services_offline_bundle_<timestamp>
```

2. Install files + load images.
```bash
chmod +x scripts/install_on_airgapped_server.sh scripts/start_stack.sh scripts/stop_stack.sh
sudo ./scripts/install_on_airgapped_server.sh "$(pwd)" /opt/orbina/internal_services
```

3. Start stack.
```bash
sudo /opt/orbina/internal_services/scripts/start_stack.sh /opt/orbina/internal_services
```

4. Verify containers.
```bash
docker ps
```

## C) Optional systemd enable/start

Enable units:
```bash
sudo systemctl enable \
  internal-services-shared-postgres.service \
  internal-services-langfuse.service \
  internal-services-litellm.service \
  internal-services-n8n.service \
  internal-services-openweb-ui.service \
  internal-services-observability.service \
  internal-services.target
```

Start entire stack via target:
```bash
sudo systemctl start internal-services.target
```

Enable nginx logrotate timer (optional):
```bash
sudo systemctl enable --now internal-services-nginx-logrotate-container.timer
```

## D) Useful operations on company server

Stop stack:
```bash
sudo /opt/orbina/internal_services/scripts/stop_stack.sh /opt/orbina/internal_services
```

Start stack:
```bash
sudo /opt/orbina/internal_services/scripts/start_stack.sh /opt/orbina/internal_services
```

Show loaded image inventory:
```bash
docker image ls
```

Backup loaded images to tar (on company server):
```bash
mkdir -p /opt/orbina/backups
# shellcheck disable=SC2046
docker save -o /opt/orbina/backups/internal-services-images-backup.tar $(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep -E '^(postgres|nginx|unrool/ziraat-openwebui|aliennor/|docker.io/langfuse|docker.io/minio|docker.io/redis|docker.io/clickhouse|harbor\.tool\.zb/devops-images/berriai/litellm-database)')
```

## E) Notes
- The bundle removes `openweb-ui/nginx-logs` to avoid shipping old runtime logs.
- If your target host uses a different root than `/opt/orbina/internal_services`, pass it as second arg to `install_on_airgapped_server.sh`.
- If private image access is restricted on source machine (e.g., Harbor), authenticate first (`docker login ...`) before running bundle creation.
