# Banka Start Here (r36)

Date: 2026-04-18

Entrypoint for Banka installs. Pick the target environment and follow one of the two canonical runbooks.

Current published images:

- installer: `docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r36`
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

## Defaults in r36

- HTTPS DNS URLs default on dev and prod, with direct HTTP IP:port retained for fallback.
- Qdrant disabled by default.
- RAGFlow mandatory, started with `elasticsearch` + `cpu` Compose profiles.
- Readiness/smoke checks advisory (`STRICT_INSTALL_HEALTH_CHECKS=false`); set `true` to make them fatal.
- Active bootstrap pre-cleans leftover containers and resets non-Ragflow DB/app state on every run; Ragflow data is preserved.
- nginx is recreated after the direct app ports are up, using host-published upstreams (no Podman bridge DNS drift).
- LiteLLM `custom_auth.py` and Redis/Langfuse bootstrap fixes are included.
- Langfuse first-run admin bootstrap wired in: `LANGFUSE_INIT_*` values are seeded from inventory (default `admin@banka.local` / `ChangeMeBanka2026!`) so the first login works out of the box.
- Langfuse startup ordering: `langfuse-web` depends only on `minio`, `clickhouse`, `redis` (Postgres is external). `langfuse-web` is the only service that runs the Prisma migrations, so it must not be gated on `langfuse-worker`; the transient "ClickHouse traces table does not exist" log lines from `langfuse-web` during the first ~60s are cosmetic and resolve once `langfuse-worker` finishes the ClickHouse migrations. The `langfuse-worker` healthcheck exists for diagnostics only and is not used as a dependency condition.
- Operator tools shipped in `ops/repair/`: `banka-apply-ip-port-mode.sh`, `banka-stack-control.sh`, `banka-reset-non-ragflow-app-state.sh`.
