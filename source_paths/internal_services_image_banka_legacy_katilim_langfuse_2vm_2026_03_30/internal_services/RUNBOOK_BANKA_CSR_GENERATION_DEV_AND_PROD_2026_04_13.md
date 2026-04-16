# Banka CSR Generation Runbook: Dev And Prod

Date: 2026-04-13

Use this to create certificate signing requests for the banka service names.

Recommended future TLS model:
- terminate TLS on the LB when the LB is ready
- forward HTTP from the LB to nginx on the active node
- use node-local nginx TLS only if the LB cannot terminate TLS

## 1) Names Covered

Prod SAN names:

```text
zfgasistan.yzyonetim.ziraat.bank
manavgat.yzyonetim.ziraat.bank
aykal.yzyonetim.ziraat.bank
mercek.yzyonetim.ziraat.bank
mecra.yzyonetim.ziraat.bank
```

Dev SAN names:

```text
zfgasistan.yzyonetim-dev.ziraat.bank
manavgat.yzyonetim-dev.ziraat.bank
aykal.yzyonetim-dev.ziraat.bank
mercek.yzyonetim-dev.ziraat.bank
mecra.yzyonetim-dev.ziraat.bank
```

## 2) Create Dev CSR For 10.11.115.108

On `108` after the installer bundle has been extracted:

```bash
cd /opt/orbina/internal_services
mkdir -p ops/install/katilim/certs/generated

cp ops/install/katilim/certs/dev-lb-openssl.cnf.example \
  ops/install/katilim/certs/generated/dev-108-openssl.cnf

vim ops/install/katilim/certs/generated/dev-108-openssl.cnf
```

Replace these placeholders before generating the CSR:

```text
<STATE_OR_PROVINCE>
<CITY>
<COMPANY_NAME>
<UNIT_NAME>
<CONTACT_EMAIL>
```

Generate the private key and CSR:

```bash
openssl req -new -newkey rsa:4096 -nodes \
  -keyout ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.key \
  -out ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.csr \
  -config ops/install/katilim/certs/generated/dev-108-openssl.cnf
```

Verify the CSR:

```bash
openssl req -in ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.csr \
  -noout -subject -text | grep -A1 "Subject Alternative Name"
```

Send this file to the certificate team:

```text
ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.csr
```

Keep this file private and do not send it:

```text
ops/install/katilim/certs/generated/dev-108.yzyonetim-dev.ziraat.bank.key
```

## 3) Create Prod CSR For 106/107 Or Future LB

On VM1 or the future LB/admin host after the installer bundle has been extracted:

```bash
cd /opt/orbina/internal_services
mkdir -p ops/install/katilim/certs/generated

cp ops/install/katilim/certs/prod-lb-openssl.cnf.example \
  ops/install/katilim/certs/generated/prod-lb-openssl.cnf

vim ops/install/katilim/certs/generated/prod-lb-openssl.cnf
```

Before the real LB exists:
- keep `IP.1 = 10.11.115.106` if the cert will be temporarily installed on VM1
- change `IP.1` to the real LB/VIP IP when the LB is assigned

Replace the same identity placeholders:

```text
<STATE_OR_PROVINCE>
<CITY>
<COMPANY_NAME>
<UNIT_NAME>
<CONTACT_EMAIL>
```

Generate the private key and CSR:

```bash
openssl req -new -newkey rsa:4096 -nodes \
  -keyout ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.key \
  -out ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr \
  -config ops/install/katilim/certs/generated/prod-lb-openssl.cnf
```

Verify the CSR:

```bash
openssl req -in ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr \
  -noout -subject -text | grep -A1 "Subject Alternative Name"
```

Send this file to the certificate team:

```text
ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.csr
```

Keep this file private and do not send it:

```text
ops/install/katilim/certs/generated/prod-yzyonetim.ziraat.bank.key
```

## 4) Use The Returned Certificate Later

If TLS terminates on the LB:
- install the returned certificate and private key on the LB
- keep backend traffic from LB to active nginx as HTTP
- keep `OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf`

If TLS terminates on node-local nginx:
- save the returned cert as `cert.pem`
- save the matching private key as `private.key`
- use `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`

Node-local inventory values:

```text
COPY_TLS=true
LOCAL_CERT_PATH=/absolute/path/to/cert.pem
LOCAL_KEY_PATH=/absolute/path/to/private.key
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.generated.conf
GENERATE_SELF_SIGNED_TLS=false
```

Installed node-local paths:

```text
/etc/pki/tls/certs/cert.pem
/etc/pki/tls/private/private.key
```
