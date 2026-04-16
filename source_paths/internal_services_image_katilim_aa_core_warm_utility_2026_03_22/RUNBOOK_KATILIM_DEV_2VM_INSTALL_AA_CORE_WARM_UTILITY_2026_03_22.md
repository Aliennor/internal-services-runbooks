# Katilim Dev 2-VM Install Runbook

Date: 2026-03-22

Target:

- `VM1`: `10.210.22.88`
- `VM2`: `10.210.22.89`
- dev LB / VIP reference: `10.210.22.164`

Hostnames:

- `zfgasistan.yzyonetim-dev.ziraatkatilim.local` -> OpenWebUI
- `manavgat.yzyonetim-dev.ziraatkatilim.local` -> LiteLLM
- `aykal.yzyonetim-dev.ziraatkatilim.local` -> n8n
- `mercek.yzyonetim-dev.ziraatkatilim.local` -> Phoenix
- `metabase.yzyonetim-dev.ziraatkatilim.local` -> Metabase

Topology after install:

- both VMs run:
  - `nginx`
  - `LiteLLM`
  - `Phoenix`
- only `VM1` runs initially:
  - `OpenWebUI`
  - `n8n`
  - `Metabase`
  - `phoenix-reporting`
  - `observability`
  - `Qdrant`
  - internal `RAGFlow`
- `VM2` stays warm-standby for utility services

This runbook assumes you are starting from the updated repo state in:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services`

and the rollout bundle folder:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_katilim_aa_core_warm_utility_2026_03_22`

## 1. Pre-Reqs Before Touching The VMs

You need these first:

1. DB-team PostgreSQL is ready with one stable writer endpoint.
2. Both dev VMs can reach that endpoint on `5432`.
3. You have credentials and TLS details for:
   - `litellm_app`
   - `phoenix_app`
   - `phoenix_reporting`
   - `metabase_app`
   - `n8n_app`
4. SSH access to both VMs as `root` or a sudo-capable user.
5. Docker and systemd are available on both VMs.

Do not proceed without the DB endpoint and credentials. This topology no longer
uses local `shared-postgres` for active runtime.

## 2. Prepare The Local Repo Inputs

Work from:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
```

Edit the live env files with the real dev DB-team values:

- `litellm/.env`
- `phoenix/.env`
- `phoenix-reporting/.env`
- `metabase/.env`
- `n8n/.env`

Minimum values to replace:

- [litellm/.env](/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/litellm/.env)
  - `LITELLM_DATABASE_URL`
- [phoenix/.env](/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/phoenix/.env)
  - `PHOENIX_SQL_DATABASE_URL`
  - `PHOENIX_PUBLIC_BASE_URL`
- [phoenix-reporting/.env](/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/phoenix-reporting/.env)
  - `PHOENIX_REPORTING_DATABASE_URL`
  - `PHOENIX_PROJECT_IDENTIFIER`
- [metabase/.env](/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/metabase/.env)
  - `MB_DB_CONNECTION_URI`
  - `MB_SITE_URL`
- [n8n/.env](/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/n8n/.env)
  - `N8N_DB_HOST`
  - `N8N_DB_PORT`
  - `N8N_DB_NAME`
  - `N8N_DB_USER`
  - `N8N_DB_PASSWORD`

Sanity-check the dev inventory:

```bash
sed -n '1,220p' /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/ops/install/katilim/inventory.env
```

It should match:

- `VM1_HOST=10.210.22.88`
- `VM2_HOST=10.210.22.89`
- dev hostnames for `manavgat`, `mercek`, `zfgasistan`, `aykal`, `metabase`

## 3. Local Validation Before Transfer

Run these from your workstation:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/litellm && docker compose config >/tmp/litellm.dev.compose.out
```

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/phoenix && docker compose config >/tmp/phoenix.dev.compose.out
```

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/metabase && docker compose config >/tmp/metabase.dev.compose.out
```

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/phoenix-reporting && docker compose config >/tmp/phoenix-reporting.dev.compose.out
```

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/openweb-ui && docker compose config >/tmp/openweb-ui.dev.compose.out
```

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/n8n && docker compose config >/tmp/n8n.dev.compose.out
```

```bash
bash /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/ops/ha/preflight-check.sh --role active || true
```

The last command will fail on macOS for `systemctl unavailable`; that is fine
locally. It should pass on the Linux VMs.

## 4. Build Or Use The Patch Bundle

The patch image is already buildable from:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_katilim_aa_core_warm_utility_2026_03_22`

If you want to rebuild it locally:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_katilim_aa_core_warm_utility_2026_03_22
docker buildx build --load -t aliennor/internal-services-katilim-aa-core-warm-utility-20260322:0.1.0 .
```

For dev-first testing, the simplest path is usually to push the updated tree to
the VMs using the existing Katilim install scripts rather than only applying the
patch image.

## 5. Prepare The Secure Config Bundle

From your workstation:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/ops/install/katilim
```

