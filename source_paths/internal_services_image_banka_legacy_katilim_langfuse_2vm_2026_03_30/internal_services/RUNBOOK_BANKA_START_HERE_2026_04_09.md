# Banka Start Here

Date: 2026-04-09

Use this order. For dev `10.11.115.108`, use the full dev runbook directly;
it now includes Podman setup, Ragflow export, config extraction, install, and
validation in one file.

## 1) Pull The Installer Bundle

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 /output
```

This extracts:

```text
/opt/orbina/internal_services
```

## 2) Pick Your Runbook

Dev single-file full path on `10.11.115.108`:
- `RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_09.md`

This is the preferred dev runbook. Do not separately follow the older dev,
Podman, or Ragflow-only runbooks unless debugging a specific failed section.

Production full path for `106` active and `107` passive later:
- `RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md`

This is the single canonical prod runbook. Do not combine it with the older
short, single-VM, or LB cutover runbooks unless debugging a specific failed
section.

DNS, LB, and TLS later:
- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`

CSR generation for dev/prod certificates:
- `RUNBOOK_BANKA_CSR_GENERATION_DEV_AND_PROD_2026_04_13.md`

## 3) First Production Target

If you are starting the real rollout now, begin with:
- `10.11.115.106`
- `RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md`

Do not start with `107`.
