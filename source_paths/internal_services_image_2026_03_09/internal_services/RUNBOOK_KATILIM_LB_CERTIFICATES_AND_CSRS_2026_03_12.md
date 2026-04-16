# Katilim LB Certificate And CSR Runbook

Use this runbook to generate the private key, OpenSSL config, CSR, and final
LB certificate bundle for the Katilim dev and prod load balancers.

This file is self-contained. You do not need any separate template file.

This runbook assumes:

- dev LB IP: `10.210.22.164`
- prod LB IP: `10.210.18.101`
- dev hostnames:
  - `zfgasistan.yzyonetim-dev.ziraatkatilim.local`
  - `manavgat.yzyonetim-dev.ziraatkatilim.local`
  - `aykal.yzyonetim-dev.ziraatkatilim.local`
  - `mercek.yzyonetim-dev.ziraatkatilim.local`
- prod hostnames:
  - `zfgasistan.yzyonetim.ziraatkatilim.local`
  - `manavgat.yzyonetim.ziraatkatilim.local`
  - `aykal.yzyonetim.ziraatkatilim.local`
  - `mercek.yzyonetim.ziraatkatilim.local`

Recommended model:

- terminate public TLS on the LB
- keep LB -> VM traffic on HTTP during initial setup unless your network team
  explicitly requires TLS on both hops
- if VM-side TLS is later required, reuse the signed certificate material by
  placing the cert chain and key at:
  - `/etc/pki/tls/certs/cert.pem`
  - `/etc/pki/tls/private/private.key`

## 1. Prepare A Working Folder

```bash
mkdir -p ~/katilim-lb-certs/dev ~/katilim-lb-certs/prod
```

```bash
cat > ~/katilim-lb-certs/dev/dev-lb-openssl.cnf <<'EOF'
[ req ]
default_bits = 4096
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = TR
ST = <STATE_OR_PROVINCE>
L = <CITY>
O = <COMPANY_NAME>
OU = <UNIT_NAME>
CN = zfgasistan.yzyonetim-dev.ziraatkatilim.local
emailAddress = <CONTACT_EMAIL>

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = zfgasistan.yzyonetim-dev.ziraatkatilim.local
DNS.2 = manavgat.yzyonetim-dev.ziraatkatilim.local
DNS.3 = aykal.yzyonetim-dev.ziraatkatilim.local
DNS.4 = mercek.yzyonetim-dev.ziraatkatilim.local
IP.1 = 10.210.22.164
EOF
```

```bash
cat > ~/katilim-lb-certs/prod/prod-lb-openssl.cnf <<'EOF'
[ req ]
default_bits = 4096
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = TR
ST = <STATE_OR_PROVINCE>
L = <CITY>
O = <COMPANY_NAME>
OU = <UNIT_NAME>
CN = zfgasistan.yzyonetim.ziraatkatilim.local
emailAddress = <CONTACT_EMAIL>

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = zfgasistan.yzyonetim.ziraatkatilim.local
DNS.2 = manavgat.yzyonetim.ziraatkatilim.local
DNS.3 = aykal.yzyonetim.ziraatkatilim.local
DNS.4 = mercek.yzyonetim.ziraatkatilim.local
IP.1 = 10.210.18.101
EOF
```

Edit these two files and replace the placeholder values:

- `<STATE_OR_PROVINCE>`
- `<CITY>`
- `<COMPANY_NAME>`
- `<UNIT_NAME>`
- `<CONTACT_EMAIL>`

You can also remove the `IP.1` line if your certificate team does not want LB
IP addresses in SANs.

## 2. Generate The Dev LB Private Key And CSR

Generate an unencrypted key:

```bash
openssl genrsa -out ~/katilim-lb-certs/dev/dev-lb.key 4096
```

Generate the CSR:

```bash
openssl req -new -sha256 -key ~/katilim-lb-certs/dev/dev-lb.key -out ~/katilim-lb-certs/dev/dev-lb.csr -config ~/katilim-lb-certs/dev/dev-lb-openssl.cnf
```

Inspect the CSR:

```bash
openssl req -in ~/katilim-lb-certs/dev/dev-lb.csr -noout -text
```

Minimal check:

```bash
openssl req -in ~/katilim-lb-certs/dev/dev-lb.csr -noout -subject -reqopt no_pubkey,no_sigdump
```

Expected SAN block in the detailed CSR output should include:

