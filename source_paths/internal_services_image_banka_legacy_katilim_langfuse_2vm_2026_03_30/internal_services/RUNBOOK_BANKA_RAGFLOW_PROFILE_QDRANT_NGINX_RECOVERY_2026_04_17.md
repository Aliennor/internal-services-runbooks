# Banka RAGFlow Profile, Qdrant, And Nginx Recovery

Date: 2026-04-17

Use this when Banka active bootstrap reaches the RAGFlow start phase, then:

- `ragflow-cpu` is not visible in `podman ps`
- `nginx-proxy` stays `starting` or restarts
- `qdrant` is `unhealthy`, but Banka is not using qdrant
- `http://127.0.0.1:18081/ready` keeps waiting

This runbook is for the already-extracted Banka tree on `106`, `107`, or
dev `108`.

## 1) Root Cause

RAGFlow's application container is behind a Compose profile. Starting
`ragflow/docker/docker-compose.yml` without profiles can start infra containers
but skip `ragflow-cpu`.

The nginx proxy config has an upstream to `ragflow-cpu`. If `nginx-proxy`
starts before `ragflow-cpu` exists on the shared network, nginx can stay in a
starting/restart state. That blocks the HA gate because `:18081/ready` requires
core services plus nginx internal health.

Qdrant is not required for the current Banka runtime path, so it should not be
used as a health blocker.

## 2) Apply Immediate Recovery On The Active Node

Run as `root` on the affected VM:

```bash
set -euo pipefail

cd /opt/orbina/internal_services

grep -q '^ENABLE_QDRANT=' /etc/internal-services/ha.env \
  && sed -i 's/^ENABLE_QDRANT=.*/ENABLE_QDRANT=false/' /etc/internal-services/ha.env \
  || echo 'ENABLE_QDRANT=false' >> /etc/internal-services/ha.env

mkdir -p /var/lib/internal-services-ha
printf 'active\n' > /var/lib/internal-services-ha/role
```

Start RAGFlow with the required profiles:

```bash
cd /opt/orbina/internal_services/ragflow/docker

DOC_ENGINE="${DOC_ENGINE:-elasticsearch}"
DEVICE="${DEVICE:-cpu}"
export COMPOSE_PROFILES="${DOC_ENGINE},${DEVICE}"

podman compose \
  --profile "$DOC_ENGINE" \
  --profile "$DEVICE" \
  -f docker-compose.yml \
  up -d

podman compose \
  --profile "$DOC_ENGINE" \
  --profile "$DEVICE" \
  -f docker-compose.yml \
  ps
```

Restart nginx/OpenWebUI after RAGFlow exists:

```bash
cd /opt/orbina/internal_services/openweb-ui
podman compose -f docker-compose.yml up -d
```

## 3) Validate

```bash
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

podman exec nginx-proxy wget -qO- http://127.0.0.1:8081/health

curl -sS http://127.0.0.1:18081/status || true
curl -i http://127.0.0.1:18081/ready || true

curl -I http://127.0.0.1:8080/ || true
curl -I http://127.0.0.1:8100/ || true
```

Expected:

- `ragflow-cpu` or `docker-ragflow-cpu-1` is present.
- `nginx-proxy` is running and passes `127.0.0.1:8081/health`.
- `qdrant` may be unhealthy or absent; ignore it for this Banka path.
- `:18081/ready` returns `200` once the core stack is healthy.

## 4) If RAGFlow Still Does Not Start

Collect focused logs:

```bash
cd /opt/orbina/internal_services/ragflow/docker

podman compose \
  --profile "${DOC_ENGINE:-elasticsearch}" \
  --profile "${DEVICE:-cpu}" \
  -f docker-compose.yml \
  logs --tail=160

podman logs --tail=160 docker-ragflow-cpu-1 || true
podman logs --tail=160 ragflow-ragflow-cpu-1 || true
```

Common causes:

- `mysql` is still warming up; `ragflow-cpu` depends on MySQL health.
- The external `internal_services_network` is missing.
- The RAGFlow image was not pulled on the restricted host.

Check the network and image:

```bash
podman network inspect internal_services_network >/dev/null \
  || podman network create internal_services_network

podman image exists docker.io/aliennor/ragflow:v0.23.0 \
  || podman pull --tls-verify=false docker.io/aliennor/ragflow:v0.23.0
```

## 5) Persistent Fix For Future Bootstraps

The corrected Banka HA bootstrap source now does four things:

- defaults `ENABLE_QDRANT=false`
- creates `internal_services_network` before RAGFlow/OpenWebUI compose operations
- starts RAGFlow with `--profile "${DOC_ENGINE:-elasticsearch}" --profile "${DEVICE:-cpu}"`
- waits for `ragflow-cpu` and RAGFlow infra before starting `openweb-ui`/`nginx`

Use installer `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r29`
or newer for first installs.

## 6) Rollback

This recovery does not delete data. To roll back the runtime changes:

```bash
cd /opt/orbina/internal_services/openweb-ui
podman compose -f docker-compose.yml down

cd /opt/orbina/internal_services/ragflow/docker
podman compose \
  --profile "${DOC_ENGINE:-elasticsearch}" \
  --profile "${DEVICE:-cpu}" \
  -f docker-compose.yml \
  down

grep -q '^ENABLE_QDRANT=' /etc/internal-services/ha.env \
  && sed -i 's/^ENABLE_QDRANT=.*/ENABLE_QDRANT=true/' /etc/internal-services/ha.env \
  || true
```

Only re-enable qdrant if an operator explicitly wants qdrant in the Banka
runtime.