Render HA envs:

```bash
bash render-ha-env.sh inventory.env
```

Create the secure bundle:

```bash
bash prepare-secure-config-bundle.sh inventory.env /Users/batur/Desktop/2025_2026_Stuff/arf_project/katilim_secure_config_dev_aa_core_warm_utility_20260322.tar.gz
```

That bundle carries:

- `litellm/.env`
- `phoenix/.env`
- `phoenix-reporting/.env`
- `metabase/.env`
- `n8n/.env`
- `openweb-ui/.env`
- `observability/.env`
- `qdrant/.env`
- `ha.vm1.env`
- `ha.vm2.env`

## 6. Transfer The Install Tree To Both Dev VMs

Still from:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services/ops/install/katilim
```

Push the install tree:

```bash
bash push-to-vms.sh inventory.env
```

If you prefer tarball transfer instead:

```bash
bash prepare-transfer-tarball.sh inventory.env
```

Then copy and extract it manually on both VMs under `/opt/orbina`.

Copy the secure bundle to both VMs, for example:

```bash
scp /Users/batur/Desktop/2025_2026_Stuff/arf_project/katilim_secure_config_dev_aa_core_warm_utility_20260322.tar.gz root@10.210.22.88:/opt/orbina/incoming/
scp /Users/batur/Desktop/2025_2026_Stuff/arf_project/katilim_secure_config_dev_aa_core_warm_utility_20260322.tar.gz root@10.210.22.89:/opt/orbina/incoming/
```

## 7. Install VM1 First

SSH to `VM1`:

```bash
ssh root@10.210.22.88
```

Apply the secure bundle:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash apply-secure-config-bundle.sh /opt/orbina/incoming/katilim_secure_config_dev_aa_core_warm_utility_20260322.tar.gz /opt/orbina
```

Install node services as active:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash install-node.sh --role active
```

Bootstrap VM1:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash bootstrap-vm1-active.sh
```

What this should do:

- install unit files
- run HA preflight
- start `nginx`, `LiteLLM`, `Phoenix`
- start utility stack on VM1
- wait for `/ready-utility`
- run the active smoke test

## 8. Validate VM1 Before Adding VM2

On `VM1`:

```bash
curl -fsS http://127.0.0.1:18081/ready-api
curl -fsS http://127.0.0.1:18081/ready-phoenix
curl -fsS http://127.0.0.1:18081/ready-utility
curl -fsS http://127.0.0.1:18081/status
```

Check services:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Check routing locally:

```bash
curl -fsS --resolve manavgat.yzyonetim-dev.ziraatkatilim.local:80:127.0.0.1 http://manavgat.yzyonetim-dev.ziraatkatilim.local/health
```

```bash
curl -fsS --resolve mercek.yzyonetim-dev.ziraatkatilim.local:80:127.0.0.1 http://mercek.yzyonetim-dev.ziraatkatilim.local/
```

```bash
curl -fsS --resolve zfgasistan.yzyonetim-dev.ziraatkatilim.local:80:127.0.0.1 http://zfgasistan.yzyonetim-dev.ziraatkatilim.local/
```

```bash
curl -fsS --resolve aykal.yzyonetim-dev.ziraatkatilim.local:80:127.0.0.1 http://aykal.yzyonetim-dev.ziraatkatilim.local/
```

```bash
curl -fsS --resolve metabase.yzyonetim-dev.ziraatkatilim.local:80:127.0.0.1 http://metabase.yzyonetim-dev.ziraatkatilim.local/
```

Check DB-backed app startup logs:

```bash
docker logs --since 5m litellm
docker logs --since 5m phoenix
docker logs --since 5m n8n
docker logs --since 5m metabase
docker logs --since 5m phoenix-reporting
```

## 9. Runtime Tests On VM1

These are the critical behavior checks.

### 9.1 LiteLLM still works

```bash
curl -fsS http://127.0.0.1:4000/health
```

```bash
curl -sS http://127.0.0.1:4000/v1/models -H 'Authorization: Bearer <YOUR_LITELLM_MASTER_KEY>'
```

### 9.2 Phoenix UI is reachable

Open in browser through the dev LB:

- `https://mercek.yzyonetim-dev.ziraatkatilim.local`

Or locally:

```bash
curl -I http://127.0.0.1:6006/
```

### 9.3 Trace ingestion works

Make one real LiteLLM request from OpenWebUI or directly through LiteLLM, then
check Phoenix UI for the trace.

If Phoenix stays empty after requests, stop here and debug before touching VM2.

### 9.4 phoenix-reporting writes facts

On the reporting DB, confirm rows land in:

- `trace_usage_fact`
- `sync_state`
- `daily_usage_rollup`
- `weekly_usage_rollup`

If `psql` access is available:

```sql
SELECT count(*) FROM trace_usage_fact;
SELECT * FROM sync_state;
```

