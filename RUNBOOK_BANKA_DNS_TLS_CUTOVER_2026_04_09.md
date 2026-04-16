# Banka DNS, LB, And TLS Placement

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
- keep `PUBLIC_URL_SCHEME=http`
- do not place the prod certificate and private key on `106` or `107` for the normal runtime path

If the real LB or VIP IP changes, update only:

```text
LOAD_BALANCER_IP=<REAL_LB_OR_VIP_IP>
```

then regenerate the HA inputs or rebuild the encrypted config image
intentionally.

## 3) Dev Certificate Source Files

The main dev runtime path now expects the build machine to already have:

```text
/tmp/cert.pem
/tmp/private.key
```

The Banka dev install defaults are:

```text
COPY_TLS=false
NODE_TLS_CERT_SOURCE_PATH=/tmp/cert.pem
NODE_TLS_KEY_SOURCE_PATH=/tmp/private.key
GENERATE_SELF_SIGNED_TLS=false
PUBLIC_URL_SCHEME=https
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf
```

So you do not need to hand-edit an inventory or rebuild the dev config image
just to include the certificate and key. The installer on `108` copies them
from `/tmp` directly during `install-node.sh`.

Installed paths on the dev node remain:

- `/etc/pki/tls/certs/cert.pem`
- `/etc/pki/tls/private/private.key`

## 4) Validation

LB-terminated production TLS:

```bash
curl -I https://zfgasistan-yzyonetim.ziraat.bank/
curl -I https://manavgat-yzyonetim.ziraat.bank/health
```

Dev node-local TLS:

```bash
curl -kI https://zfgasistan-yzyonetim-dev.ziraat.bank/
curl -kI https://manavgat-yzyonetim-dev.ziraat.bank/
```

HTTP fallback checks:

```bash
curl -I http://10.11.115.106:8080/
curl -I http://10.11.115.106:4000/health
curl -I http://10.11.115.108:8080/
curl -I http://10.11.115.108:4000/health
```
