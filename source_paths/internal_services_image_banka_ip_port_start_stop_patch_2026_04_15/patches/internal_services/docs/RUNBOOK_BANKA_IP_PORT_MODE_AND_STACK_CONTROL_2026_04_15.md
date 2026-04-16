# Banka IP/Port Mode And Stack Control Patch Runbook

Date: 2026-04-15

Patch image:

- `docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1`

Use this when DNS names and certificates are not ready yet and the services must work by server IP and direct ports.

## 1) What This Fixes

This patch:

- changes public app URLs away from `*.yzyonetim...` DNS names
- sets LiteLLM admin/public URL to `http://<server-ip>:4000`
- sets Langfuse `NEXTAUTH_URL` to `http://<server-ip>:3000`
- sets n8n editor/webhook URLs to `http://<server-ip>:5678`
- sets OpenWebUI direct URL to `http://<server-ip>:8080`
- installs an IP-only nginx config with `server_name _`
- adds a stack-control script that starts/stops RAGFlow as well as the other stacks

This patch does not wipe volumes.

## 2) Pull And Extract On Dev 108

Run on `10.11.115.108`:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1 \
  /output
```

## 3) Apply IP/Port Mode On Dev 108

Run on `10.11.115.108`:

```bash
sudo su -

SERVER_IP=10.11.115.108 \
  /opt/orbina/internal_services/ops/repair/banka-apply-ip-port-mode.sh
```

Restart all stacks, including RAGFlow:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh restart
```

If a stack hangs, stop the loop with `Ctrl+C`, then run section 7 for that stack.

## 4) Validate Dev 108

Run on `10.11.115.108`:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh status
/opt/orbina/internal_services/ops/repair/banka-stack-control.sh validate
```

Check logs:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh logs
```

Expected direct URLs:

```text
OpenWebUI:   http://10.11.115.108:8080/
LiteLLM:     http://10.11.115.108:4000/
Langfuse:    http://10.11.115.108:3000/
n8n:         http://10.11.115.108:5678/
Qdrant:      http://10.11.115.108:6333/dashboard
RAGFlow UI:  http://10.11.115.108:8100/
RAGFlow API: http://10.11.115.108:5100/
```

If you are browsing from a different machine, do not use `localhost`. Use `10.11.115.108`.

## 5) Prod 106/107

Run on active `10.11.115.106`:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1 \
  /output

SERVER_IP=10.11.115.106 \
  /opt/orbina/internal_services/ops/repair/banka-apply-ip-port-mode.sh

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh restart
```

Expected direct prod-active URLs before LB/DNS:

```text
OpenWebUI:   http://10.11.115.106:8080/
LiteLLM:     http://10.11.115.106:4000/
Langfuse:    http://10.11.115.106:3000/
n8n:         http://10.11.115.106:5678/
Qdrant:      http://10.11.115.106:6333/dashboard
RAGFlow UI:  http://10.11.115.106:8100/
RAGFlow API: http://10.11.115.106:5100/
```

Run on passive `10.11.115.107` only if you are intentionally preparing or testing that node directly:

```bash
sudo su -

podman pull --tls-verify=false docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1
podman run --rm -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-banka-ip-port-mode:2026-04-15-r1 \
  /output

SERVER_IP=10.11.115.107 \
  /opt/orbina/internal_services/ops/repair/banka-apply-ip-port-mode.sh
```

Do not start a passive Postgres replica as an independent primary unless you are intentionally doing failover/fallback testing.

## 6) Start And Stop Commands

Start all stacks:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh start
```

Stop all stacks:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh stop
```

Restart all stacks:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh restart
```

Status:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh status
```

Validate URLs:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh validate
```

## 7) If RAGFlow Is Not Running

Run RAGFlow manually:

```bash
sudo su -

cd /opt/orbina/internal_services/ragflow/docker
set -a
. ./.env
set +a
DOC_ENGINE="${DOC_ENGINE:-elasticsearch}"
DEVICE="${DEVICE:-cpu}"
export COMPOSE_PROFILES="${DOC_ENGINE},${DEVICE}"

CONTAINER_ENGINE=podman timeout 300 podman compose \
  --profile "$DOC_ENGINE" \
  --profile "$DEVICE" \
  up -d
```

Check RAGFlow containers:

```bash
sudo su -

podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -Ei 'ragflow|mysql|minio|redis|elastic|opensearch|infinity|oceanbase' || true
```

Check logs:

```bash
sudo su -

podman logs --tail=160 ragflow-ragflow-cpu-1 || true
podman logs --tail=160 docker-ragflow-cpu-1 || true
podman logs --tail=160 ragflow-mysql-1 || true
podman logs --tail=160 docker-mysql-1 || true
podman logs --tail=160 ragflow-minio-1 || true
podman logs --tail=160 docker-minio-1 || true
podman logs --tail=160 ragflow-redis-1 || true
podman logs --tail=160 docker-redis-1 || true
podman logs --tail=160 ragflow-es01-1 || true
podman logs --tail=160 docker-es01-1 || true
```

Try the UI:

```bash
curl -I http://127.0.0.1:8100/ || true
curl -I http://10.11.115.108:8100/ || true
```

## 8) If Langfuse Is Up But Browser Cannot Access It

If you are on your workstation browser, `localhost:3000` means your workstation, not the server. Use:

```text
http://10.11.115.108:3000/
```

If you are on the server itself, test:

```bash
sudo su -

curl -I http://127.0.0.1:3000/ || true
podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -i langfuse || true
podman logs --tail=160 langfuse-web || true
```

## 9) Rollback

The IP/port patch backs up changed files under:

```text
/opt/orbina/backups/banka_ip_port_mode_<timestamp>/
```

To restore a file, copy it back from that backup directory. Example:

```bash
sudo su -

cp /opt/orbina/backups/banka_ip_port_mode_<timestamp>/opt/orbina/internal_services/litellm/.env \
  /opt/orbina/internal_services/litellm/.env
```

Then restart:

```bash
sudo su -

/opt/orbina/internal_services/ops/repair/banka-stack-control.sh restart
```
