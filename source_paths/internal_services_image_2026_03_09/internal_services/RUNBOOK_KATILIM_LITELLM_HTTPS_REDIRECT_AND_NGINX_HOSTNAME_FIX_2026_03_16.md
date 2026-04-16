# Katilim LiteLLM HTTPS Redirect And Nginx Hostname Fix

Use this runbook on an already-installed Katilim VM when:

- LiteLLM opens on the `manavgat...` hostname
- clicking the admin panel or login redirects to a dead URL and the browser shows `connection refused`
- the current nginx config still contains the old `.zb` hostnames

Purpose:

- force LiteLLM to generate HTTPS admin/login redirects
- remove the old `.zb` Katilim hostnames from nginx
- keep only the `*.ziraatkatilim.local` hostnames in the live Katilim nginx config

This is a live VM-side fix for the current running servers.

## 1. Update LiteLLM Redirect Base URL

On a dev VM:

```bash
sudo sh -c 'grep -q "^PROXY_BASE_URL=" /opt/orbina/internal_services/litellm/.env && sed -i.bak "s|^PROXY_BASE_URL=.*|PROXY_BASE_URL=https://manavgat.yzyonetim-dev.ziraatkatilim.local|" /opt/orbina/internal_services/litellm/.env || echo "PROXY_BASE_URL=https://manavgat.yzyonetim-dev.ziraatkatilim.local" >> /opt/orbina/internal_services/litellm/.env'
```

On a prod VM:

```bash
sudo sh -c 'grep -q "^PROXY_BASE_URL=" /opt/orbina/internal_services/litellm/.env && sed -i.bak "s|^PROXY_BASE_URL=.*|PROXY_BASE_URL=https://manavgat.yzyonetim.ziraatkatilim.local|" /opt/orbina/internal_services/litellm/.env || echo "PROXY_BASE_URL=https://manavgat.yzyonetim.ziraatkatilim.local" >> /opt/orbina/internal_services/litellm/.env'
```

Verify:

```bash
grep '^PROXY_BASE_URL=' /opt/orbina/internal_services/litellm/.env
```

## 2. Remove Old `.zb` Hostnames From Live Katilim Nginx Config

```bash
sudo perl -0pi -e 's/zfgasistan\.yzyonetim-dev\.zb\s+//g; s/manavgat\.yzyonetim-dev\.zb\s+//g; s/aykal\.yzyonetim-dev\.zb\s+//g; s/mercek\.yzyonetim-dev\.zb\s+//g' /opt/orbina/internal_services/openweb-ui/nginx.conf
```

Optional check:

```bash
grep -n 'server_name' /opt/orbina/internal_services/openweb-ui/nginx.conf
```

Expected result:

- only `*.ziraatkatilim.local` Katilim names remain in the `server_name` lines

## 3. Restart LiteLLM And Nginx

```bash
cd /opt/orbina/internal_services/litellm && docker compose up -d litellm
```

```bash
cd /opt/orbina/internal_services/openweb-ui && docker compose restart nginx
```

## 4. Validate On The VM

For dev:

```bash
curl -kI --resolve manavgat.yzyonetim-dev.ziraatkatilim.local:443:127.0.0.1 https://manavgat.yzyonetim-dev.ziraatkatilim.local/
```

For prod:

```bash
curl -kI --resolve manavgat.yzyonetim.ziraatkatilim.local:443:127.0.0.1 https://manavgat.yzyonetim.ziraatkatilim.local/
```

Optional LiteLLM health check:

```bash
curl -sS http://127.0.0.1:4000/health || true
```

## 5. Validate In The Browser

For dev:

- open `https://manavgat.yzyonetim-dev.ziraatkatilim.local`

For prod:

- open `https://manavgat.yzyonetim.ziraatkatilim.local`

If the LB certificate is still not fully correct for the exact hostname:

- the browser warning can still appear
- use `continue anyway`
- after this fix, LiteLLM should keep redirecting the admin/login flow to `https://...` instead of falling back to dead `http://...`

## 6. Scope Note

This fixes the live running Katilim VM behavior.

It does not by itself rebuild the encrypted config image. If you later refresh
the Katilim config bundle again, make sure the published encrypted config image
also carries the HTTPS `PROXY_BASE_URL` value.
