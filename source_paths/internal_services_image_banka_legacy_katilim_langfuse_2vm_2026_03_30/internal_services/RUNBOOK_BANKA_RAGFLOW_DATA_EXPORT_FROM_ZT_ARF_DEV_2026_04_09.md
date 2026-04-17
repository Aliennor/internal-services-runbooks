# Banka Ragflow Data Export Runbook: From ZT ARF Dev To Banka Targets

Date: 2026-04-09

Scope:
- source is the ZT ARF dev server
- source runtime is `docker`
- default export is the full core Ragflow state set
- operator downloads the export from the source server, then uploads it manually
- restore happens on the active banka node only

Authoritative installer workspace:
- `internal_services_image_banka_legacy_katilim_langfuse_2vm_2026_03_30/internal_services`

Target upload locations:
- active banka rollout on `10.11.115.106`:
  - `/opt/orbina/incoming/ragflow_volumes_export`
- dev single-node rollout on `10.11.115.108`:
  - `/opt/orbina/incoming/ragflow_volumes_export`

Do not upload this export separately to `10.11.115.107`.

Why:
- `bootstrap-vm1-active.sh` restores Ragflow automatically from
  `/opt/orbina/incoming/ragflow_volumes_export` if `volume-names.txt` exists
- later `106 -> 107` HA sync carries:
  - Ragflow volumes: `esdata01`, `mysql_data`, `minio_data`, `redis_data`
  - Qdrant is intentionally excluded unless an operator explicitly enables it

Default export scope:
- `esdata01`
- `minio_data`
- `mysql_data`
- `redis_data`

This covers the core Ragflow state, including chunk/index/object-store data.

## 0) Prerequisite On The Source Server

On the ZT ARF dev server, verify `docker` works:

```bash
docker version
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker volume ls
```

## 1) Pull The Export Script Package On The Source Server

On the ZT ARF dev server, pull the installer bundle from Docker Hub and extract
the script package locally:

```bash
mkdir -p /opt/orbina-export-tools

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r31
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina-export-tools:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r31 \
  /output

install -m 0755 \
  /opt/orbina-export-tools/internal_services/ops/install/katilim/export-ragflow-volumes.sh \
  /root/export-ragflow-volumes.sh
```

## 2) Inspect The Actual Ragflow-Related Docker Volumes First

On the ZT ARF dev server:

```bash
docker volume ls --format '{{.Name}}' | sort | egrep 'esdata01|minio_data|mysql_data|redis_data|ragflow'
```

This shows the real Docker volume names that will be matched by the export.

The exporter matches both:
- exact names such as `esdata01`
- prefixed Compose names such as `docker_esdata01`

## 3) Export The Full Core Ragflow State Set

On the ZT ARF dev server:

```bash
cd /root

TS=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="/root/ragflow_volumes_export_${TS}"

SELECTED_VOLUME_BASES=esdata01,minio_data,mysql_data,redis_data \
  /root/export-ragflow-volumes.sh "$EXPORT_DIR"
```

Expected result:
- a folder like `/root/ragflow_volumes_export_20260409_123456`
- one `*.tar.gz` per exported volume
- `volume-names.txt`
- `SHA256SUMS.txt`

Inspect the result:

```bash
cd "$EXPORT_DIR"
ls -lh
cat volume-names.txt
test -f SHA256SUMS.txt || {
  echo "Export is incomplete: SHA256SUMS.txt is missing. Do not archive or upload this export."
  exit 1
}
cat SHA256SUMS.txt
```

If you only see `volume-names.txt` and no `SHA256SUMS.txt`, the export failed
before all volume tarballs and checksums were written. Delete that partial
export folder and rerun this section with the latest script package:

```bash
rm -rf "$EXPORT_DIR"
```

## 4) Archive It For Transfer

On the ZT ARF dev server:

```bash
cd /root
EXPORT_BASENAME=$(basename "$EXPORT_DIR")
ARCHIVE_PATH="/root/${EXPORT_BASENAME}.tar.gz"
tar -C /root -czf "$ARCHIVE_PATH" "$EXPORT_BASENAME"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$ARCHIVE_PATH"
else
  shasum -a 256 "$ARCHIVE_PATH"
fi
```

Preferred transfer path: from the ZT ARF dev server, copy the export directly
to the target node.

For active rollout on `10.11.115.106`:

```bash
TARGET_HOST=10.11.115.106
ssh root@"$TARGET_HOST" "mkdir -p /opt/orbina/incoming/ragflow_volumes_export"
rsync -a "${EXPORT_DIR}/" root@"$TARGET_HOST":/opt/orbina/incoming/ragflow_volumes_export/
```

For dev single-node rollout on `10.11.115.108`:

```bash
TARGET_HOST=10.11.115.108
ssh root@"$TARGET_HOST" "mkdir -p /opt/orbina/incoming/ragflow_volumes_export"
rsync -a "${EXPORT_DIR}/" root@"$TARGET_HOST":/opt/orbina/incoming/ragflow_volumes_export/
```

If source-server-to-target SSH/rsync is not allowed, move `$ARCHIVE_PATH`
through your approved internal file-transfer route, place it on the active
target or dev target, and extract it there:

```bash
ARCHIVE_PATH=/root/ragflow_volumes_export_<timestamp>.tar.gz
mkdir -p /tmp/ragflow-import
tar -xzf "$ARCHIVE_PATH" -C /tmp/ragflow-import
EXPORT_FOLDER=$(find /tmp/ragflow-import -maxdepth 1 -type d -name 'ragflow_volumes_export_*' | head -n 1)

mkdir -p /opt/orbina/incoming/ragflow_volumes_export
rsync -a "${EXPORT_FOLDER}/" /opt/orbina/incoming/ragflow_volumes_export/
```

## 5) Verify It On The Banka Target

For active rollout on `10.11.115.106`:

```bash
ssh root@10.11.115.106
ls -lh /opt/orbina/incoming/ragflow_volumes_export
cat /opt/orbina/incoming/ragflow_volumes_export/volume-names.txt
```

For dev single-node rollout on `10.11.115.108`:

```bash
ssh root@10.11.115.108
ls -lh /opt/orbina/incoming/ragflow_volumes_export
cat /opt/orbina/incoming/ragflow_volumes_export/volume-names.txt
```

## 6) Preferred Restore Timing

Preferred timing is:
1. finish the normal installer tree extraction and secure bundle application
2. upload `ragflow_volumes_export` to `/opt/orbina/incoming`
3. only then run:
   - `sudo ops/install/katilim/bootstrap-vm1-active.sh`

Reason:
- `bootstrap-vm1-active.sh` checks `/opt/orbina/incoming/ragflow_volumes_export`
- if `volume-names.txt` is present there, it restores automatically before the
  active stack is brought up

For the main banka rollout, follow this runbook before:
- `RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md`

For the dev box, follow this runbook before:
- `RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_09.md`

## 7) Manual Restore Fallback

If the export is already uploaded but you need to restore it manually on the
active target:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
```

Use this only on the active node:
- `10.11.115.106` for the main rollout
- `10.11.115.108` for the dev box

Do not run it on `10.11.115.107`.

## 8) Do Not Seed `10.11.115.107` Manually

For the active/passive banka topology:
- restore Ragflow only on `10.11.115.106`
- bootstrap `10.11.115.107` as passive normally
- then enable HA sync from `VM1`

The current HA volume sync manifest already covers:
- Ragflow: `esdata01`, `mysql_data`, `minio_data`, `redis_data`
- Qdrant is disabled by default and not required for this Banka path

That is why the passive node does not need a separate manual Ragflow volume
upload.
