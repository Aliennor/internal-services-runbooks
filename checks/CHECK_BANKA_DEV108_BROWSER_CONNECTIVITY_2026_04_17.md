# Banka Dev108 Browser Connectivity Check

Use this when a URL works from the server with `curl --resolve` but does not
open from a browser or another client machine.

Target:

- server: `10.11.115.108`
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

## Read The Result

- Server `HTTP/2 200` and client failure: DNS, firewall, route, client proxy, or TLS inspection issue outside the local stack.
- Server `HTTP/2 502` for manavgat: nginx can receive the request but cannot reach LiteLLM on `4000`.
- Direct `http://10.11.115.108:4000/` works but HTTPS hostname fails from client: focus on DNS/TLS/proxy path to nginx.
- Both direct `4000` and HTTPS hostname fail from client while server-local checks pass: focus on network ACL/firewall between client subnet and `10.11.115.108`.
