# Banka Runbook: DNS, LB, And TLS Cutover

Date: 2026-04-09

Scope:
- banca-only Langfuse installer surface
- applies after first HTTP deployment is already working
- covers prod `106/107` and dev `108`

## Current Recommended State Before Cutover

- HTTP on nginx
- direct IP:port access enabled
- prod names still pointed to `10.11.115.106` or test `/etc/hosts`
- dev names still pointed to `10.11.115.108` or test `/etc/hosts`

## 1) DNS Targets

Prod:

```text
zfgasistan.yzyonetim.ziraat.bank
manavgat.yzyonetim.ziraat.bank
aykal.yzyonetim.ziraat.bank
mercek.yzyonetim.ziraat.bank
mecra.yzyonetim.ziraat.bank
```

Dev:

```text
zfgasistan.yzyonetim-dev.ziraat.bank
manavgat.yzyonetim-dev.ziraat.bank
aykal.yzyonetim-dev.ziraat.bank
mercek.yzyonetim-dev.ziraat.bank
mecra.yzyonetim-dev.ziraat.bank
```

## 2) If No Real DNS Yet

Use temporary `/etc/hosts`.

Prod:

```text
10.11.115.106 zfgasistan.yzyonetim.ziraat.bank
10.11.115.106 manavgat.yzyonetim.ziraat.bank
10.11.115.106 aykal.yzyonetim.ziraat.bank
10.11.115.106 mercek.yzyonetim.ziraat.bank
10.11.115.106 mecra.yzyonetim.ziraat.bank
```

Dev:

```text
10.11.115.108 zfgasistan.yzyonetim-dev.ziraat.bank
10.11.115.108 manavgat.yzyonetim-dev.ziraat.bank
10.11.115.108 aykal.yzyonetim-dev.ziraat.bank
10.11.115.108 mercek.yzyonetim-dev.ziraat.bank
10.11.115.108 mecra.yzyonetim-dev.ziraat.bank
```

## 3) LB Recommendation

Recommended future state:
- terminate TLS on the LB
- send HTTP from LB to the active node nginx on port `80`
- keep direct IP ports available for break-glass/debugging

This means you can keep:

```text
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf
```

after LB cutover if the LB handles HTTPS.

## 4) Inventory Changes For A Real LB Or VIP

On the company server or admin host where the installer bundle was extracted:

```bash
cd /opt/orbina/internal_services
vim ops/install/katilim/inventory.banka-ha-ready.env
```

Set:

```text
LOAD_BALANCER_IP=<REAL_LB_OR_VIP_IP>
```

Then regenerate the HA inputs on that same server:

```bash
bash ops/install/katilim/render-ha-env.sh ops/install/katilim/inventory.banka-ha-ready.env
bash ops/install/katilim/prepare-secure-config-bundle.sh ops/install/katilim/inventory.banka-ha-ready.env
```

If you are using the already-published encrypted config image flow, do not
build a new config bundle locally. Re-extract the appropriate encrypted config
image on each target node, then reapply the installer steps from the prod
runbook.

If you intentionally build a new config bundle, build it on a company server or
admin host and transfer it directly between company servers. Do not use any
operator-machine local path.

## 5) Node-Local TLS Fallback

If TLS must terminate on nginx instead of the LB:

1. Place the certificate and key on the company server or admin host that holds
   the extracted installer bundle.
2. Edit inventory on that server:

```text
COPY_TLS=true
LOCAL_CERT_PATH=/absolute/path/to/cert.pem
LOCAL_KEY_PATH=/absolute/path/to/private.key
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf
GENERATE_SELF_SIGNED_TLS=false
```

3. Rebuild the secure bundle:

```bash
bash ops/install/katilim/prepare-secure-config-bundle.sh ops/install/katilim/inventory.banka-ha-ready.env
```

4. Copy and apply it to the target node or nodes.
5. Rerun install:

```bash
ssh root@10.11.115.106
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt
```

For the HA pair, repeat the bundle apply and install step on `107` with `--role passive`.

Installed certificate paths on the node:
- `/etc/pki/tls/certs/cert.pem`
- `/etc/pki/tls/private/private.key`

## 6) Certificate Examples

Use these example SAN configs:
- `ops/install/katilim/certs/prod-lb-openssl.cnf.example`
- `ops/install/katilim/certs/dev-lb-openssl.cnf.example`

For the full CSR generation flow, use:
- `RUNBOOK_BANKA_CSR_GENERATION_DEV_AND_PROD_2026_04_13.md`

## 7) Validation

LB-terminated TLS:

```bash
curl -I https://zfgasistan.yzyonetim.ziraat.bank/
curl -I https://manavgat.yzyonetim.ziraat.bank/health
```

Node-local TLS:

```bash
curl -k -I https://zfgasistan.yzyonetim.ziraat.bank/
curl -k -I https://manavgat.yzyonetim.ziraat.bank/health
```

Fallback direct ports should still answer unless you later restrict
`DIRECT_BIND_ADDRESS`.
