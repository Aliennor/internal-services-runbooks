# Banka Dev108 r33 Post-Install Triage

Date: 2026-04-17

Use this on Banka dev `10.11.115.108` after the expected current install line:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r33`
- dev encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`

This runbook is intentionally server-local. Do not run these checks from a
workstation that cannot reach the company server.

## 1) Capture A Triage Log

Run as `root` on `10.11.115.108`:

```bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
TRIAGE_LOG="/tmp/banka-dev108-r33-triage-${TS}.log"
exec > >(tee -a "$TRIAGE_LOG") 2>&1

echo "triage_log=$TRIAGE_LOG"
echo "timestamp=$(date -Is)"
hostname -f || hostname
id
```

## 2) Confirm Installed Tree And Config State

```bash
cd /opt/orbina/internal_services

echo "== current env =="
grep -E '^(NODE_ROLE|PRIMARY_HOST|PASSIVE_SSH_HOST|PUBLIC_URL_SCHEME|DIRECT_PUBLIC_BASE_SCHEME|DIRECT_PUBLIC_BASE_HOST|OPENWEBUI_NGINX_CONFIG_PATH|LITELLM_BROWSER_URL|LANGFUSE_BROWSER_URL|ENABLE_QDRANT|ENABLE_RAGFLOW_STACK|RAGFLOW_DOC_ENGINE|RAGFLOW_DEVICE|STRICT_INSTALL_HEALTH_CHECKS|RESET_NON_RAGFLOW_ON_FIRST_ACTIVE_BOOTSTRAP|RESET_NON_RAGFLOW_ON_ACTIVE_BOOTSTRAP|PRE_CLEAN_INSTALL_ATTEMPT)=' \
  /etc/internal-services/ha.env || true

echo "== app env urls =="
grep -E '^(NGINX_CONFIG_PATH|OPENWEBUI_DIRECT_PORT|DIRECT_BIND_ADDRESS)=' openweb-ui/.env || true
grep -E '^(PROXY_BASE_URL|LANGFUSE_BASE_URL|LANGFUSE_HOST|LITELLM_DIRECT_PORT|DIRECT_BIND_ADDRESS)=' litellm/.env || true
grep -E '^(NEXTAUTH_URL|CLICKHOUSE_URL|CLICKHOUSE_MIGRATION_URL|LANGFUSE_DIRECT_PORT|DIRECT_BIND_ADDRESS)=' langfuse/.env || true

echo "== current image references in extracted bundle =="
grep -R "banka-langfuse-2026-04-17-r33\|banka-langfuse-dev108-2026-04-17-r7\|docker.io/aliennor/nginx:1.27-alpine" \
  RUNBOOK_BANKA*.md ops/install/katilim openweb-ui/docker-compose.yml 2>/dev/null || true
```

Expected:

- `PUBLIC_URL_SCHEME=https`
- `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf`
- `LITELLM_BROWSER_URL=https://manavgat-yzyonetim-dev.ziraat.bank`
- `LANGFUSE_BROWSER_URL=https://mercek-yzyonetim-dev.ziraat.bank`
- `ENABLE_QDRANT=false`

## 3) Check Containers And Local Ports

```bash
echo "== containers =="
podman ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

echo "== direct local ports =="
for port in 8080 4000 3000 5678 8100 18081; do
  printf 'port %s: ' "$port"
  curl --noproxy '*' --max-time 5 -k -sS -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:${port}/" || true
done

echo "== health endpoints =="
curl --noproxy '*' --max-time 5 -fsS http://127.0.0.1:18081/status || true
curl --noproxy '*' --max-time 5 -i http://127.0.0.1:18081/ready || true
curl --noproxy '*' --max-time 5 -i http://127.0.0.1:4000/health || true
curl --noproxy '*' --max-time 5 -I http://127.0.0.1:3000/ || true
curl --noproxy '*' --max-time 5 -I http://127.0.0.1:8100/ || true
```

Interpretation:

- If `4000` works but browser DNS for LiteLLM times out, suspect DNS, firewall,
  or nginx routing rather than LiteLLM itself.
- If `3000` fails locally, nginx cannot make Langfuse work; inspect Langfuse and
  ClickHouse logs before touching nginx.
- If `18081/ready` is true while browser DNS times out, the app stack is likely
  local-ready and the remaining issue is public routing.

## 4) Verify Active Nginx Config

```bash
echo "== nginx image and config =="
podman image inspect docker.io/aliennor/nginx:1.27-alpine --format '{{.Architecture}} {{.Os}} {{.Id}}' || true
podman exec nginx-proxy nginx -t || true
podman exec nginx-proxy sh -c "grep -n 'proxy_pass\\|server_name\\|listen' /etc/nginx/nginx.conf" || true

echo "== stale bridge upstream check =="
podman exec nginx-proxy sh -c "grep -n '10\\.89\\|langfuse-web:3000\\|litellm:4000\\|openwebui:8080\\|ragflow-cpu' /etc/nginx/nginx.conf" || true

echo "== expected host upstream check =="
podman exec nginx-proxy sh -c "grep -n 'host.containers.internal:8080\\|host.containers.internal:4000\\|host.containers.internal:3000\\|host.containers.internal:5678\\|host.containers.internal:8100' /etc/nginx/nginx.conf" || true

echo "== nginx internal health and upstream reachability =="
podman exec nginx-proxy env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY \
  NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  wget -S -qO- http://127.0.0.1:8081/health || true
podman exec nginx-proxy getent hosts host.containers.internal || true
podman exec nginx-proxy wget -S -qO- http://host.containers.internal:4000/ >/dev/null || true
podman exec nginx-proxy wget -S -qO- http://host.containers.internal:3000/ >/dev/null || true
```

