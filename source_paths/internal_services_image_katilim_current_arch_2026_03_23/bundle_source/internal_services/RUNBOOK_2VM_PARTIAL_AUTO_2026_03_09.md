# 2-VM Partial-Auto Runbook

Preferred operator entrypoint:

- use `RUNBOOK_KATILIM_FULL_INSTALL_AND_HA_2026_03_10.md` for the Katilim full install plus HA flow
- keep this file as the generic HA operations reference

Scope:

- Baseline image: `aliennor/redis-09.03-internal:latest`
- Exported working tree: `/opt/orbina/internal_services`
- Topology: `VM1` active, `VM2` passive warm standby
- Failout: automatic through an external load balancer checking `http://<vm>:18081/ready`
- Database failover: operator-confirmed with `ops/ha/promote-passive.sh`

This runbook preserves the current working service configs. The HA layer is additive and lives in:

- `ops/ha`
- `ops/systemd/ha`
- `shared-postgres/docker-compose.primary-ha.yml`
- `shared-postgres/docker-compose.replica.yml`

## 1. Pre-flight

Confirm both new VMs have:

- Docker Engine with the Compose plugin
- `python3`
- `systemd`
- passwordless SSH from `VM1` to `VM2` for the sync user
- the same TLS files and the same service `.env` files placed as required by the exported March 9 stack

Decide the fixed node addresses up front:

- `VM1` active host/IP
- `VM2` passive host/IP
- external LB target configuration

## 2. Copy The Exported Tree To Both VMs

From the workstation that holds the exported March 9 snapshot:

```bash
rsync -a ./internal_services_image_2026_03_09/internal_services/ root@VM1:/opt/orbina/internal_services/
rsync -a ./internal_services_image_2026_03_09/internal_services/ root@VM2:/opt/orbina/internal_services/
```

Copy the same application secrets and certificates to both VMs. Do not change the current per-service `.env` structure.

## 3. Create The HA Env File On Both VMs

Start from:

- `/opt/orbina/internal_services/ops/ha/ha.env.example`

Write the real file to:

- `/etc/internal-services/ha.env`

Required fields on `VM1`:

```dotenv
NODE_ROLE=active
PRIMARY_HOST=<VM1-IP>
PEER_HOST=<VM2-IP>
PASSIVE_SSH_HOST=<VM2-IP>
PASSIVE_SSH_USER=root
PASSIVE_ROOT=/opt/orbina/internal_services
HA_STATE_DIR=/var/lib/internal-services-ha
HA_HEALTH_PORT=18081
POSTGRES_PRIMARY_PORT=5432
POSTGRES_REPLICATION_USER=internal_services_replicator
POSTGRES_REPLICATION_PASSWORD=<replication-password>
POSTGRES_REPLICATION_SLOT=internal_services_vm2
POSTGRES_REPLICATION_NETWORK=<CIDR-that-includes-VM2>
MAX_REPLICATION_LAG_SECONDS=30
```

Required fields on `VM2`:

```dotenv
NODE_ROLE=passive
PRIMARY_HOST=<VM1-IP>
PEER_HOST=<VM1-IP>
PASSIVE_ROOT=/opt/orbina/internal_services
HA_STATE_DIR=/var/lib/internal-services-ha
HA_HEALTH_PORT=18081
POSTGRES_PRIMARY_PORT=5432
POSTGRES_REPLICATION_USER=internal_services_replicator
POSTGRES_REPLICATION_PASSWORD=<replication-password>
POSTGRES_REPLICATION_SLOT=internal_services_vm2
POSTGRES_REPLICATION_NETWORK=<CIDR-that-includes-VM2>
MAX_REPLICATION_LAG_SECONDS=30
```

Create the state directory on both VMs:

```bash
mkdir -p /etc/internal-services /var/lib/internal-services-ha/staging
chmod 700 /etc/internal-services
```

## 4. Install The HA Units On Both VMs

```bash
/opt/orbina/internal_services/ops/ha/install-ha-systemd-units.sh
systemctl enable --now internal-services-ha-health.service
systemctl enable --now internal-services-ha-watchdog.service
```

Enable sync timers only on `VM1`:

```bash
systemctl enable --now internal-services-ha-sync-light.timer
systemctl enable --now internal-services-ha-sync-heavy.timer
```

Leave both timers disabled on `VM2`.

## 4A. Run Preflight Before Starting Anything

On `VM1`:

```bash
cd /opt/orbina/internal_services
ops/ha/preflight-check.sh --role active --check-peer
```

On `VM2`:

```bash
cd /opt/orbina/internal_services
ops/ha/preflight-check.sh --role passive
```

Do not continue until both checks pass.

## 5. Bootstrap `VM1` As The Active Node

