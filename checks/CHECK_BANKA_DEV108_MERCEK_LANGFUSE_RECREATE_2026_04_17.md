# Banka Dev108 Mercek Langfuse-Web Recreate

Current facts collected on `10.11.115.108`:

- nginx serves `manavgat`, `aykal`, `mecra`, `zfgasistan` as `HTTP/2 200`.
- nginx serves `mercek-yzyonetim-dev.ziraat.bank` as `HTTP/2 502`.
- `langfuse-web` container is `Up`, Next.js is actually running and listening
  inside the container on the container IP `10.89.0.16:3000`, not on
  `127.0.0.1:3000`.
- host `127.0.0.1:3000` is not reachable, so nginx `proxy_pass` through
  `host.containers.internal:3000` fails.
- From Windows `10.2.101.18`, TCP 443 succeeds and DNS resolves for all five
  UI hostnames. Browser-level `ERR_TIMED_OUT` mostly maps to the mercek `502`
  path; the other four hostnames return `200` on `HEAD /`.

Confirmed compose project path:

- `/opt/orbina/internal_services/langfuse/docker-compose.yaml`

## Step 1: Force-Recreate Langfuse-Web
Run on `10.11.115.108` as root:

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-mercek-langfuse-recreate-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

cd /opt/orbina/internal_services/langfuse
podman compose -f docker-compose.yaml ps || true

podman compose -f docker-compose.yaml up -d --force-recreate langfuse-web
sleep 12

podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'langfuse|nginx-proxy|NAMES' || true

http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' \
  curl --noproxy '*' --max-time 12 -I http://127.0.0.1:3000/ || true

curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true

podman logs --tail=80 langfuse-web 2>&1 | tail -n 80
```

## Step 2: If Step 1 Does Not Fix Mercek

Langfuse-web may be binding to its compose-network container IP only and the
host port publish alone is not enough when nginx-proxy lives in another compose
project network.

Check which podman networks each container is on:

```bash
podman inspect langfuse-web --format 'networks={{json .NetworkSettings.Networks}}'
podman inspect nginx-proxy --format 'networks={{json .NetworkSettings.Networks}}'
```

If they do not share a network, attach nginx-proxy to the langfuse network:

```bash
LANGFUSE_NET=$(podman inspect langfuse-web --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "langfuse_net=$LANGFUSE_NET"

podman network connect "$LANGFUSE_NET" nginx-proxy || true

podman exec nginx-proxy sh -lc \
  'http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY=* wget -Y off -S -O- http://langfuse-web:3000/ >/dev/null' || true

curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true
```

Do NOT change the nginx upstream target in this step; only attach the network
so `host.containers.internal:3000` still resolves. A persistent fix that
rewrites nginx config should be a separate runbook after validation.

## Send Back

- `/tmp/banka-dev108-mercek-langfuse-recreate-*.log`
- last curl result for `https://mercek-yzyonetim-dev.ziraat.bank/`
- langfuse-web and nginx-proxy network output if Step 2 was needed
