# Banka Dev108 Browser Connectivity Check

Use this when a URL works from the server with `curl --resolve` but does not
open from a browser or another client machine.

Target:

- server: `10.11.115.108`
- browser test client: Windows terminal server `10.2.101.18`
- LiteLLM browser URL: `https://manavgat-yzyonetim-dev.ziraat.bank`
- direct fallback: `http://10.11.115.108:4000/`

## Server Command

Run on `10.11.115.108`:

```bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-browser-connectivity-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"
hostname -f || hostname
ip -br addr || true

echo "== listeners =="
ss -ltnp | grep -E '(:80|:443|:4000|:3000|:8080|:8100)\b' || true

echo "== containers =="
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'nginx-proxy|litellm|langfuse-web|openwebui|ragflow|NAMES' || true

echo "== nginx config =="
podman exec nginx-proxy nginx -t || true
podman exec nginx-proxy sh -c "grep -n 'server_name manavgat\|proxy_pass http://host.containers.internal:4000' /etc/nginx/nginx.conf" || true

echo "== server-local https through nginx =="
curl --noproxy '*' --max-time 8 -kI \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://manavgat-yzyonetim-dev.ziraat.bank/ || true

echo "== server-ip https through nginx =="
curl --noproxy '*' --max-time 8 -kI \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:10.11.115.108 \
  https://manavgat-yzyonetim-dev.ziraat.bank/ || true

echo "== direct litellm fallback =="
curl --noproxy '*' --max-time 8 -i http://127.0.0.1:4000/health || true
curl --noproxy '*' --max-time 8 -I http://10.11.115.108:4000/ || true

echo "== firewall quick view =="
firewall-cmd --state || true
firewall-cmd --list-all || true
```

## Client Command

Run from the machine where the browser fails.

PowerShell:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-browser-connectivity-$ts.txt"
Start-Transcript -Path $out

Resolve-DnsName manavgat-yzyonetim-dev.ziraat.bank
Test-NetConnection manavgat-yzyonetim-dev.ziraat.bank -Port 443
Test-NetConnection 10.11.115.108 -Port 443
Test-NetConnection 10.11.115.108 -Port 4000

curl.exe -vkI https://manavgat-yzyonetim-dev.ziraat.bank/
curl.exe -vI http://10.11.115.108:4000/

Stop-Transcript
Write-Host "out=$out"
```

Windows terminal server all-host comparison:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-browser-host-compare-$ts.txt"
Start-Transcript -Path $out

$hosts = @(
  "zfgasistan-yzyonetim-dev.ziraat.bank",
  "manavgat-yzyonetim-dev.ziraat.bank",
  "aykal-yzyonetim-dev.ziraat.bank",
  "mercek-yzyonetim-dev.ziraat.bank",
  "mecra-yzyonetim-dev.ziraat.bank"
)

Write-Host "client_source_ip_should_be=10.2.101.18"
ipconfig

foreach ($h in $hosts) {
  Write-Host "== $h dns =="
  Resolve-DnsName $h
  Write-Host "== $h tcp 443 =="
  Test-NetConnection $h -Port 443
  Write-Host "== $h https head =="
  curl.exe -vkI "https://$h/"
}

Write-Host "== direct service ports =="
foreach ($p in @(443,8080,4000,3000,5678,8100)) {
  Test-NetConnection 10.11.115.108 -Port $p
}

Stop-Transcript
Write-Host "out=$out"
```

Linux/macOS:

```bash
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-browser-connectivity-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
date -Is
nslookup manavgat-yzyonetim-dev.ziraat.bank || true
nc -vz manavgat-yzyonetim-dev.ziraat.bank 443 || true
nc -vz 10.11.115.108 443 || true
nc -vz 10.11.115.108 4000 || true
curl --max-time 8 -vkI https://manavgat-yzyonetim-dev.ziraat.bank/ || true
curl --max-time 8 -vI http://10.11.115.108:4000/ || true
```

## Follow-Up: Page Opens Then Times Out

Use this when nginx access logs show `200` for `/`, Swagger assets, or
`/openapi.json`, but the browser later reports `ERR_TIMED_OUT`.

Run on `10.11.115.108`:

