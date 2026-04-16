# Runbook: Source Company Server -> Empty Company Server (Unique Data Target)

## Goal
Transfer the same stack setup to a new server **without cloning source data**.

What gets transferred:
- `internal_services` folder (configs/scripts)
- Docker images required by the stack

Default behavior is selective:
- Transfers specific ragflow/qdrant volumes by default: `esdata01`, `minio_data`, `mysql_data`, `redis_data`, `qdrant_data`
- Does not transfer unrelated full-stack volumes unless explicitly enabled

## Files (this toolkit)
- `export_from_running_server.sh` (run on source server)
- `import_to_new_server.sh` (run on target server)
- `generate_tls_csr.sh` (run on target server when requesting CA-signed cert)
- `start_stack.sh` / `stop_stack.sh` (core stack)
- `start_stack_with_ragflow.sh` / `stop_stack_with_ragflow.sh` (core + ragflow + qdrant + ragflow_mcp)

## A) On source (currently running) company server

1. Copy `offline_deploy/` directory to source server.

2. Run export (default skips data volumes):
```bash
cd /path/to/offline_deploy
chmod +x *.sh
./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```

Default export prunes heavy optional artifacts from the bundle only (source files are untouched):
- removes `openweb-ui/nginx-logs` from bundle
- keeps `ragflow*` and `qdrant` by default (includes their images)
- skips `openwebui-test`
- skips `n8n` archive parts (`n8n-part.*`, `n8n-node.tar.gz` copies)
- removes `*.bak_*` files in bundle copy

If you need a core-only bundle (exclude ragflow/qdrant/mcp):
```bash
INCLUDE_RAGFLOW_STACK=false ./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```

By default, optional ragflow profile images are excluded
(`opensearch`, `infinity`, `sandbox`, `kibana`, `oceanbase`).
To include them too:
```bash
INCLUDE_RAGFLOW_OPTIONAL_IMAGES=true ./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```

If you also want to skip observability images/config in the bundle:
```bash
INCLUDE_OBSERVABILITY=false ./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```

If you need transfer-friendly smaller files (e.g., WinSCP limits), create split parts:
```bash
SPLIT_ARCHIVE=true SPLIT_SIZE_MB=1900 KEEP_FULL_ARCHIVE=false \
  ./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```
This produces:
- `...zip.part-000`, `...zip.part-001`, ...
- `...zip.parts.sha256`

Output:
- `/opt/orbina/internal_services_server_migration_<timestamp>/`
- `/opt/orbina/internal_services_server_migration_<timestamp>.zip`

3. Transfer ZIP to target server (USB/SCP over approved path).

## B) On target (empty) company server

1. Extract ZIP:
```bash
cd /opt/orbina
unzip internal_services_server_migration_<timestamp>.zip
cd internal_services_server_migration_<timestamp>
```

If split parts were transferred, rebuild ZIP first:
```bash
cd /opt/orbina
cat internal_services_server_migration_<timestamp>.zip.part-* > internal_services_server_migration_<timestamp>.zip
sha256sum -c internal_services_server_migration_<timestamp>.zip.parts.sha256
unzip internal_services_server_migration_<timestamp>.zip
cd internal_services_server_migration_<timestamp>
```

2. Import (fresh unique data mode):
```bash
chmod +x scripts/*.sh
sudo GENERATE_SELF_SIGNED_TLS=true TLS_SUBJECT="/CN=$(hostname -f)" ./scripts/import_to_new_server.sh "$(pwd)" /opt/orbina/internal_services
```

3. Start stack:
```bash
sudo /opt/orbina/internal_services/scripts/start_stack.sh /opt/orbina/internal_services
```

Or start full stack with ragflow/qdrant:
```bash
sudo /opt/orbina/internal_services/scripts/start_stack_with_ragflow.sh /opt/orbina/internal_services
```

4. Verify:
```bash
docker ps
```

## C) Generate key + CSR for company CA (after target import)

On target server:
```bash
cd /opt/orbina/internal_services_server_migration_<timestamp>
chmod +x scripts/generate_tls_csr.sh
SAN_DNS="zfgasistan.your-domain.local,manavgat.your-domain.local,aykal.your-domain.local,mercek.your-domain.local" \
  sudo ./scripts/generate_tls_csr.sh zfgasistan.your-domain.local /opt/orbina/tls
```

Send the generated `.csr` file in `/opt/orbina/tls/` to your company PKI/CA team.

When signed certificate is returned:
```bash
sudo install -d -m 0755 /etc/pki/tls/certs /etc/pki/tls/private
sudo cp /path/from-ca/signed-cert.pem /etc/pki/tls/certs/cert.pem
sudo cp /opt/orbina/tls/zfgasistan.your-domain.local.key /etc/pki/tls/private/private.key
sudo chmod 600 /etc/pki/tls/private/private.key
sudo chmod 644 /etc/pki/tls/certs/cert.pem
sudo /opt/orbina/internal_services/scripts/start_stack.sh /opt/orbina/internal_services
```

## D) Optional: enable systemd units
```bash
sudo systemctl enable \
  internal-services-shared-postgres.service \
  internal-services-langfuse.service \
  internal-services-litellm.service \
  internal-services-n8n.service \
  internal-services-openweb-ui.service \
  internal-services-observability.service \
  internal-services.target

sudo systemctl start internal-services.target
```

Optional logrotate timer:
```bash
sudo systemctl enable --now internal-services-nginx-logrotate-container.timer
```

## E) If you ever want full data clone later
On source export:
```bash
INCLUDE_DATA_VOLUMES=true FREEZE_STACK=true ./export_from_running_server.sh /opt/orbina/internal_services /opt/orbina
```
On target import:
```bash
RESTORE_DATA_VOLUMES=true ./scripts/import_to_new_server.sh "$(pwd)" /opt/orbina/internal_services
```

## Notes
- Import script can auto-generate self-signed cert/key at `/etc/pki/tls/certs/cert.pem` and `/etc/pki/tls/private/private.key`.
- With self-signed certs, HTTPS works immediately on target ports, but browsers will show a certificate warning until you install a trusted cert.
- Ragflow/qdrant files under `internal_services` are transferred by default.
- Ragflow/qdrant named Docker volumes are transferred only when:
  - default selective mode (already on): `INCLUDE_DEFAULT_SELECTED_VOLUMES=true` (default)
  - or full mode: source export `INCLUDE_DATA_VOLUMES=true`
  - target import restore is on by default (`RESTORE_DATA_VOLUMES=true`)
- To skip volume restore on target explicitly:
  - `RESTORE_DATA_VOLUMES=false ./scripts/import_to_new_server.sh ...`
- Core stop/start scripts:
  - `/opt/orbina/internal_services/scripts/start_stack.sh`
  - `/opt/orbina/internal_services/scripts/stop_stack.sh`
- Full stop/start scripts (with ragflow/qdrant):
  - `/opt/orbina/internal_services/scripts/start_stack_with_ragflow.sh`
  - `/opt/orbina/internal_services/scripts/stop_stack_with_ragflow.sh`
