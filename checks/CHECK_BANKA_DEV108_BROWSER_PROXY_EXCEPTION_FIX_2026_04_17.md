# Banka Dev108 Browser Proxy Exception Fix

## Root Cause

On Windows terminal server `10.2.101.18`:

- `ProxyEnable = 1`
- `ProxyServer = http://istvekil.fintek.local:8080`
- `ProxyOverride = 10.*;*.fintek.local;*-ref.sube.ziraat.bank;*-prod.sube.ziraat.bank;172...`

`*-yzyonetim-dev.ziraat.bank` is NOT in the override list, so the browser
sends its requests to the corporate proxy. The proxy cannot reach the
internal dev server `10.11.115.108`, so the browser times out with
`ERR_TIMED_OUT`. `curl.exe` returned `200` because it does not honor
WinINET / IE proxy settings by default; it went direct.

No change is required on the server. The fix is to add the dev hostname
pattern to the WinINET proxy bypass list.

## Fix A: Per-User Registry (Recommended)

Run in PowerShell on `10.2.101.18` as the same user that runs the browser:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "$env:TEMP\banka-dev108-browser-proxy-fix-$ts.txt"
Start-Transcript -Path $out

$reg = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$cur = (Get-ItemProperty -Path $reg).ProxyOverride
Write-Host "before=$cur"

$additions = @(
  '*-yzyonetim-dev.ziraat.bank',
  '*.ziraat.bank',
  '10.11.115.108'
)
$parts = @()
if ($cur) { $parts = $cur -split ';' }
foreach ($a in $additions) {
  if ($parts -notcontains $a) { $parts += $a }
}
$new = ($parts -join ';')
Set-ItemProperty -Path $reg -Name ProxyOverride -Value $new
Write-Host "after=$new"

Write-Host "== verify =="
Get-ItemProperty -Path $reg |
  Select-Object ProxyEnable, ProxyServer, ProxyOverride

Stop-Transcript
Write-Host "out=$out"
```

Then:

1. Close ALL browser windows (Edge, Chrome).
2. Reopen and visit `https://mercek-yzyonetim-dev.ziraat.bank/`.
3. Retry the other four hostnames.

## Fix B: Edge / Chrome GUI Proxy Exceptions (Fallback)

If the registry fix is blocked by policy, the same effect can be applied
through the system GUI:

1. `Win+R` → `inetcpl.cpl` → `Connections` → `LAN settings` → `Advanced`.
2. In `Exceptions`, append:

   ```text
   *-yzyonetim-dev.ziraat.bank;*.ziraat.bank;10.11.115.108
   ```

3. OK → OK → restart the browser.

## Fix C: System-Wide netsh WinHTTP (For Non-Interactive Tools Only)

WinHTTP proxy is separate from WinINET. Browsers use WinINET. Only touch
this if non-browser tools like `winget` or background services complain.

```powershell
netsh winhttp show proxy
```

If a proxy must be set here, mirror the same overrides. Do not change this
step unless the browser-first fix is already applied and validated.

## Validate

After applying Fix A or B, from `10.2.101.18`:

```powershell
$hosts = @(
  "manavgat-yzyonetim-dev.ziraat.bank",
  "mercek-yzyonetim-dev.ziraat.bank",
  "aykal-yzyonetim-dev.ziraat.bank",
  "mecra-yzyonetim-dev.ziraat.bank",
  "zfgasistan-yzyonetim-dev.ziraat.bank"
)
foreach ($h in $hosts) {
  Start-Process "https://$h/"
}
```

All five should load in the browser now.

## Send Back

- `/Users/.../Temp/banka-dev108-browser-proxy-fix-*.txt`
- Short note for each hostname: `loads` / `still times out` / other error
