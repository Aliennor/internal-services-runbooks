# Banka Reset Non-RAGFlow App State Patch Runbook

Date: 2026-04-15

Patch image:

- `docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3`

Use this runbook as the single source for this patch.

## What This Patch Does

This patch installs:

```text
/opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
/opt/orbina/internal_services/RUNBOOK_BANKA_RESET_NON_RAGFLOW_APP_STATE_DEV_AND_PROD_2026_04_15.md
```

It can wipe and recreate non-RAGFlow app state:

- shared Postgres data for LiteLLM, Langfuse, and n8n
- Langfuse ClickHouse and MinIO volumes
- n8n local volume
- OpenWebUI local volume
- Qdrant local volume
- observability volumes

It intentionally does not remove RAGFlow containers or any volume whose name contains `ragflow`.

The reset is destructive for non-RAGFlow app data. It does not take full volume backups.

## 1) If You Are Currently Stuck From r1/r2

If the terminal is stuck at:

```text
Starting shared Postgres first so init-databases.sh recreates app databases/users...
```

Press:

```text
Ctrl+C
```

Then run this on `10.11.115.108`:

```bash
sudo su -

podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
podman logs --tail=120 shared_postgres || true
```

If `shared_postgres` is running and logs say `database system is ready to accept connections`, do not rerun the destructive wipe. Pull/extract r3 and start stacks directly:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3 \
  /output

for d in shared-postgres langfuse litellm n8n openweb-ui qdrant observability; do
  if [ -d "/opt/orbina/internal_services/$d" ]; then
    echo "Starting $d"
    cd "/opt/orbina/internal_services/$d"
    CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
  fi
done
```

Then go to section 4.

## 2) Fresh Dev 108 Reset

Run on `10.11.115.108`:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3 \
  /output
```

Dry-run first:

```bash
sudo su -

DRY_RUN=true CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
```

Review the printed volume list. It must not include any volume with `ragflow` in the name.

Execute the reset without automatic startup:

```bash
sudo su -

RESTART_AFTER_RESET=false CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
```

Start all non-RAGFlow stacks directly with `podman compose`:

```bash
sudo su -

for d in shared-postgres langfuse litellm n8n openweb-ui qdrant observability; do
  if [ -d "/opt/orbina/internal_services/$d" ]; then
    echo "Starting $d"
    cd "/opt/orbina/internal_services/$d"
    CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
  fi
done
```

Then go to section 4.

## 3) Prod 106/107 Reset

Run the destructive reset on active `10.11.115.106` first. Do not run this against passive `10.11.115.107` while it is a read-only Postgres replica.

Run on `10.11.115.106`:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3 \
  /output
```

Dry-run on `106`:

```bash
sudo su -

DRY_RUN=true CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
```

Execute on `106` without automatic startup:

```bash
sudo su -

RESTART_AFTER_RESET=false CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
```

Start active stacks on `106`:

```bash
sudo su -

for d in shared-postgres langfuse litellm n8n openweb-ui qdrant observability; do
  if [ -d "/opt/orbina/internal_services/$d" ]; then
    echo "Starting $d"
    cd "/opt/orbina/internal_services/$d"
    CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
  fi
done
```

Validate `106` with section 4. After `106` is healthy, refresh passive `107` using the normal active/passive sync/bootstrap runbook.

If you explicitly need to wipe local non-RAGFlow volumes on passive `107`, run this on `107` only after confirming it is safe:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-non-ragflow-db-reset:2026-04-15-r3 \
  /output

DRY_RUN=true CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh

RESTART_AFTER_RESET=false CONFIRM_WIPE_NON_RAGFLOW=YES \
  /opt/orbina/internal_services/ops/repair/banka-reset-non-ragflow-app-state.sh
```

Then run the normal passive bootstrap/sync procedure for `107`.

## 4) Validation Commands

Run on the machine you patched:

```bash
sudo su -

podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl --failed --no-pager || true

podman logs --tail=100 shared_postgres || true
podman logs --tail=100 langfuse-web || true
podman logs --tail=100 langfuse-worker || true
podman logs --tail=100 litellm || true
podman logs --tail=100 n8n || true
podman logs --tail=100 openwebui || true
podman logs --tail=100 qdrant || true
podman logs --tail=100 observability-grafana || true
```

Check direct local ports:

```bash
sudo su -

curl -I http://127.0.0.1:3000/ || true
curl -I http://127.0.0.1:4000/ || true
curl -I http://127.0.0.1:5678/ || true
curl -I http://127.0.0.1:8080/ || true
curl -I http://127.0.0.1:8100/ || true
```

Expected common UI/API ports:

```text
Langfuse:  http://<server-ip>:3000/
LiteLLM:   http://<server-ip>:4000/
n8n:       http://<server-ip>:5678/
OpenWebUI: http://<server-ip>:8080/
RAGFlow:   http://<server-ip>:8100/
```

RAGFlow should remain available on dev:

```text
http://10.11.115.108:8100/
```

Check RAGFlow separately if needed:

```bash
sudo su -

podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -i ragflow || true
grep -E '^(RAGFLOW_PUBLIC_HTTP_PORT|RAGFLOW_PUBLIC_HTTPS_PORT|RAGFLOW_API_PORT|RAGFLOW_ADMIN_PORT)=' \
  /opt/orbina/internal_services/ragflow/docker/.env || true
```

## 5) If A Stack Does Not Start

Run the failing stack manually and inspect logs:

```bash
sudo su -

cd /opt/orbina/internal_services/shared-postgres
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 shared_postgres || true
```

For Langfuse:

```bash
sudo su -

cd /opt/orbina/internal_services/langfuse
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 langfuse-web || true
podman logs --tail=160 langfuse-worker || true
podman logs --tail=160 langfuse-redis || true
podman logs --tail=160 langfuse-clickhouse || true
```

For LiteLLM:

```bash
sudo su -

cd /opt/orbina/internal_services/litellm
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 litellm || true
```

For n8n:

```bash
sudo su -

cd /opt/orbina/internal_services/n8n
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 n8n || true
```

For OpenWebUI and nginx:

```bash
sudo su -

cd /opt/orbina/internal_services/openweb-ui
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 openwebui || true
podman logs --tail=160 nginx-proxy || true
```

For Qdrant:

```bash
sudo su -

cd /opt/orbina/internal_services/qdrant
CONTAINER_ENGINE=podman timeout 180 podman compose up -d || true
podman logs --tail=160 qdrant || true
```

## 6) Backup And Rollback Notes

The reset script writes logs and copied `.env` files under:

```text
/opt/orbina/backups/banka_non_ragflow_app_state_reset_<timestamp>/
```

It does not take full volume backups. If you need rollback of deleted non-RAGFlow app data, restore from external VM/storage backups.

RAGFlow volumes are excluded by design.
