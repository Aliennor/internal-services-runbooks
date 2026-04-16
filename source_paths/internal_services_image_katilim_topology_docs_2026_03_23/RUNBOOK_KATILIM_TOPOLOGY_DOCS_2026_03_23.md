# Katilim Topology Docs Bundle

Patch image:

- intended tag: `aliennor/internal-services-katilim-topology-docs-20260323:0.1.0`
- pushed digest: `sha256:33f6ab66bccad22f5a48bff158d45258f8a96a825c373720ac40a59e44f3d620`

Goal:

- deliver the latest Katilim topology diagrams and their architecture index to a
  company server through a Linux amd64 Docker image
- extract them into the architecture docs folder without modifying the live
  `/opt/orbina/internal_services` runtime

This bundle touches only:

- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/README.md`
- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*`

It does not touch:

- running compose stacks
- service configs under `/opt/orbina/internal_services`
- secrets
- databases
- nginx runtime

Included artifacts:

- updated architecture index `README.md`
- Katilim final topology pack:
  - `katilim-aa-core-warm-utility-overview.{d2,svg}`
  - `katilim-layered-hierarchy.{d2,svg}`
  - `katilim-postgresql-service-map.{d2,svg}`
  - `katilim-phoenix-reporting-schema.{d2,svg}`
  - bundle `README.md`

## 1. Pull The Image On The Company Server

```bash
docker pull aliennor/internal-services-katilim-topology-docs-20260323:0.1.0
```

## 2. Prepare The Target Directory

```bash
sudo mkdir -p /opt/orbina/architecture
```

## 3. Optional Backup Of Existing Docs

```bash
STAMP="$(date +%Y%m%d_%H%M%S)" && BACKUP_DIR="/opt/orbina/backups/katilim_topology_docs_$STAMP" && sudo mkdir -p "$BACKUP_DIR"
```

```bash
if [ -d /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 ]; then sudo cp -R /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 "$BACKUP_DIR/"; fi
```

## 4. Extract The Bundle

```bash
docker run --rm -v /opt/orbina/architecture:/output aliennor/internal-services-katilim-topology-docs-20260323:0.1.0 /output
```

## 5. Validate The Extracted Files

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23 -maxdepth 1 -type f | sort
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*.svg
```

## 6. Main Files To Open

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/README.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*overview.svg
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*hierarchy.svg
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*postgresql-service-map.svg
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-aa-core-warm-utility-2026-03-23/*phoenix-reporting-schema.svg
```

## 7. Rollback

If you took the optional backup and need to restore:

```bash
sudo rm -rf /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16
```

```bash
if [ -d "$BACKUP_DIR/arf_subsidiary_architecture_2026_03_16" ]; then sudo cp -R "$BACKUP_DIR/arf_subsidiary_architecture_2026_03_16" /opt/orbina/architecture/; fi
```

## 8. Notes

- This is a documentation bundle, not a live runtime patch.
- It is safe to extract without restarting any internal services.
- The runbook assumes the image has been pushed to Docker Hub under the tag
  above.
- If you want the same artifacts copied to another path, change the host-side
  bind mount in step `4`.