If you do not have DB shell access, inspect exporter logs:

```bash
docker logs --since 10m phoenix-reporting
```

## 10. Install VM2

SSH to `VM2`:

```bash
ssh root@10.210.22.89
```

Apply the secure bundle:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash apply-secure-config-bundle.sh /opt/orbina/incoming/katilim_secure_config_dev_aa_core_warm_utility_20260322.tar.gz /opt/orbina
```

Install node services as passive:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash install-node.sh --role passive
```

Bootstrap VM2:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash bootstrap-vm2-passive.sh
```

This should start:

- `nginx`
- `LiteLLM`
- `Phoenix`

and keep utility services stopped.

## 11. Validate VM2 Standby State

On `VM2`:

```bash
curl -fsS http://127.0.0.1:18081/ready-api
curl -fsS http://127.0.0.1:18081/ready-phoenix
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18081/ready-utility
curl -fsS http://127.0.0.1:18081/status
```

Expected:

- `/ready-api` -> `200`
- `/ready-phoenix` -> `200`
- `/ready-utility` -> not ready yet, typically `503`

Check running containers:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

`openwebui`, `n8n`, `metabase`, `phoenix-reporting`, and utility-only stacks
should not be running yet.

## 12. Enable Utility Sync From VM1

Back on `VM1`:

```bash
ssh root@10.210.22.88
cd /opt/orbina/internal_services/ops/install/katilim
bash enable-vm1-passive-sync.sh
```

This performs the first full sync and enables the sync timers.

After it finishes, re-check `VM2`:

```bash
ssh root@10.210.22.89
curl -fsS http://127.0.0.1:18081/status
```

You want fresh sync stamps in the HA status path.

## 13. Dev LB / VIP Checks

From a client machine that resolves the dev LB:

- `https://manavgat.yzyonetim-dev.ziraatkatilim.local`
- `https://mercek.yzyonetim-dev.ziraatkatilim.local`
- `https://zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `https://aykal.yzyonetim-dev.ziraatkatilim.local`
- `https://metabase.yzyonetim-dev.ziraatkatilim.local`

Confirm:

- `manavgat` works
- `mercek` works
- utility hostnames resolve to the utility-primary VM behavior

If the LB is health-based, update it so:

- API core health can use `/ready-api`
- Phoenix core health can use `/ready-phoenix`
- utility routing must use `/ready-utility`

Keep the single VIP model. Do not split to separate VIPs for this test.

## 14. Failover Test

Only do this after VM1 and VM2 both look healthy.

On `VM2`, confirm it is promotion-ready:

```bash
test -f /var/lib/internal-services-ha/promotion-ready && echo ready
```

Simulate utility-primary failure by stopping utility services or taking `VM1`
out of LB utility routing.

Then on `VM2`:

```bash
cd /opt/orbina/internal_services
bash ops/ha/promote-passive.sh
```

After promotion:

```bash
curl -fsS http://127.0.0.1:18081/ready-api
curl -fsS http://127.0.0.1:18081/ready-phoenix
curl -fsS http://127.0.0.1:18081/ready-utility
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Validate the public hostnames again through the dev LB.

## 15. Pass Criteria For Dev

Dev test is successful if all are true:

1. `VM1` comes up with all three readiness endpoints green.
2. `VM2` comes up with API + Phoenix ready and utility not ready before promotion.
3. LiteLLM requests succeed.
4. Phoenix shows real traces from LiteLLM.
5. `phoenix-reporting` writes reporting rows.
6. OpenWebUI, n8n, and Metabase are reachable on the utility-primary node.
7. Volume sync completes from VM1 to VM2.
8. Promotion on VM2 starts utility services successfully.

## 16. Rollback

If anything fails badly on a VM:

1. Stop the new services:

```bash
cd /opt/orbina/internal_services
bash ops/ha/stop-active.sh || true
bash ops/ha/stop-passive.sh || true
```

2. Restore the backed-up pre-patch tree if you took one.
3. Restore the old env files.
4. Restart the previous stack.

If you used the patch bundle directly, use the backup tar you created before
apply.

## 17. What To Avoid During Dev Test

- Do not test with fake DB DSNs.
- Do not assume Phoenix ingestion works just because containers are up.
- Do not promote VM2 before initial sync is completed.
- Do not remove the single VIP model just to make the test easier.
- Do not treat local macOS validation as proof of runtime correctness.

## 18. Short Operator Checklist

Use this condensed order:

1. Get DB-team endpoint and credentials.
2. Fill the five DB-backed env files locally.
3. Run local compose/config validation.
4. Render HA envs and create secure config bundle.
5. Push install tree and bundle to both dev VMs.
6. Install and bootstrap `VM1`.
7. Validate VM1 runtime, routing, tracing, reporting.
8. Install and bootstrap `VM2`.
9. Enable sync from `VM1`.
10. Validate standby behavior on `VM2`.
11. Test promotion on `VM2`.
