# ARF Subsidiary Architecture Docs Bundle

Patch image:

- `aliennor/internal-services-arf-subsidiary-architecture-docs-20260318:0.1.0`
- digest: `sha256:c18c4e600472ad33e2d787fe43153b3886920a6d937a1f84df30a4613232a43c`

Goal:

- deliver the current ARF subsidiary architecture notes and top-down D2
  topology artifacts to a company server via a Docker image
- extract them into a documentation folder without modifying the live
  `/opt/orbina/internal_services` runtime

This bundle touches only:

- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*`

It does not touch:

- running compose stacks
- service configs under `/opt/orbina/internal_services`
- secrets
- databases
- nginx runtime

Included artifacts:

- current inherited `2VM` architecture note
- planned multi-subsidiary architecture note
- technical HA/DB deep-dive note
- DB/storage explanation note
- top-down D2 sources and rendered SVGs

## 1. Pull The Image On The Company Server

```bash
docker pull aliennor/internal-services-arf-subsidiary-architecture-docs-20260318:0.1.0
```

## 2. Prepare The Target Directory

```bash
sudo mkdir -p /opt/orbina/architecture
```

## 3. Optional Backup Of Existing Docs

```bash
STAMP="$(date +%Y%m%d_%H%M%S)" && BACKUP_DIR="/opt/orbina/backups/arf_subsidiary_architecture_docs_$STAMP" && sudo mkdir -p "$BACKUP_DIR"
```

```bash
if [ -d /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 ]; then sudo cp -R /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 "$BACKUP_DIR/"; fi
```

## 4. Extract The Bundle

```bash
docker run --rm -v /opt/orbina/architecture:/output aliennor/internal-services-arf-subsidiary-architecture-docs-20260318:0.1.0 /output
```

## 5. Validate The Extracted Files

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 -maxdepth 1 -type f | sort
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*.svg
```

## 6. Main Files To Open

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*current-2vm*.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*planned-multi-subsidiary*.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/arf-subsidiaries-topdown-ha-mechanics*.svg
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
- If you want the same artifacts copied to another path, change the host-side
  bind mount in step `4`.