- `DNS:zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `DNS:manavgat.yzyonetim-dev.ziraatkatilim.local`
- `DNS:aykal.yzyonetim-dev.ziraatkatilim.local`
- `DNS:mercek.yzyonetim-dev.ziraatkatilim.local`
- optionally `IP Address:10.210.22.164`

## 3. Generate The Prod LB Private Key And CSR

Generate an unencrypted key:

```bash
openssl genrsa -out ~/katilim-lb-certs/prod/prod-lb.key 4096
```

Generate the CSR:

```bash
openssl req -new -sha256 -key ~/katilim-lb-certs/prod/prod-lb.key -out ~/katilim-lb-certs/prod/prod-lb.csr -config ~/katilim-lb-certs/prod/prod-lb-openssl.cnf
```

Inspect the CSR:

```bash
openssl req -in ~/katilim-lb-certs/prod/prod-lb.csr -noout -text
```

Minimal check:

```bash
openssl req -in ~/katilim-lb-certs/prod/prod-lb.csr -noout -subject -reqopt no_pubkey,no_sigdump
```

Expected SAN block in the detailed CSR output should include:

- `DNS:zfgasistan.yzyonetim.ziraatkatilim.local`
- `DNS:manavgat.yzyonetim.ziraatkatilim.local`
- `DNS:aykal.yzyonetim.ziraatkatilim.local`
- `DNS:mercek.yzyonetim.ziraatkatilim.local`
- optionally `IP Address:10.210.18.101`

## 4. Files To Send For Signing

Normally send only:

- `~/katilim-lb-certs/dev/dev-lb.csr`
- `~/katilim-lb-certs/prod/prod-lb.csr`

Do not send:

- `*.key`

Keep the private keys only with the LB/operator team.

## 5. After Signed Certificates Return

Assume you receive:

- server certificate
- one or more intermediate CA certificates
- optional root CA certificate

Build a full chain file for dev:

```bash
cat ~/katilim-lb-certs/dev/dev-lb.crt ~/katilim-lb-certs/dev/intermediate-1.crt ~/katilim-lb-certs/dev/intermediate-2.crt > ~/katilim-lb-certs/dev/dev-lb-fullchain.pem
```

Build a full chain file for prod:

```bash
cat ~/katilim-lb-certs/prod/prod-lb.crt ~/katilim-lb-certs/prod/intermediate-1.crt ~/katilim-lb-certs/prod/intermediate-2.crt > ~/katilim-lb-certs/prod/prod-lb-fullchain.pem
```

If you receive only one intermediate, remove the extra filename.

Validate the returned dev certificate:

```bash
openssl x509 -in ~/katilim-lb-certs/dev/dev-lb-fullchain.pem -noout -subject -issuer -dates -ext subjectAltName
```

Validate the returned prod certificate:

```bash
openssl x509 -in ~/katilim-lb-certs/prod/prod-lb-fullchain.pem -noout -subject -issuer -dates -ext subjectAltName
```

## 6. What To Install On The LB

For dev LB:

- private key:
  - `~/katilim-lb-certs/dev/dev-lb.key`
- certificate chain:
  - `~/katilim-lb-certs/dev/dev-lb-fullchain.pem`

For prod LB:

- private key:
  - `~/katilim-lb-certs/prod/prod-lb.key`
- certificate chain:
  - `~/katilim-lb-certs/prod/prod-lb-fullchain.pem`

Your LB team can rename these files to match the LB platform conventions.

## 7. Optional VM-Side TLS Placement

If you later decide to terminate TLS on the VMs instead of the LB, or on both,
place the files like this on each VM:

For dev:

```bash
sudo cp ~/katilim-lb-certs/dev/dev-lb-fullchain.pem /etc/pki/tls/certs/cert.pem
```

```bash
sudo cp ~/katilim-lb-certs/dev/dev-lb.key /etc/pki/tls/private/private.key
```

```bash
sudo chmod 644 /etc/pki/tls/certs/cert.pem
```

```bash
sudo chmod 600 /etc/pki/tls/private/private.key
```

For prod:

```bash
sudo cp ~/katilim-lb-certs/prod/prod-lb-fullchain.pem /etc/pki/tls/certs/cert.pem
```

```bash
sudo cp ~/katilim-lb-certs/prod/prod-lb.key /etc/pki/tls/private/private.key
```

```bash
sudo chmod 644 /etc/pki/tls/certs/cert.pem
```

```bash
sudo chmod 600 /etc/pki/tls/private/private.key
```

Then restart the frontend stack:

```bash
cd /opt/orbina/internal_services && sudo ops/ha/stop-active.sh && sudo ops/ha/start-single-node-fallback.sh
```

## 8. Quick Verification After LB Install

From a machine that resolves the hostnames to the LB:

Dev:

```bash
openssl s_client -connect 10.210.22.164:443 -servername zfgasistan.yzyonetim-dev.ziraatkatilim.local -showcerts </dev/null
```

```bash
curl -vkI https://zfgasistan.yzyonetim-dev.ziraatkatilim.local/
```

Prod:

```bash
openssl s_client -connect 10.210.18.101:443 -servername zfgasistan.yzyonetim.ziraatkatilim.local -showcerts </dev/null
```

```bash
curl -vkI https://zfgasistan.yzyonetim.ziraatkatilim.local/
```

## 9. Example CSR Summary

Dev example subject:

```text
Subject: C=TR, ST=<STATE_OR_PROVINCE>, L=<CITY>, O=<COMPANY_NAME>, OU=<UNIT_NAME>, CN=zfgasistan.yzyonetim-dev.ziraatkatilim.local, emailAddress=<CONTACT_EMAIL>
```

Prod example subject:

```text
Subject: C=TR, ST=<STATE_OR_PROVINCE>, L=<CITY>, O=<COMPANY_NAME>, OU=<UNIT_NAME>, CN=zfgasistan.yzyonetim.ziraatkatilim.local, emailAddress=<CONTACT_EMAIL>
```

Dev SAN example:

```text
X509v3 Subject Alternative Name:
    DNS:zfgasistan.yzyonetim-dev.ziraatkatilim.local, DNS:manavgat.yzyonetim-dev.ziraatkatilim.local, DNS:aykal.yzyonetim-dev.ziraatkatilim.local, DNS:mercek.yzyonetim-dev.ziraatkatilim.local, IP Address:10.210.22.164
```

Prod SAN example:

```text
X509v3 Subject Alternative Name:
    DNS:zfgasistan.yzyonetim.ziraatkatilim.local, DNS:manavgat.yzyonetim.ziraatkatilim.local, DNS:aykal.yzyonetim.ziraatkatilim.local, DNS:mercek.yzyonetim.ziraatkatilim.local, IP Address:10.210.18.101
```
