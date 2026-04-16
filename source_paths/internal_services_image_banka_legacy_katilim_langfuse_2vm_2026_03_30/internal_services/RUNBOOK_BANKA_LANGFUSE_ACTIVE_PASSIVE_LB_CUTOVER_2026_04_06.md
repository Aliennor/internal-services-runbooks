# Banka Langfuse Runbook: Add VM2 Passive And Prepare LB Cutover

Date: 2026-04-06

Scope:
- banca production path
- assumes `10.11.115.106` is already active
- adds `10.11.115.107` as passive
- still no LB cutover during bootstrap

Public prod names remain:
- `zfgasistan.yzyonetim.ziraat.bank`
- `manavgat.yzyonetim.ziraat.bank`
- `aykal.yzyonetim.ziraat.bank`
- `mercek.yzyonetim.ziraat.bank`
- `mecra.yzyonetim.ziraat.bank`

## 0) Reuse The Same Inventory

On the company server or admin host where the installer bundle was extracted:

```bash
cd /opt/orbina/internal_services
vim ops/install/katilim/inventory.banka-ha-ready.env
```

Before the real LB exists, keep:

```text
LOAD_BALANCER_IP=10.11.115.106
OPENWEBUI_NGINX_CONFIG_PATH=./nginx.http-only.generated.conf
```

## 1) Re-Render HA Inputs And Build A Fresh Bundle

For the current banka flow, prefer the already-published encrypted config
image. If the encrypted config image has the correct current settings, pull and
extract that image on each target node instead of building a bundle here.

Only run the following commands on a company server or admin host when you are
intentionally creating a fresh server-side config bundle:

```bash
bash ops/install/katilim/render-ha-env.sh ops/install/katilim/inventory.banka-ha-ready.env
bash ops/install/katilim/prepare-secure-config-bundle.sh \
  ops/install/katilim/inventory.banka-ha-ready.env \
  "$PWD/banka_langfuse_secure_config_$(date +%Y%m%d_%H%M%S).tar.gz"
```

## 2) Transfer To Both Nodes

Run this only from a company server or admin host with SSH access to both VMs.
Do not stage the files on an operator machine.

```bash
bash ops/install/katilim/push-to-vms.sh ops/install/katilim/inventory.banka-ha-ready.env
scp ./banka_langfuse_secure_config_*.tar.gz root@10.11.115.106:/opt/orbina/incoming/
scp ./banka_langfuse_secure_config_*.tar.gz root@10.11.115.107:/opt/orbina/incoming/
```

Important:
- do not manually upload Ragflow volume export to `10.11.115.107`
- seed only `VM1`
- HA sync will carry Ragflow and Qdrant state later

## 3) Apply The Secure Bundle On Both Nodes

On `VM1`:

```bash
ssh root@10.11.115.106
cd /opt/orbina/internal_services
LATEST_BUNDLE=$(ls -1t /opt/orbina/incoming/banka_langfuse_secure_config_*.tar.gz | head -n 1)
sudo ops/install/katilim/apply-secure-config-bundle.sh "$LATEST_BUNDLE" /opt/orbina
exit
```

On `VM2`:

```bash
ssh root@10.11.115.107
cd /opt/orbina/internal_services
LATEST_BUNDLE=$(ls -1t /opt/orbina/incoming/banka_langfuse_secure_config_*.tar.gz | head -n 1)
sudo ops/install/katilim/apply-secure-config-bundle.sh "$LATEST_BUNDLE" /opt/orbina
```

## 4) Install VM2 As Passive

On `VM2`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh \
  --role passive \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

## 5) Enable Sync On VM1

On `VM1`:

```bash
ssh root@10.11.115.106
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

## 6) Validate Health

On `VM1`:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
systemctl status internal-services-ha-sync-light.timer --no-pager
systemctl status internal-services-ha-sync-heavy.timer --no-pager
```

Expected:
- `/ready` is `200`

On `VM2`:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status && echo
systemctl status internal-services-ha-sync-light.timer --no-pager || true
systemctl status internal-services-ha-sync-heavy.timer --no-pager || true
```

Expected:
- `/ready` is `503`
- sync timers are not active on `VM2`

## 7) Validate PostgreSQL Roles

On `VM1`:

```bash
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();"
```

Expected:
- `f`

On `VM2`:

```bash
docker exec shared_postgres psql -U "${POSTGRES_USER:-postgres}" -d postgres -c "select pg_is_in_recovery();"
```

Expected:
- `t`

## 8) Keep Traffic On VM1 Until LB Exists

Before LB cutover, keep:
- `/etc/hosts` or test DNS pointed at `10.11.115.106`
- direct IP ports on `10.11.115.106` for fallback

Do not point public names to `10.11.115.107` directly.

## 9) Later DNS, LB, And TLS Cutover

When the LB or VIP is available, use:
- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`

That runbook covers:
- changing `LOAD_BALANCER_IP`
- switching DNS from node IP to LB/VIP
- keeping HTTP behind the LB or enabling node-local nginx TLS
- certificate placement

## 10) Optional Promotion Test

Only in a controlled window:

```bash
ssh root@10.11.115.107
cd /opt/orbina/internal_services
sudo ops/ha/promote-passive.sh
```

Validate:
- `VM2` `/ready` becomes `200`
- PostgreSQL on `VM2` is no longer in recovery
