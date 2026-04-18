# Banka Start Here (r34)

Date: 2026-04-17

Entrypoint for Banka installs. Pick the target environment and follow one of the two canonical runbooks.

Current published images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-17-r34`
- dev encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`
- prod encrypted config: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7`

## Runtime paths

Dev `10.11.115.108` single-node:

- `RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_17.md`

Prod `10.11.115.106` + `10.11.115.107` active/passive:

- `RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_17.md`

## Supporting references

- DNS, LB, dev cert source paths: `RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md`
- Prod `106 <-> 107` SSH trust: `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md`
- Ragflow export from ZT ARF dev: `RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md`
- Encrypted config image build: `RUNBOOK_BANKA_ENCRYPTED_CONFIG_IMAGE_2026_04_09.md`

## Defaults in r34

- HTTPS DNS URLs default on dev and prod, with direct HTTP IP:port retained for fallback.
- Qdrant disabled by default.
- RAGFlow mandatory, started with `elasticsearch` + `cpu` Compose profiles.
- Readiness/smoke checks advisory (`STRICT_INSTALL_HEALTH_CHECKS=false`); set `true` to make them fatal.
- Active bootstrap pre-cleans leftover containers and resets non-Ragflow DB/app state on every run; Ragflow data is preserved.
- nginx is recreated after the direct app ports are up, using host-published upstreams (no Podman bridge DNS drift).
- LiteLLM `custom_auth.py` and Redis/Langfuse bootstrap fixes are included.
- Operator tools shipped in `ops/repair/`: `banka-apply-ip-port-mode.sh`, `banka-stack-control.sh`, `banka-reset-non-ragflow-app-state.sh`.