Expected after `r33`:

- no `10.89.x.x` upstreams in `/etc/nginx/nginx.conf`
- no app upstreams like `langfuse-web:3000`
- `proxy_pass http://host.containers.internal:<direct-port>` for the app routes

If nginx still contains stale bridge upstreams, go to section 8.

## 5) Test HTTPS Routes Locally On The Server

```bash
for host in \
  zfgasistan-yzyonetim-dev.ziraat.bank \
  manavgat-yzyonetim-dev.ziraat.bank \
  aykal-yzyonetim-dev.ziraat.bank \
  mercek-yzyonetim-dev.ziraat.bank \
  mecra-yzyonetim-dev.ziraat.bank
do
  echo "== $host =="
  curl --noproxy '*' --max-time 8 -kI --resolve "${host}:443:127.0.0.1" "https://${host}/" || true
done
```

Interpretation:

- If these work locally but clients time out, check DNS, routing, firewall, and
  load balancer path outside the server.
- If only `mercek` fails and `127.0.0.1:3000` also fails, inspect Langfuse.
- If only nginx HTTPS fails but direct ports work, inspect nginx config, TLS
  mounts, and `nginx-proxy` logs.

## 6) Collect Focused Logs

```bash
echo "== nginx logs =="
podman logs --tail=160 nginx-proxy || true

echo "== app logs =="
podman logs --tail=120 openwebui || true
podman logs --tail=120 litellm || true
podman logs --tail=160 langfuse-web || true
podman logs --tail=160 langfuse-worker || true
podman logs --tail=120 langfuse-clickhouse || true
podman logs --tail=120 docker-ragflow-cpu-1 || podman logs --tail=120 ragflow-cpu || true

echo "== service status =="
systemctl --failed --no-pager || true
journalctl -u internal-services-ha-health.service -n 120 --no-pager || true
journalctl -u internal-services-ha-watchdog.service -n 120 --no-pager || true
```

Langfuse may log background migration warnings while ClickHouse tables are still
being created. Treat that as a Langfuse-specific readiness issue only if
`127.0.0.1:3000` does not answer or Langfuse keeps restarting.

## 7) ClickHouse Table Check For Langfuse

Run this only if Langfuse direct port `3000` fails or Langfuse logs repeatedly
say ClickHouse tables are missing:

```bash
podman exec langfuse-clickhouse clickhouse-client \
  --user "${CLICKHOUSE_USER:-clickhouse}" \
  --password "$(grep '^CLICKHOUSE_PASSWORD=' /opt/orbina/internal_services/langfuse/.env | cut -d= -f2-)" \
  --query "SHOW DATABASES" || true

podman exec langfuse-clickhouse clickhouse-client \
  --user "${CLICKHOUSE_USER:-clickhouse}" \
  --password "$(grep '^CLICKHOUSE_PASSWORD=' /opt/orbina/internal_services/langfuse/.env | cut -d= -f2-)" \
  --query "SHOW TABLES FROM langfuse" || true
```

Expected Langfuse v3 runtime eventually needs tables such as traces,
observations, scores, event_log, and blob_storage_file_log. If the database is
empty while `langfuse-web` and `langfuse-worker` are stable, restart just the
Langfuse compose stack and recheck logs:

```bash
cd /opt/orbina/internal_services/langfuse
podman compose -f docker-compose.yaml up -d
podman logs --tail=160 langfuse-web || true
podman logs --tail=160 langfuse-worker || true
```

## 8) Recovery Only If Nginx Still Uses Stale Upstreams

Use this only when section 4 shows `10.89.x.x`, `langfuse-web:3000`,
`litellm:4000`, or other stale upstreams inside the running nginx config.

```bash
set -euo pipefail

cd /opt/orbina/internal_services

ops/install/katilim/render-openwebui-nginx.sh \
  --env-file /etc/internal-services/ha.env \
  --out-dir /opt/orbina/internal_services/openweb-ui

grep -n 'host.containers.internal' /opt/orbina/internal_services/openweb-ui/nginx.generated.conf
! grep -n '10\.89\|langfuse-web:3000\|litellm:4000\|openwebui:8080\|ragflow-cpu' \
  /opt/orbina/internal_services/openweb-ui/nginx.generated.conf

cd /opt/orbina/internal_services/openweb-ui
podman compose -f docker-compose.yml up -d --force-recreate nginx
podman exec nginx-proxy nginx -t
podman exec nginx-proxy env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY \
  NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  wget -qO- http://127.0.0.1:8081/health
```

Then rerun sections 4 and 5.

## 9) Send Back These Lines

If this still fails, send back:

- the path printed as `triage_log=...`
- section 3 direct local port results
- section 4 stale bridge upstream check
- section 5 HTTPS route results
- last 80 lines of `nginx-proxy`, `langfuse-web`, and `langfuse-worker` logs
