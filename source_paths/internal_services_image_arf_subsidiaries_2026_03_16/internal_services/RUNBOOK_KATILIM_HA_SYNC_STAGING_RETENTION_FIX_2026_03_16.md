# Katilim HA Sync Staging Retention Fix

Use this runbook on already-installed Katilim dev or prod VM pairs when
timestamped sync staging folders have started filling the host.

Purpose:

- move HA sync staging off the small `/var` filesystem
- keep only a small retained history of successful sync runs
- refresh the installed HA sync script with the staging-retention cleanup logic

Important:

- the shared install bundle is intentionally sanitized
- it can overwrite `/opt/orbina/internal_services` without the managed service `.env` files
- after extracting the shared install bundle, reapply the matching encrypted config image on the same VM before using the stack again
- if the managed `.env` files already disappeared on a VM, use:
  - `RUNBOOK_KATILIM_RECOVER_MANAGED_ENVS_AFTER_BUNDLE_REFRESH_2026_03_16.md`

This fix uses the shared install bundle:

- `aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21`

Result after apply:

- active and passive nodes use `SYNC_STAGING_DIR=/opt/orbina/ha-staging`
- successful syncs keep only the latest `2` timestamped staging runs locally and remotely
- old accumulated timestamp folders can be cleaned once immediately

## 1. On `VM1` And `VM2`, Refresh The Installed Script From The Shared Bundle

```bash
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21
```

```bash
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r21 /output
```

Before continuing, reapply the matching encrypted config bundle on the same VM.

For dev:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

```bash
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9
```

```bash
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output
```

For prod:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

```bash
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1
```

```bash
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-prod-2vm-2026-03-11-r1 /output
```

Optional check:

```bash
ls -l /opt/orbina/internal_services/openweb-ui/.env
```

## 2. On `VM1` And `VM2`, Move Sync Staging To Root-Backed Storage

```bash
sudo mkdir -p /opt/orbina/ha-staging
```

```bash
sudo sed -i.bak '/^SYNC_STAGING_DIR=/d;/^SYNC_STAGING_KEEP_RUNS=/d' /etc/internal-services/ha.env
```

```bash
printf '\nSYNC_STAGING_DIR=/opt/orbina/ha-staging\nSYNC_STAGING_KEEP_RUNS=2\n' | sudo tee -a /etc/internal-services/ha.env >/dev/null
```

```bash
grep -E '^(SYNC_STAGING_DIR|SYNC_STAGING_KEEP_RUNS)=' /etc/internal-services/ha.env
```

Expected output:

- `SYNC_STAGING_DIR=/opt/orbina/ha-staging`
- `SYNC_STAGING_KEEP_RUNS=2`

## 3. One-Time Cleanup Of Old Timestamped Staging Folders

Run this on `VM1` and `VM2` to keep only the latest `2` old runs under the
previous `/var` staging path:

```bash
sudo bash -lc 'dir=/var/lib/internal-services-ha/staging; keep=2; [ -d "$dir" ] || exit 0; n=0; find "$dir" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" 2>/dev/null | grep -E "^[0-9]{8}_[0-9]{6}$" | sort -r | while IFS= read -r entry; do n=$((n + 1)); if [ "$n" -gt "$keep" ]; then rm -rf -- "$dir/$entry"; fi; done'
```

Optional check:

```bash
sudo find /var/lib/internal-services-ha/staging -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort
```

## 4. Re-Run The Initial Full Sync From `VM1`

```bash
cd /opt/orbina/internal_services
```

```bash
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

Successful end should print:

- `Passive volume sync complete for profile all.`
- `Initial full sync completed and VM1 sync timers are enabled.`

## 5. Validate The New Staging Path And Retention Behavior

On `VM1`:

```bash
sudo find /opt/orbina/ha-staging -mindepth 1 -maxdepth 2 -type d | sort
```

```bash
systemctl status internal-services-ha-sync-light.timer --no-pager
```

```bash
systemctl status internal-services-ha-sync-heavy.timer --no-pager
```

On `VM2`:

```bash
sudo find /opt/orbina/ha-staging -mindepth 1 -maxdepth 2 -type d | sort
```

Notes:

- failed sync runs may still leave their current timestamp directory behind for inspection
- successful syncs prune older retained history automatically
- if you want a different history length later, change only:
  - `SYNC_STAGING_KEEP_RUNS=<count>`
  in `/etc/internal-services/ha.env` on both VMs
