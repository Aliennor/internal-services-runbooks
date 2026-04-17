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

## Follow-Up: Manavgat Browser Timeout After Initial 200

Use this if Windows `10.2.101.18` gets `200` from `HEAD /`, but the browser
shows `ERR_TIMED_OUT` after opening the page.

Run on `10.11.115.108`:

```bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-manavgat-html-url-check-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

curl --noproxy '*' --max-time 20 -k \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  -o /tmp/manavgat-root.html \
  https://manavgat-yzyonetim-dev.ziraat.bank/ || true

curl --noproxy '*' --max-time 30 -k \
  --resolve manavgat-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  -o /tmp/manavgat-openapi.json \
  https://manavgat-yzyonetim-dev.ziraat.bank/openapi.json || true

echo "== absolute or direct URLs in root html =="
grep -En 'https?://|10\\.11\\.115\\.108|:4000|:3000|:8080|:8100' /tmp/manavgat-root.html || true

echo "== absolute or direct URLs in openapi =="
grep -En 'https?://|10\\.11\\.115\\.108|:4000|:3000|:8080|:8100' /tmp/manavgat-openapi.json | head -80 || true

echo "== nginx accesses from Windows client =="
podman logs --since=20m nginx-proxy 2>&1 | grep '10.2.101.18' || true
```

Run on Windows terminal server `10.2.101.18`:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-manavgat-full-get-$ts.txt"
Start-Transcript -Path $out

curl.exe -vkL --max-time 30 -o "$env:TEMP\manavgat-root.html" "https://manavgat-yzyonetim-dev.ziraat.bank/"
curl.exe -vkL --max-time 60 -o "$env:TEMP\manavgat-openapi.json" "https://manavgat-yzyonetim-dev.ziraat.bank/openapi.json"
curl.exe -vkL --max-time 60 -o "$env:TEMP\manavgat-swagger-ui-bundle.js" "https://manavgat-yzyonetim-dev.ziraat.bank/swagger/swagger-ui-bundle.js"

Select-String -Path "$env:TEMP\manavgat-root.html" -Pattern "http://","https://","10.11.115.108",":4000",":3000",":8080",":8100"
Select-String -Path "$env:TEMP\manavgat-openapi.json" -Pattern "http://","https://","10.11.115.108",":4000",":3000",":8080",":8100" | Select-Object -First 80

Stop-Transcript
Write-Host "out=$out"
```

## Follow-Up: Mercek 502 / Langfuse Port 3000

Use this when `mercek-yzyonetim-dev.ziraat.bank` returns `502` while other
browser hosts return `200`.

Run on `10.11.115.108`:

```bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/banka-dev108-mercek-langfuse-502-${TS}.log"
exec > >(tee -a "$OUT") 2>&1

echo "out=$OUT"
echo "timestamp=$(date -Is)"

echo "== mercek through nginx =="
curl --noproxy '*' --max-time 12 -kI \
  --resolve mercek-yzyonetim-dev.ziraat.bank:443:127.0.0.1 \
  https://mercek-yzyonetim-dev.ziraat.bank/ || true

echo "== langfuse direct ports =="
curl --noproxy '*' --max-time 12 -I http://127.0.0.1:3000/ || true
curl --noproxy '*' --max-time 12 -I http://10.11.115.108:3000/ || true
podman exec nginx-proxy wget -S -O- http://host.containers.internal:3000/ >/dev/null || true

echo "== langfuse process and logs =="
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'langfuse|NAMES' || true
podman logs --tail=220 langfuse-web 2>&1 | grep -Ei 'ready|error|exception|traceback|listen|started|3000|next|clickhouse|migration|shutting|exited' || true
podman inspect langfuse-web --format '{{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}' || true
```

Observed evidence from `2026-04-17 18:54` run:

- `manavgat-yzyonetim-dev.ziraat.bank` served `/` and `/openapi.json` as `200`; no direct `10.11.115.108:<port>` URL was found in the root HTML grep.
- `mercek-yzyonetim-dev.ziraat.bank` returned `HTTP/2 502` through nginx.
- Direct host checks to Langfuse failed with `curl: (7) Failed to connect to 127.0.0.1 port 3000: Connection refused` and same on `10.11.115.108:3000`.
- `langfuse-web` container still reported `Up` and log line `Ready`, which means process-state alone is not enough; validate effective listener and upstream reachability.
- `podman exec nginx-proxy wget ... host.containers.internal:3000` can be polluted by proxy environment and show `504 Unknown Host`; rerun with `--no-proxy` before concluding host routing is broken.

Interpretation:

- This is a `mercek`-specific backend path issue (`nginx -> host.containers.internal:3000`) and not a shared browser DNS/TLS failure.
- If `manavgat` is `200` while `mercek` is `502`, classify the incident under Langfuse/port-3000 availability, not LiteLLM.

## Read The Result

- Server `HTTP/2 200` and client failure: DNS, firewall, route, client proxy, or TLS inspection issue outside the local stack.
- Server `HTTP/2 502` for manavgat: nginx can receive the request but cannot reach LiteLLM on `4000`.
- Direct `http://10.11.115.108:4000/` works but HTTPS hostname fails from client: focus on DNS/TLS/proxy path to nginx.
- Both direct `4000` and HTTPS hostname fail from client while server-local checks pass: focus on network ACL/firewall between client subnet and `10.11.115.108`.
- `proxy_temp` warnings with matching `200` access-log lines are normally informational for large Swagger/OpenAPI responses.
- Repeated long `urt`/`uht` timings or LiteLLM tracebacks while `/openapi.json` is loading point to LiteLLM backend response generation, not DNS.
- If all browser hostnames fail from the client but server-local HTTPS is `200`, focus on client network/proxy/TLS inspection.
- If only `mercek` is `502` while other hostnames are `200`, focus on Langfuse on port `3000`.
- If Windows full GETs to manavgat succeed but browser still times out, inspect the browser devtools Network tab for a request that is not going through `https://manavgat-yzyonetim-dev.ziraat.bank/`.
- If `/tmp/manavgat-root.html` or `/tmp/manavgat-openapi.json` contains direct `10.11.115.108:<port>` URLs, fix the app public/base URL so browser assets stay on the hostname over 443.