```bash
set -u

CLIENT_IP="10.2.101.18"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-manavgat-page-timeout-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

echo "== nginx recent manavgat client lines =="
podman logs --since=20m nginx-proxy 2>&1 | grep -E "${CLIENT_IP}|manavgat|upstream|timed out|reset|502|504|proxy_temp" || true

echo "== litellm recent errors =="
podman logs --since=20m litellm 2>&1 | grep -Ei 'error|exception|traceback|timeout|reset|health|swagger|openapi|pydantic|langfuse' || true

echo "== full GET through nginx from server =="
curl --noproxy '*' --max-time 20 -k \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  -o /tmp/manavgat-root.html \
  -w 'root code=%{http_code} size=%{size_download} connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n' \
  https://manavgat-yzyonetim-dev.ziraat.bank/ || true

curl --noproxy '*' --max-time 30 -k \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  -o /tmp/manavgat-openapi.json \
  -w 'openapi code=%{http_code} size=%{size_download} connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n' \
  https://manavgat-yzyonetim-dev.ziraat.bank/openapi.json || true

curl --noproxy '*' --max-time 30 -k \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  -o /tmp/manavgat-swagger-ui-bundle.js \
  -w 'swagger-js code=%{http_code} size=%{size_download} connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n' \
  https://manavgat-yzyonetim-dev.ziraat.bank/swagger/swagger-ui-bundle.js || true

echo "== direct host-port GETs from server =="
curl --noproxy '*' --max-time 20 \
  -o /tmp/litellm-root-direct.html \
  -w 'direct-root code=%{http_code} size=%{size_download} connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n' \
  http://127.0.0.1:4000/ || true

curl --noproxy '*' --max-time 30 \
  -o /tmp/litellm-openapi-direct.json \
  -w 'direct-openapi code=%{http_code} size=%{size_download} connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n' \
  http://127.0.0.1:4000/openapi.json || true

echo "== browser path note =="
echo "The nginx proxy_temp warning by itself is not a failure. It means nginx buffered a large upstream response to disk."
echo "Direct :4000 from client may be blocked by network policy; browser access should use https://manavgat-yzyonetim-dev.ziraat.bank/ on 443."
```

## Follow-Up: Compare All Browser Hosts

Use this if more than one browser hostname appears broken. This separates a
common nginx/client issue from per-service backend failures.

Run on `10.11.115.108`:

```bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-browser-host-compare-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

for host in \
  zfgasistan-yzyonetim-dev.ziraat.bank \
  manavgat-yzyonetim-dev.ziraat.bank \
  aykal-yzyonetim-dev.ziraat.bank \
  mercek-yzyonetim-dev.ziraat.bank \
  mecra-yzyonetim-dev.ziraat.bank
do
  echo "== https $host via local nginx =="
  curl --noproxy '*' --max-time 12 -kI \
    --resolve "${host}:443:127.0.0.1" \
    "https://${host}/" || true
done

echo "== direct service ports from server =="
for port in 8080 4000 5678 3000 8100; do
  echo "== port $port =="
  curl --noproxy '*' --max-time 12 -I "http://127.0.0.1:${port}/" || true
done

echo "== nginx recent 502/504/timeouts =="
podman logs --since=30m nginx-proxy 2>&1 | grep -Ei 'mercek|manavgat|502|504|timed out|connect\\(\\) failed|upstream|proxy_temp' || true

echo "== langfuse recent status =="
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'langfuse|nginx-proxy|litellm|NAMES' || true
podman logs --since=30m langfuse-web 2>&1 | grep -Ei 'ready|error|exception|traceback|listen|started|3000|clickhouse|migration' || true

echo "== litellm recent status =="
podman logs --since=30m litellm 2>&1 | grep -Ei 'ready|error|exception|traceback|listen|started|4000|pydantic|langfuse|timeout' || true
```

## Read The Result

- Server `HTTP/2 200` and client failure: DNS, firewall, route, client proxy, or TLS inspection issue outside the local stack.
- Server `HTTP/2 502` for manavgat: nginx can receive the request but cannot reach LiteLLM on `4000`.
- Direct `http://10.11.115.108:4000/` works but HTTPS hostname fails from client: focus on DNS/TLS/proxy path to nginx.
- Both direct `4000` and HTTPS hostname fail from client while server-local checks pass: focus on network ACL/firewall between client subnet and `10.11.115.108`.
- `proxy_temp` warnings with matching `200` access-log lines are normally informational for large Swagger/OpenAPI responses.
- Repeated long `urt`/`uht` timings or LiteLLM tracebacks while `/openapi.json` is loading point to LiteLLM backend response generation, not DNS.
- If all browser hostnames fail from the client but server-local HTTPS is `200`, focus on client network/proxy/TLS inspection.
- If only `mercek` is `502` while other hostnames are `200`, focus on Langfuse on port `3000`.
