# Katilim Failover Docs Bundle

Patch image:

- intended tag: `aliennor/internal-services-katilim-failover-docs-20260331:0.1.0`

Goal:

- deliver the expanded Katilim failover architecture docs to a company server
  through a Linux amd64 Docker image
- include:
  - the current failover diagrams
  - the explanation notes
  - the optional `Airflow` case
  - the optional `Langfuse` alternative
- extract them into the architecture docs folder without modifying the live
  `/opt/orbina/internal_services` runtime

This bundle touches only:

- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/README.md`
- `/opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/*`

It does not touch:

- running compose stacks
- service configs under `/opt/orbina/internal_services`
- secrets
- databases
- nginx runtime

Included artifacts:

- updated architecture index `README.md`
- failover docs pack:
  - current `Phoenix`-based diagrams
  - simple diagrams and ASCII summary
  - `katilim-failover-explained-2026-03-26.md`
  - `katilim-failover-with-airflow-separate-case-2026-03-26.md`
  - `katilim-failover-with-airflow-simple.{d2,svg}`
  - `katilim-failover-langfuse-reference-2026-03-26.md`
  - `katilim-failover-langfuse-reference.{d2,svg}`
  - `katilim-failover-langfuse-simple.{d2,svg}`
  - updated selection note:
    - `Langfuse` reference chosen for banka / Katilim / Dinamik
    - iştiraks remain separate

## 1. Pull The Image On The Company Server

```bash
docker pull aliennor/internal-services-katilim-failover-docs-20260331:0.1.0
```

## 2. Prepare The Target Directory

```bash
sudo mkdir -p /opt/orbina/architecture
```

## 3. Optional Backup Of Existing Docs

```bash
STAMP="$(date +%Y%m%d_%H%M%S)" && BACKUP_DIR="/opt/orbina/backups/katilim_failover_docs_$STAMP" && sudo mkdir -p "$BACKUP_DIR"
```

```bash
if [ -d /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 ]; then sudo cp -R /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16 "$BACKUP_DIR/"; fi
```

## 4. Extract The Bundle

```bash
docker run --rm -v /opt/orbina/architecture:/output aliennor/internal-services-katilim-failover-docs-20260331:0.1.0 /output
```

## 5. Validate The Extracted Files

```bash
find /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25 -maxdepth 1 -type f | sort
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/*.svg
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/*.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/*ascii.txt
```

## 6. Main Files To Open

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/README.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/katilim-failover-explained-2026-03-26.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/katilim-failover-with-airflow-separate-case-2026-03-26.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/katilim-failover-langfuse-reference-2026-03-26.md
```

```bash
ls -1 /opt/orbina/architecture/arf_subsidiary_architecture_2026_03_16/katilim-failover-ragflow-3infra-2026-03-25/*simple*.svg
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
