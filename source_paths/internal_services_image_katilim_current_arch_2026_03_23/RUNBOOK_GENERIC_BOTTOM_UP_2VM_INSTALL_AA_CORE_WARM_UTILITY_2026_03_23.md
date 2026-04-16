# Generic Bottom-Up 2-VM Install Runbook

This runbook is intentionally generic.

Replace these placeholders before use:

- `VM1_HOST`
- `VM2_HOST`
- `LOAD_BALANCER_IP`
- registry endpoint values
- all public hostnames
- all DB URLs / DB credentials

Editable source tree:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_aa_core_warm_utility_bottom_up_installer_2026_03_23/bundle_source/internal_services`

Main runtime placeholders:

- `openwebui.example.internal`
- `litellm.example.internal`
- `n8n.example.internal`
- `phoenix.example.internal`
- `metabase.example.internal`
- `db.example.internal`
- `registry.example.internal:5000`

Recommended flow:

1. Update `bundle_source/internal_services/ops/install/katilim/inventory*.env`.
2. Update the service `.env` files under:
   - `litellm`
   - `phoenix`
   - `phoenix-reporting`
   - `metabase`
   - `n8n`
3. Update `bundle_source/internal_services/openweb-ui/nginx.conf` if the final
   hostname map differs.
4. Rebuild the tarball:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_aa_core_warm_utility_bottom_up_installer_2026_03_23
bash refresh-bundle-tar.sh
```

5. Build the installer image if needed:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_aa_core_warm_utility_bottom_up_installer_2026_03_23
bash build-bundle-image.sh
```

6. Extract the bundle onto the target host:

```bash
docker run --rm -v /opt/orbina:/output aliennor/internal-services-aa-core-warm-utility-installer:generic-2026-03-23 /output
```

7. On the active VM:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash install-node.sh --role active
bash bootstrap-vm1-active.sh
```

8. Validate:

```bash
curl -fsS http://127.0.0.1:18081/ready-api
curl -fsS http://127.0.0.1:18081/ready-phoenix
curl -fsS http://127.0.0.1:18081/ready-utility
```

9. On the passive VM:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash install-node.sh --role passive
bash bootstrap-vm2-passive.sh
```

10. Enable sync from the active VM:

```bash
cd /opt/orbina/internal_services/ops/install/katilim
bash enable-vm1-passive-sync.sh
```

11. Test promotion only after the active VM is fully validated:

```bash
cd /opt/orbina/internal_services
bash ops/ha/promote-passive.sh
```

This folder is meant to be specialized later. It is not locked to Katilim dev
or prod values.
