# Banka Single-VM Runbook Using The Legacy Katilim Installer

Date: 2026-03-25

Use this runbook when:

- the new topology is not ready yet
- you want the legacy March 9 Katilim installer surface
- banka `VM1` is `10.11.115.106`
- banka `VM2` will later be `10.11.115.107`
- there is no load balancer yet

This path brings up only `VM1` in single-node fallback mode, but keeps the
inventory, rendered HA env, hostnames, and VM role split aligned with a future
active/passive setup and later LB.

## Deployment Posture

- current runtime mode:
  - `VM1` active only
- prepared but not bootstrapped yet:
  - `VM2` passive
- prepared but not available yet:
  - LB or VIP
- keep the same service names now and later:
  - point them to `VM1` first
  - repoint them to the LB when the LB exists

## Decisions

- authoritative installer surface:
  - `internal_services_image_banka_legacy_katilim_single_vm_2026_03_25/internal_services`
- current runtime target:
  - `VM1=10.11.115.106`
- reserved future passive node:
  - `VM2=10.11.115.107`
- temporary service hostnames:
  - `openwebui.banka.local`
  - `litellm.banka.local`
  - `n8n.banka.local`
  - `phoenix.banka.local`
  - `metabase.banka.local`
- these hostnames point to `10.11.115.106` now
- later, keep the same names and repoint them to the future LB
- `ENABLE_RAGFLOW_STACK=false` for now because this legacy bundle still has a
  non-Docker-Hub Opensearch dependency in the Ragflow path

## 0) Preconditions On VM1

The installer still uses the `docker` command. On banka this is acceptable only
if Docker itself is installed or Podman is already exposed through Docker
compatibility.

Run on `10.11.115.106` first:

```bash
docker --version
docker compose version
```

If those fail on a Podman-based host, fix the Docker-compat layer first before
continuing with this legacy installer.

## 1) Create The Banka Inventory On The Workstation

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_banka_legacy_katilim_single_vm_2026_03_25/internal_services/ops/install/katilim
cp inventory.banka-single-vm.env.example inventory.banka-single-vm.env
```

If you already know the final banka DNS names, replace the temporary
`*.banka.local` names now. Otherwise keep them and just change DNS later when
the LB exists.

## 2) Add Temporary Host Mappings

Add these entries on:

- the operator workstation you will test from
- `VM1` itself if you want local curl/browser tests by name

```text
10.11.115.106 openwebui.banka.local
10.11.115.106 litellm.banka.local
10.11.115.106 n8n.banka.local
10.11.115.106 phoenix.banka.local
10.11.115.106 metabase.banka.local
```

Do not point these names to `10.11.115.107` yet.

## 3) Render HA Inputs And Secure Config

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_banka_legacy_katilim_single_vm_2026_03_25/internal_services/ops/install/katilim
./render-ha-env.sh inventory.banka-single-vm.env
./prepare-secure-config-bundle.sh inventory.banka-single-vm.env /tmp/banka_single_vm_secure_config_$(date +%Y%m%d_%H%M%S).tar.gz
ls -l rendered/ha.vm1.env rendered/ha.vm2.env /tmp/banka_single_vm_secure_config_*.tar.gz
```

## 4) Transfer Only VM1

Use the new VM1-only mode. This still renders `ha.vm2.env` for later, but it
does not try to contact `10.11.115.107` yet.

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_banka_legacy_katilim_single_vm_2026_03_25/internal_services/ops/install/katilim
./push-to-vms.sh --vm1-only inventory.banka-single-vm.env
scp /tmp/banka_single_vm_secure_config_*.tar.gz root@10.11.115.106:/opt/orbina/incoming/
```

## 5) Apply The Secure Config On VM1

```bash
ssh root@10.11.115.106
cd /opt/orbina/internal_services
ls -l /opt/orbina/incoming
sudo ops/install/katilim/apply-secure-config-bundle.sh /opt/orbina/incoming/$(ls /opt/orbina/incoming | grep '^banka_single_vm_secure_config_.*\.tar\.gz$' | tail -n 1)
```

## 6) Install VM1 With Docker Hub Sources

Run the installer with:

- role `active`
- the banka inventory
- the Docker Hub image map

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh \
  --role active \
  --inventory /opt/orbina/internal_services/ops/install/katilim/inventory.banka-single-vm.env \
  --image-map /opt/orbina/internal_services/ops/install/katilim/banka-dockerhub-image-map.txt
```

Then bootstrap the active node in single-node fallback mode:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

## 7) Validate VM1

Check the HA health API:

```bash
curl --noproxy '*' -fsS http://127.0.0.1:18081/status
```

Run the built-in smoke test:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/smoke-test-active.sh
```

Check the main containers:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | sed -n '1,40p'
```

Optional direct hostname checks on VM1:

```bash
curl --noproxy '*' -fsS --resolve litellm.banka.local:80:127.0.0.1 http://litellm.banka.local/health
curl --noproxy '*' -fsS --resolve openwebui.banka.local:80:127.0.0.1 http://openwebui.banka.local/
curl --noproxy '*' -fsS --resolve n8n.banka.local:80:127.0.0.1 http://n8n.banka.local/
curl --noproxy '*' -fsS --resolve phoenix.banka.local:80:127.0.0.1 http://phoenix.banka.local/
curl --noproxy '*' -fsS --resolve metabase.banka.local:80:127.0.0.1 http://metabase.banka.local/
```

## 8) What This Does Not Do Yet

- It does not bootstrap `10.11.115.107`.
- It does not enable passive sync timers.
- It does not introduce a load balancer.
- It does not enable Ragflow on banka yet.

What it does prepare now:

- `VM2` stays reserved in the inventory and rendered HA env
- `ha.vm2.env` is rendered now and can be transferred later without changing
  the hostname model
- the temporary banka names can later move from `VM1` to the LB without
  changing per-service public URLs
- the active node already runs under the same service names that the later
  active/passive installation will use

## 9) Later Follow-Up Path

When `10.11.115.107` is ready:

1. keep the same inventory file and hostnames
2. repoint the temporary names to the future LB instead of `10.11.115.106`
3. rerun transfer without `--vm1-only`
4. run the passive-node bootstrap on `VM2`
5. enable sync and failover steps in the original HA runbook

That means this runbook is intentionally:

- single-node right now
- active/passive-prepared by naming, inventory, and HA env layout
- LB-ready later without redoing the whole hostname scheme
