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

The r26/r6 dev first-install path is HTTP/IP-first. To switch dev `108` to
node-local HTTPS after first install is healthy, use:

- `RUNBOOK_BANKA_DEV108_HTTPS_LITELLM_CUTOVER_2026_04_17.md`

That cutover expects the target node to already have:

```text
/tmp/cert.pem
/tmp/private.key
```

The r26/r6 first-install defaults before cutover are:

```text
COPY_TLS=false
NODE_TLS_CERT_SOURCE_PATH=/tmp/cert.pem
NODE_TLS_KEY_SOURCE_PATH=/tmp/private.key
GENERATE_SELF_SIGNED_TLS=true
PUBLIC_URL_SCHEME=http
DIRECT_PUBLIC_BASE_SCHEME=http
DIRECT_PUBLIC_BASE_HOST=10.11.115.108
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf
```

The HTTPS cutover installs `/tmp/cert.pem` and `/tmp/private.key` into
`/etc/pki/tls`, switches nginx to `nginx.generated.conf`, and updates:

- LiteLLM `PROXY_BASE_URL=https://manavgat-yzyonetim-dev.ziraat.bank`
- Langfuse `NEXTAUTH_URL=https://mercek-yzyonetim-dev.ziraat.bank`

LiteLLM and Langfuse browser URLs default to direct HTTP on the node IP during
bring-up, so unresolved DNS does not block login:

- LiteLLM: `http://10.11.115.108:4000`
- Langfuse: `http://10.11.115.108:3000`

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
