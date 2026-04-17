# Banka Dev108 Mercek 502 Compose Path And Proxy Check

Use this when:

- `mercek-yzyonetim-dev.ziraat.bank` returns `502`
- previous checks mixed proxy behavior and direct checks
- `podman compose -f /opt/internal-services/docker-compose.yml ...` fails with missing file

Target server: `10.11.115.108`

## Step 1: Clean Diagnostic (Proxy-Safe)

Run on `10.11.115.108`:

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-mercek-502-path-proxy-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

echo "== working dir and proxy env =="
pwd || true
env | grep -Ei '^(http|https|no)_proxy=' || true

echo "== langfuse-web status and ports =="
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'langfuse-web|nginx-proxy|NAMES' || true
podman port langfuse-web || true
ss -ltnp | grep ':3000' || true

echo "== host direct with proxy disabled in command =="
http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' \
  curl --noproxy '*' --max-time 12 -svI http://127.0.0.1:3000/ || true

echo "== inside langfuse-web loopback without proxy =="
podman exec langfuse-web sh -lc \
  'http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY=* wget -Y off -S -O- http://127.0.0.1:3000/ >/dev/null' || true

echo "== nginx container to host.containers.internal:3000 without proxy =="
podman exec nginx-proxy sh -lc \
  'http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY=* wget -Y off -S -O- http://host.containers.internal:3000/ >/dev/null' || true

echo "== mercek via local nginx =="
curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true
```

## Step 2: Find Real Compose File Path

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-compose-path-discovery-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

for d in \
  /opt/internal-services \
  /opt/internal_services \
  /srv/internal-services \
  /srv/internal_services \
  /home/*/internal-services \
  /root/internal-services
do
  ls "$d" 2>/dev/null || true
  ls "$d"/docker-compose*.yml 2>/dev/null || true
  ls "$d"/compose*.yml 2>/dev/null || true
done
```

## Step 3: Recreate Langfuse-Web Using The Actual Compose File

After Step 2, replace `ACTUAL_COMPOSE_FILE`:

```bash
ACTUAL_COMPOSE_FILE="/absolute/path/to/docker-compose.yml"
podman compose -f "$ACTUAL_COMPOSE_FILE" up -d --force-recreate langfuse-web
sleep 8

http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' \
  curl --noproxy '*' --max-time 12 -I http://127.0.0.1:3000/ || true

curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true
```

## Expected Interpretation

- If host `127.0.0.1:3000` is `200/302` and mercek becomes `200`, issue is resolved.
- If host `3000` is still refused but container says `Up`, inspect `podman logs --tail=200 langfuse-web` and container startup command.
