# Banka DNS, LB, HTTP, And Dev Cert Placement

Date: 2026-04-16

Use this as a reference only. It is not part of the Banka runtime install path.

## 1) Current Banka Name Set

Prod:

```text
zfgasistan-yzyonetim.ziraat.bank
manavgat-yzyonetim.ziraat.bank
aykal-yzyonetim.ziraat.bank
mercek-yzyonetim.ziraat.bank
mecra-yzyonetim.ziraat.bank
```

Dev:

```text
zfgasistan-yzyonetim-dev.ziraat.bank
manavgat-yzyonetim-dev.ziraat.bank
aykal-yzyonetim-dev.ziraat.bank
mercek-yzyonetim-dev.ziraat.bank
mecra-yzyonetim-dev.ziraat.bank
```

If real DNS is not ready yet, temporary `/etc/hosts` entries can still point
all prod names to `10.11.115.106` and all dev names to `10.11.115.108`.

## 2) Production LB Model

Keep the Banka nodes HTTP-first. The intended production network path is:

```text
client HTTPS -> LB -> active node HTTP :80
```

Production rules:

- terminate TLS on the LB
- forward plain HTTP from the LB to active nginx on port `80`
- keep `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`
- do not place the prod certificate and private key on `106` or `107` for the
  normal runtime path

If the real LB or VIP IP changes, update only:

```text
LOAD_BALANCER_IP=<REAL_LB_OR_VIP_IP>
```

then regenerate the HA inputs or rebuild the encrypted config image
intentionally.

## 3) Optional Dev Node-Local Certificate Placement

The main dev runtime path stays HTTP-first. If you later want node-local TLS on
dev `108`, place the existing certificate and key on the admin host or company
server that holds the extracted Banka installer tree, then set:

```text
COPY_TLS=true
LOCAL_CERT_PATH=/absolute/path/to/cert.pem
LOCAL_KEY_PATH=/absolute/path/to/private.key
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf
GENERATE_SELF_SIGNED_TLS=false
```

Rebuild the secure config bundle or encrypted config image intentionally, then
rerun install on `108`.

Installed paths on the node remain:

- `/etc/pki/tls/certs/cert.pem`
- `/etc/pki/tls/private/private.key`

CSR generation is intentionally out of the runtime flow and out of this
reference path.

## 4) Validation

LB-terminated production TLS:

```bash
curl -I https://zfgasistan-yzyonetim.ziraat.bank/
curl -I https://manavgat-yzyonetim.ziraat.bank/health
```

HTTP-first direct fallback:

```bash
curl -I http://10.11.115.106:8080/
curl -I http://10.11.115.106:4000/health
curl -I http://10.11.115.108:8080/
curl -I http://10.11.115.108:4000/health
```
