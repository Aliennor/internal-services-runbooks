# Banka Dev108 Client Timeout And Langfuse 3000 Check

Current incident:

- From Windows terminal server `10.2.101.18`, the browser times out for all UI
  hostnames (`manavgat`, `mercek`, `aykal`, `mecra`, `zfgasistan`).
- On server `10.11.115.108`, `mercek-yzyonetim-dev.ziraat.bank` returns
  `HTTP/2 502` while other hostnames are `200`.
- Container `langfuse-web` is listed as `Up` with `0.0.0.0:3000->3000/tcp`,
  but both host and in-container `curl 127.0.0.1:3000` return `Connection refused`.
- `conmon` holds port `3000` on the host, but the Next.js process inside the
  container has not actually bound on `3000`.
- The compose file is not at `/opt/internal-services/docker-compose.yml`.

## Step 1: Classify Client Timeout From 10.2.101.18

Run on Windows terminal server `10.2.101.18`:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-client-timeout-classify-$ts.txt"
Start-Transcript -Path $out

ipconfig

$hosts = @(
  "manavgat-yzyonetim-dev.ziraat.bank",
  "mercek-yzyonetim-dev.ziraat.bank",
  "aykal-yzyonetim-dev.ziraat.bank",
  "mecra-yzyonetim-dev.ziraat.bank",
  "zfgasistan-yzyonetim-dev.ziraat.bank"
)

foreach ($h in $hosts) {
  Write-Host "== $h dns =="
  Resolve-DnsName $h
  Write-Host "== $h tcp 443 =="
  Test-NetConnection $h -Port 443
  Write-Host "== $h https HEAD =="
  curl.exe --max-time 15 -vkI "https://$h/"
}

foreach ($p in @(80,443,4000,3000,5678,8100)) {
  Write-Host "== 10.11.115.108 tcp $p =="
  Test-NetConnection 10.11.115.108 -Port $p
}

Stop-Transcript
Write-Host "out=$out"
```

Interpretation:

- If `Test-NetConnection 443` fails for all hosts: network ACL / firewall /
  TLS inspection between `10.2.101.18` and `10.11.115.108`, not the stack.
- If DNS resolves but TCP 443 fails: external path issue (proxy, firewall,
  VPN routing).
- If browser was working earlier today and now all hosts time out from the
  client: investigate recent proxy/firewall change rather than application
  services.

## Step 2: Confirm Server-Local Nginx Path Still Works

Run on `10.11.115.108`:

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-server-local-all-hosts-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

for host in \
  manavgat-yzyonetim-dev.ziraat.bank \
  aykal-yzyonetim-dev.ziraat.bank \
  mecra-yzyonetim-dev.ziraat.bank \
  zfgasistan-yzyonetim-dev.ziraat.bank \
  mercek-yzyonetim-dev.ziraat.bank
do
  echo "== $host =="
  curl --noproxy '*' --max-time 10 -kI \
    --resolve "${host}:443:127.0.0.1" "https://${host}/" || true
done
```

If every host is still `200` except `mercek`, the client timeout is purely
network/path (Step 1), and the application stack is unrelated.

## Step 3: Fix Langfuse-Web Not Actually Listening

Run on `10.11.115.108`:

```bash
set -u
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-langfuse-web-listen-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

echo "== container state =="
podman ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'langfuse|nginx-proxy|NAMES' || true
podman inspect langfuse-web --format '{{.State.Status}} started={{.State.StartedAt}} restarts={{.RestartCount}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'

echo "== compose labels =="
for c in langfuse-web langfuse-worker langfuse-redis langfuse-clickhouse langfuse-minio nginx-proxy litellm; do
  echo "-- $c --"
  podman inspect "$c" --format \
    '{{index .Config.Labels "com.docker.compose.project"}} | {{index .Config.Labels "com.docker.compose.project.working_dir"}} | {{index .Config.Labels "com.docker.compose.project.config_files"}}' \
    2>/dev/null || true
done

echo "== compose file discovery =="
find /root /home /opt /srv -maxdepth 5 -type f \
  \( -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' \
     -o -name 'compose*.yml' -o -name 'compose*.yaml' \) 2>/dev/null | head -n 40

echo "== what is actually listening inside container =="
podman exec langfuse-web sh -lc \
  'command -v ss >/dev/null 2>&1 && ss -ltnp || netstat -ltnp 2>/dev/null || cat /proc/net/tcp | awk "NR==1 || \$4==\"0A\""' || true
podman exec langfuse-web sh -lc 'ps -ef 2>/dev/null || ps aux 2>/dev/null' || true

echo "== last 200 log lines =="
podman logs --tail=200 langfuse-web 2>&1 | tail -n 200
```

Once you have the compose project directory (from labels or `find`):

```bash
ACTUAL_WORKING_DIR="/real/compose/project/dir"
ACTUAL_COMPOSE_FILE="/real/compose/project/dir/docker-compose.yml"

cd "$ACTUAL_WORKING_DIR"
podman compose -f "$ACTUAL_COMPOSE_FILE" up -d --force-recreate langfuse-web
sleep 10

http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' \
  curl --noproxy '*' --max-time 12 -I http://127.0.0.1:3000/ || true

curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true

podman logs --tail=80 langfuse-web 2>&1 | tail -n 80
```

## Send Back

- `/tmp/banka-dev108-client-timeout-classify-*.txt` from Windows
- `/tmp/banka-dev108-server-local-all-hosts-*.log` from server
- `/tmp/banka-dev108-langfuse-web-listen-*.log` from server
- the two recreate `curl` results plus last log tail