On `VM1`:

```bash
cd /opt/orbina/internal_services
ops/ha/start-active.sh
ops/ha/postgres-primary-setup.sh
```

Validate:

```bash
curl -fsS http://127.0.0.1:18081/ready
curl -fsS http://127.0.0.1:18081/status
docker ps
```

Expected result:

- `/ready` returns `200`
- PostgreSQL is primary
- public services are running with the current working config unchanged

This step is enough to make one VM serve traffic by itself. The passive side is
not required for `VM1` to act as the working server.

## 6. Bootstrap `VM2` As The Passive Standby

On `VM2`:

```bash
cd /opt/orbina/internal_services
ops/ha/bootstrap-passive-postgres.sh
ops/ha/start-passive.sh
```

Validate:

```bash
curl -sS http://127.0.0.1:18081/status
docker ps
```

Expected result:

- `/ready` returns `503`
- `/status` shows `node_role=passive`
- PostgreSQL is running in standby mode
- public app services are stopped

## 7. Seed Passive Volumes From `VM1`

Run from `VM1` after the active stack is stable:

```bash
cd /opt/orbina/internal_services
ops/ha/sync-volumes-to-passive.sh all
```

This sync excludes `postgres_data` because PostgreSQL uses streaming replication.

The sync manifest is:

- `ops/ha/volume-sync-manifest.env`

Default coverage:

- `n8n_storage`
- `openwebui_data`
- `phoenix_trace_spool`
- `qdrant_data`
- `prometheus_data`
- `alertmanager_data`
- `loki_data`
- `grafana_data`
- `esdata01`
- `mysql_data`
- `minio_data`
- `redis_data`
- `mysql_data`
- `minio_data`
- `redis_data`

## 8. Configure The External Load Balancer

Use only the HA endpoint for active routing:

- `http://VM1:18081/ready`
- `http://VM2:18081/ready`

Expected LB behavior:

- active healthy node returns `200`
- passive healthy standby returns `503`
- unhealthy active node returns `503`

Do not use public app URLs for failover control.

## 9. Promotion Procedure

When `VM1` has failed and the standby is ready, log in to `VM2` and run:

```bash
cd /opt/orbina/internal_services
ops/ha/promote-passive.sh
```

What the script does:

- refuses promotion if the old primary still reports ready
- verifies local PostgreSQL is still a standby
- verifies standby lag and sync freshness
- stops the active-side sync timers if they exist locally
- promotes PostgreSQL with `pg_promote`
- flips the node role to `active`
- starts the public application stack

After promotion:

- move LB traffic to `VM2`
- verify `curl -fsS http://127.0.0.1:18081/ready`
- verify user-facing services

## 10. Failback Preparation

Once `VM1` is repaired and `VM2` is the confirmed primary, rebuild `VM1` as the new standby:

```bash
cd /opt/orbina/internal_services
ops/ha/prepare-failback.sh <VM2-IP>
```

This stops the old active stack on `VM1`, re-seeds PostgreSQL from `VM2`, and returns `VM1` to passive standby mode.

## 11. Validation Checklist

Run after initial install and after any promotion:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
docker compose -f shared-postgres/docker-compose.yml -f shared-postgres/docker-compose.primary-ha.yml ps
docker compose -f shared-postgres/docker-compose.yml -f shared-postgres/docker-compose.replica.yml ps
```

Check the HA state files when needed:

- `/var/lib/internal-services-ha/health.env`
- `/var/lib/internal-services-ha/last-sync-light`
- `/var/lib/internal-services-ha/last-sync-heavy`
- `/var/lib/internal-services-ha/promotion-ready`

## 12. Rollback

If the HA layer must be disabled:

1. Stop the HA timers and services.
2. Remove the LB health checks from `:18081/ready`.
3. Continue using the current working stack exactly as before on the chosen active node.

Commands:

```bash
systemctl disable --now internal-services-ha-sync-light.timer internal-services-ha-sync-heavy.timer
systemctl disable --now internal-services-ha-watchdog.service internal-services-ha-health.service
```

The base compose files remain unchanged, so disabling the HA layer does not require rewriting the current application configuration.

## 13. Single-VM Fallback

If the 2-VM flow fails at any point and you need one working VM immediately,
keep the load balancer pointed at `VM1` and run:

```bash
cd /opt/orbina/internal_services
ops/ha/start-single-node-fallback.sh
curl -fsS http://127.0.0.1:18081/ready
```

Behavior:

- `VM1` stays the active node
- public services continue to run from `VM1`
- local HA ready endpoint still works
- sync timers are disabled so passive sync failures do not interfere with the active node

This is the safe fallback if `VM2` bootstrap, replication, or volume sync is not ready yet.
