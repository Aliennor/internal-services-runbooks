# Banka Dev108 Mercek Langfuse 3000 Recovery Check

Use this when `mercek-yzyonetim-dev.ziraat.bank` returns `502` while other
hostnames still return `200`.

Target:

- server: `10.11.115.108`
- hostname: `https://mercek-yzyonetim-dev.ziraat.bank/`
- expected backend path: `nginx -> host.containers.internal:3000 -> langfuse-web`

## Step 1: Diagnose Before Recreate

Run on `10.11.115.108`:

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-mercek-fix-check-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

echo "== 1) langfuse container icinden 3000 dinliyor mu =="
podman exec langfuse-web sh -lc 'wget -S -O- http://127.0.0.1:3000/ >/dev/null' || true

echo "== 2) hostta 3000 publish var mi =="
podman port langfuse-web || true
ss -ltnp | grep ':3000' || true

echo "== 3) nginx containerdan proxy'siz host.containers.internal:3000 =="
podman exec nginx-proxy sh -lc 'wget --no-proxy -S -O- http://host.containers.internal:3000/ >/dev/null' || true

echo "== 4) mercek durumu =="
curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true
```

## Step 2: Fast Recovery (Only If 3000 Is Unreachable)

```bash
podman compose -f /opt/internal-services/docker-compose.yml up -d --force-recreate langfuse-web
sleep 8
curl --noproxy '*' --max-time 12 -I http://127.0.0.1:3000/ || true
curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true
```

## Send Back

Share:

- generated log path from Step 1 (`/tmp/banka-dev108-mercek-fix-check-*.log`)
- the last two `curl` results from Step 2
