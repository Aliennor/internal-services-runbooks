# Banka Dev108 Browser ERR_TIMED_OUT Classify

Current facts:

- From Windows terminal server `10.2.101.18`, `curl.exe --max-time 15 -vkI`
  returns `HTTP/1.1 200 OK` for `manavgat`, `aykal`, `mecra`, `zfgasistan`
  and (after langfuse-web recreate) `mercek`.
- `Test-NetConnection` for TCP 443 succeeds.
- Browser still shows `ERR_TIMED_OUT` for the same hostnames.

This means nginx and the application stack are healthy; the timeout is in
the browser's own network path (system proxy, TLS inspection, PAC script,
extension, or a specific asset URL that the page loads).

## Step 1: Classify Browser vs Curl Path

Run on Windows terminal server `10.2.101.18` in PowerShell:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-browser-proxy-classify-$ts.txt"
Start-Transcript -Path $out

Write-Host "== system winhttp proxy =="
netsh winhttp show proxy

Write-Host "== ie/wininet proxy (HKCU) =="
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
  Select-Object ProxyEnable, ProxyServer, ProxyOverride, AutoConfigURL

Write-Host "== env proxies =="
$env:HTTP_PROXY
$env:HTTPS_PROXY
$env:NO_PROXY

Write-Host "== curl via system proxy (simulate browser path) =="
$hosts = @(
  "manavgat-yzyonetim-dev.ziraat.bank",
  "mercek-yzyonetim-dev.ziraat.bank",
  "aykal-yzyonetim-dev.ziraat.bank",
  "mecra-yzyonetim-dev.ziraat.bank",
  "zfgasistan-yzyonetim-dev.ziraat.bank"
)
foreach ($h in $hosts) {
  Write-Host "== $h GET via system proxy =="
  curl.exe --max-time 20 -vkL "https://$h/"
}

Write-Host "== curl with --noproxy (bypass proxy) =="
foreach ($h in $hosts) {
  Write-Host "== $h GET noproxy =="
  curl.exe --max-time 20 --noproxy '*' -vkL "https://$h/"
}

Stop-Transcript
Write-Host "out=$out"
```

Interpretation:

- If `curl via system proxy` times out but `--noproxy` returns `200`, the
  browser path goes through a corporate proxy that is not forwarding these
  hostnames, and curl was silently bypassing the proxy before.
- If both paths succeed, the browser is using a different proxy (PAC script,
  extension, or Chrome-specific settings).

## Step 2: Ask The Browser Where It Actually Fails

In the browser that shows `ERR_TIMED_OUT`:

1. Open DevTools > Network.
2. Enable "Preserve log".
3. Reload the failing URL.
4. Record:
   - the exact URL that shows a pending / failed request
   - its `Remote Address`
   - its `Status`
   - whether the request is HTTPS, HTTP, or to a direct IP / port

If the failing URL is the initial HTML (`https://<host>/`):

- Copy its request URL and also check `chrome://net-export/` or
  `edge://net-export/` trace for 30 seconds while reproducing.

If the failing URL is a sub-resource (asset, API, openapi.json):

- Note if it points to `10.11.115.108:<port>` or another hostname.

## Step 3: Quick Browser-Side Sanity Fixes

Try these, one at a time, in the failing browser, and retry after each:

```text
1. Open in InPrivate / Incognito window.
2. Disable all browser extensions for the session.
3. Clear HSTS for the hostname (only if safe):
   - Chrome: chrome://net-internals/#hsts  → Query/Delete domain security policies.
4. Flush DNS and client-side caches:
   - cmd: ipconfig /flushdns
5. Try another browser (Edge vs Chrome) against the same URL.
```

## Step 4: Browser-Only Diagnostic Artifacts To Send Back

- `/Users/.../Temp/banka-dev108-browser-proxy-classify-*.txt`
- DevTools Network tab screenshot or HAR export of the failing reload
- `chrome://net-export/` log if available

## Read The Result

- Proxy misroute: the fix is an exception in the corporate proxy / PAC for
  `*.ziraat.bank` hostnames; nothing to change on the server.
- Specific asset URL pointing to `10.11.115.108:<port>` different from `443`:
  the failing port is blocked by client network policy; app public URL must
  stay on `443` hostname.
- All browser probes still fail and `curl --noproxy` works: TLS inspection
  or a browser extension is breaking the connection.
