# Katilim Managed Env Recovery After Bundle Refresh

Use this runbook if a shared install bundle refresh removed managed service
`.env` files under `/opt/orbina/internal_services`, for example:

- `openweb-ui/.env`
- `litellm/.env`
- `langfuse/.env`
- `n8n/.env`
- `observability/.env`
- `qdrant/.env`

Cause:

- the shared install bundle is intentionally sanitized
- `docker run ... internal-services-katilim-install ...` with `BUNDLE_MODE=force`
  can replace `/opt/orbina/internal_services`
- the managed `.env` files come from the encrypted config image, not the shared
  install bundle

Use this recovery on either dev or prod VMs.

## 1. Pick The Correct Encrypted Config Image

For dev:

- `aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9`

For prod:

- `aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1`

## 2. Reapply The Matching Encrypted Config Bundle On The Affected VM

Read the passphrase into the shell:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

If the VM is dev:

```bash
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9
```

```bash
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output
```

If the VM is prod:

```bash
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1
```

```bash
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 /output
```

## 3. Confirm The Managed Env Files Are Back

```bash
ls -l /opt/orbina/internal_services/openweb-ui/.env
```

```bash
ls -l /opt/orbina/internal_services/litellm/.env
```

```bash
ls -l /opt/orbina/internal_services/langfuse/.env
```

```bash
ls -l /opt/orbina/internal_services/n8n/.env
```

```bash
ls -l /opt/orbina/internal_services/observability/.env
```

```bash
ls -l /opt/orbina/internal_services/qdrant/.env
```

## 4. If The Active Node Was Already Disturbed, Reassert The Active Stack

On an active VM:

```bash
cd /opt/orbina/internal_services
```

```bash
sudo ops/ha/start-single-node-fallback.sh
```

```bash
curl -fsS http://127.0.0.1:18081/ready
```

On a passive VM:

```bash
cd /opt/orbina/internal_services
```

```bash
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

```bash
curl -sS http://127.0.0.1:18081/status
```

## 5. Prevent The Same Mistake Next Time

If you are using the staging-retention fix path, follow:

- `RUNBOOK_KATILIM_HA_SYNC_STAGING_RETENTION_FIX_2026_03_16.md`

and do not stop after the shared install bundle refresh. Reapply the matching
encrypted config image on the same VM before using the stack again.
