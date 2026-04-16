# Katilim AA Core / Warm Utility Rollout

Patch bundle folder:

- `internal_services_image_katilim_aa_core_warm_utility_2026_03_22`

Purpose:

- replace `Langfuse` with `Phoenix`
- make `LiteLLM` active/active on `manavgat`
- make `Phoenix` active/active on `mercek`
- add `Metabase` as a utility service on `metabase`
- keep `OpenWebUI`, `n8n`, `Metabase`, `Qdrant`, `observability`, and internal
  `RAGFlow` in warm-standby failover
- switch app-state databases to DB-team PostgreSQL
- split HA readiness into `/ready-api`, `/ready-phoenix`, and `/ready-utility`

This patch bundle touches:

- `litellm`
- `phoenix`
- `phoenix-reporting`
- `metabase`
- `n8n`
- `openweb-ui`
- `ops/ha`
- `ops/install/katilim`
- `ops/systemd`

It also removes these retired systemd units from the target tree:

- `/opt/orbina/internal_services/ops/systemd/internal-services-langfuse.service`
- `/opt/orbina/internal_services/ops/systemd/internal-services-shared-postgres.service`

It does not create or manage the DB-team PostgreSQL objects. Those must exist
before starting the patched stack.

## 1. Preconditions

Confirm with the DB team:

- one stable HA PostgreSQL writer endpoint
- connectivity from both Katilim VMs
- credentials and TLS settings for:
  - `litellm_app`
  - `phoenix_app`
  - `phoenix_reporting`
  - `metabase_app`
  - `n8n_app`

## 2. Back Up The Current Snapshot

```bash
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/opt/orbina/backups/katilim_aa_core_warm_utility_$STAMP"
sudo mkdir -p "$BACKUP_DIR"
```

```bash
sudo tar -C /opt/orbina -czf "$BACKUP_DIR/internal_services_before_patch.tar.gz" internal_services
```

```bash
cd "$BACKUP_DIR" && sha256sum internal_services_before_patch.tar.gz > SHA256SUMS.txt
```

## 3. Apply The Patch Bundle

If using the folder directly on the server:

```bash
cd /opt/orbina/internal_services_image_katilim_aa_core_warm_utility_2026_03_22
sudo sh apply-patch.sh /opt/orbina
```

If using a built image later:

```bash
docker run --rm -v /opt/orbina:/output aliennor/internal-services-katilim-aa-core-warm-utility-20260322:0.1.0 /output
```

## 4. Refresh The Secure Env Bundle Inputs

Update these files under `/opt/orbina/internal_services` with real DB-team DSNs
and public URLs before restart:

- `litellm/.env`
- `phoenix/.env`
- `phoenix-reporting/.env`
- `metabase/.env`
- `n8n/.env`

Then re-run:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
sudo bash prepare-secure-config-bundle.sh inventory.prod.env /opt/orbina/incoming/katilim_secure_config_aa_core_warm_utility.tar.gz
```

If the secure bundle is already staged on the target:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
sudo bash apply-secure-config-bundle.sh /opt/orbina/incoming/katilim_secure_config_aa_core_warm_utility.tar.gz /opt/orbina
```

## 5. Validate Config Before Restart

```bash
cd /opt/orbina/internal_services/litellm && docker compose config >/tmp/litellm.compose.out
cd /opt/orbina/internal_services/phoenix && docker compose config >/tmp/phoenix.compose.out
cd /opt/orbina/internal_services/metabase && docker compose config >/tmp/metabase.compose.out
cd /opt/orbina/internal_services/phoenix-reporting && docker compose config >/tmp/phoenix-reporting.compose.out
cd /opt/orbina/internal_services/openweb-ui && docker compose config >/tmp/openweb-ui.compose.out
cd /opt/orbina/internal_services/n8n && docker compose config >/tmp/n8n.compose.out
```

```bash
bash /opt/orbina/internal_services/ops/ha/preflight-check.sh --role active
```

```bash
rg -n 'langfuse|shared-postgres|shared_postgres' /opt/orbina/internal_services/litellm /opt/orbina/internal_services/openweb-ui /opt/orbina/internal_services/ops/ha /opt/orbina/internal_services/ops/install/katilim /opt/orbina/internal_services/ops/systemd
```

The final `rg` command should return no matches.

## 6. Restart In The New Topology

On the utility-primary VM:

```bash
cd /opt/orbina/internal_services
sudo bash ops/ha/stop-active.sh || true
sudo bash ops/ha/start-active.sh
```

On the utility-standby VM:

```bash
cd /opt/orbina/internal_services
sudo bash ops/ha/stop-passive.sh || true
sudo bash ops/ha/start-passive.sh
```

Re-enable sync timers on the utility-primary VM if they are part of the
deployment flow:

```bash
sudo systemctl enable --now internal-services-ha-sync-light.timer internal-services-ha-sync-heavy.timer
```

## 7. Smoke Checks

Local HA endpoints:

```bash
curl -fsS http://127.0.0.1:18081/ready-api
curl -fsS http://127.0.0.1:18081/ready-phoenix
curl -fsS http://127.0.0.1:18081/ready-utility
curl -fsS http://127.0.0.1:18081/status
```

Hostname routing:

```bash
curl -fsS --resolve manavgat.yzyonetim.ziraatkatilim.local:80:127.0.0.1 http://manavgat.yzyonetim.ziraatkatilim.local/health
curl -fsS --resolve mercek.yzyonetim.ziraatkatilim.local:80:127.0.0.1 http://mercek.yzyonetim.ziraatkatilim.local/
curl -fsS --resolve zfgasistan.yzyonetim.ziraatkatilim.local:80:127.0.0.1 http://zfgasistan.yzyonetim.ziraatkatilim.local/
curl -fsS --resolve aykal.yzyonetim.ziraatkatilim.local:80:127.0.0.1 http://aykal.yzyonetim.ziraatkatilim.local/
curl -fsS --resolve metabase.yzyonetim.ziraatkatilim.local:80:127.0.0.1 http://metabase.yzyonetim.ziraatkatilim.local/
```

## 8. Rollback

```bash
sudo rm -rf /opt/orbina/internal_services
sudo tar -C /opt/orbina -xzf "$BACKUP_DIR/internal_services_before_patch.tar.gz"
```

Then restore the previous service state with the prior HA flow.

## 9. Scope Limits

This patch intentionally does not:

- create DB-team databases or roles
- seed Metabase dashboards
- harden Phoenix auth beyond the private LB/TLS surface
- change the one-VIP load-balancer model
