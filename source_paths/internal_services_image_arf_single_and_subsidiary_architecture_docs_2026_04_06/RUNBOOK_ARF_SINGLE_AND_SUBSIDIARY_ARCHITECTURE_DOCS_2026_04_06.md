# ARF Single And Subsidiary Architecture Docs Bundle Runbook

Date:

- `2026-04-06`

Patch image tag:

- `docker.io/aliennor/internal-services-arf-single-and-subsidiary-architecture-docs-20260406:0.1.3`

## Goal

Pull one Docker image on the company server and extract:

- the final subsidiary shared-backend architecture pack
- the final single-company shared-backend architecture pack
- the final graph-book PDF plus editable page SVG masters
- the key technical notes and architecture index that explain the broader ARF
  topology and shared-state model

## Scope

This bundle is documentation only.

It does not:

- modify secrets
- restart running services
- change the live runtime tree under `/opt/orbina/internal_services`

It touches only:

- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*`
- `/opt/orbina/architecture/arf_architecture_docs_bundle_info/*`

## Build And Push

This bundle is built from:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_arf_single_and_subsidiary_architecture_docs_2026_04_06`

Reference build/push commands:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_arf_single_and_subsidiary_architecture_docs_2026_04_06
docker buildx build --platform linux/amd64 -t docker.io/aliennor/internal-services-arf-single-and-subsidiary-architecture-docs-20260406:0.1.3 --load .
docker push docker.io/aliennor/internal-services-arf-single-and-subsidiary-architecture-docs-20260406:0.1.3
```

## 1. Pull The Image On The Company Server

```bash
docker pull docker.io/aliennor/internal-services-arf-single-and-subsidiary-architecture-docs-20260406:0.1.3
```

## 2. Prepare The Target Directory

```bash
sudo mkdir -p /opt/orbina/architecture
```

## 3. Optional Backup Of Existing Docs

```bash
STAMP="$(date +%Y%m%d_%H%M%S)" && BACKUP_DIR="/opt/orbina/backups/arf_architecture_docs_${STAMP}" && sudo mkdir -p "$BACKUP_DIR"
```

```bash
if [ -d /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 ]; then sudo cp -R /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 "$BACKUP_DIR/"; fi
```

```bash
if [ -d /opt/orbina/architecture/arf_architecture_docs_bundle_info ]; then sudo cp -R /opt/orbina/architecture/arf_architecture_docs_bundle_info "$BACKUP_DIR/"; fi
```

## 4. Extract The Bundle

```bash
docker run --rm -v /opt/orbina/architecture:/output docker.io/aliennor/internal-services-arf-single-and-subsidiary-architecture-docs-20260406:0.1.3 /output
```

## 5. Validate The Extracted Files

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 -maxdepth 1 -type f | sort
```

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/subsidiary-3x-shared-backend-final-2026-04-06 -maxdepth 1 -type f | sort
```

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/single-company-shared-backend-final-2026-04-06 -maxdepth 1 -type f | sort
```

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/final-graph-book-2026-04-06 -maxdepth 2 -type f | sort
```

```bash
find /opt/orbina/architecture/arf_architecture_docs_bundle_info -maxdepth 1 -type f | sort
```

## 6. Main Files To Open

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/README.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/subsidiary-3x-shared-backend-final-2026-04-06/README.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/single-company-shared-backend-final-2026-04-06/README.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/final-graph-book-2026-04-06/arf-single-and-subsidiary-final-graph-book-2026-04-06.pdf
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/final-graph-book-2026-04-06/page_svgs
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/*technical-deep-dive*.md
```

```bash
ls -1 /opt/orbina/architecture/arf_architecture_docs_bundle_info/RUNBOOK_ARF_SINGLE_AND_SUBSIDIARY_ARCHITECTURE_DOCS_2026_04_06.md
```

## 7. Suggested Review Order

1. `arf_subsidiary_architecture_2026_03_16/README.md`
2. `subsidiary-3x-shared-backend-final-2026-04-06/README.md`
3. `single-company-shared-backend-final-2026-04-06/README.md`
4. `final-graph-book-2026-04-06/arf-single-and-subsidiary-final-graph-book-2026-04-06.pdf`
5. `technical-deep-dive-current-2vm-and-planned-multi-subsidiary-2026-03-18.md`
6. `database-systems-explained-2026-03-18.md`

## 8. Rollback

If you took the optional backup and need to restore:

```bash
sudo rm -rf /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16
```

```bash
if [ -d "$BACKUP_DIR/arf_subsidiary_architecture_2026_03_16" ]; then sudo cp -R "$BACKUP_DIR/arf_subsidiary_architecture_2026_03_16" /opt/orbina/architecture/; fi
```

```bash
sudo rm -rf /opt/orbina/architecture/arf_architecture_docs_bundle_info
```

```bash
if [ -d "$BACKUP_DIR/arf_architecture_docs_bundle_info" ]; then sudo cp -R "$BACKUP_DIR/arf_architecture_docs_bundle_info" /opt/orbina/architecture/; fi
```

## 9. Notes

- This is a documentation bundle, not a live runtime patch.
- It is safe to extract without restarting any internal services.
- The image is intended for restricted company servers that can pull from
  Docker Hub.
- If you want the same artifacts copied to another path, change the host-side
  bind mount in step `4`.
