# Banka Start Here

Date: 2026-04-16

Use this file only as the entrypoint. The canonical runtime paths are the Banka
dev `108` runbook and the Banka prod `106/107` runbook below.

Current published images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r32`
- dev encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`
- prod encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7`

## 1) Reuse Or Extract The Installer Bundle

If `/opt/orbina/internal_services` already exists on the Banka machine you are
working on, keep using that extracted tree and continue with the canonical
runtime runbook.

If it is missing, extract the current installer bundle:

```bash
mkdir -p /opt/orbina
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r32
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r32 \
  /output
```

## 2) Pick The Runtime Path

Dev `108` single-node runtime:

- `RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_09.md`

Prod `106/107` active/passive runtime:

- `RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md`

Use only those two runbooks for the live runtime path.

## 3) Separate References

DNS, LB, prod TLS, and dev cert source paths:

- `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`

Prod `106 <-> 107` SSH trust:

- `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md`

ZT ARF dev Ragflow export:

- `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`

## 4) Working Rules

- Dev `108` and prod `106/107` now default to HTTPS browser URLs and the full nginx config on the nodes.
- Direct HTTP IP:port access remains exposed on dev `108` and prod `106/107` for fallback and debugging.
- Qdrant is disabled by default; ignore qdrant health unless an operator explicitly enables it.
- RAGFlow is mandatory in this Banka stack and starts with the `elasticsearch` and `cpu` Compose profiles.
- Installer health checks are advisory by default: RAGFlow waits up to 60 seconds, HA `/ready` uses short curl timeouts, and smoke failures print warnings unless `STRICT_INSTALL_HEALTH_CHECKS=true`.
- For production, the intended final network shape is:
  - `HTTPS client -> LB -> HTTP :80 on 106/107`
- Dev should stage the real node cert at `/tmp/cert.pem` and `/tmp/private.key`; prod may keep using LB TLS with node-local self-signed fallback on `443`.
- Every active bootstrap now performs a fresh reset for all non-Ragflow app state, then recreates the non-Ragflow databases and services from zero.
- `install-node.sh` and the bootstrap scripts now pre-clean old containers and failed compose leftovers before starting again. This cleanup keeps Ragflow export files and `/tmp` cert/key files.
- The active bootstrap also recreates `nginx-proxy` near the end so hostname upstreams resolve to the final container IPs after LiteLLM/Langfuse/N8N settle.
- `observability-cadvisor` may still complain about Docker/containerd discovery on Podman hosts; ignore that for Banka readiness unless you are explicitly debugging observability.
- Do not add CSR generation back into the runtime install path.
- Older Banka runbooks with overlapping install steps are superseded and kept only for traceability.
