# Banka Encrypted Config Image

Date: 2026-04-16

Use this after extracting the shared installer bundle.

## Published Image

Current Banka encrypted config images:

- dev `108`: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-dev108-2026-04-17-r7`
- prod `106/107`: `docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-17-r7`

These images contain the live Banka `.env` set and rendered HA inputs in
encrypted form. Use the dev image on `108`; use the prod image on `106/107`.

## What It Restores

It writes these files under `/opt/orbina`:

- `internal_services/shared-postgres/.env`
- `internal_services/langfuse/.env`
- `internal_services/litellm/.env`
- `internal_services/n8n/.env`
- `internal_services/openweb-ui/.env`
- `internal_services/observability/.env`
- `internal_services/qdrant/.env`
- `internal_services/ragflow/docker/.env`
- `incoming/ha.vm1.env`
- `incoming/ha.vm2.env`

The `r7` images default to HTTPS browser URLs, direct HTTP IP:port fallback,
and `ENABLE_QDRANT=false`. `install-node.sh` copies staged certs when present
and otherwise generates self-signed fallback cert files under `/etc/pki/tls`.

## VM Commands

Pull the image:

```bash
podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:<TAG>
```

Extract it:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:<TAG> \
  /output
unset CONFIG_BUNDLE_PASSPHRASE
```

Use `<TAG>` as:

```text
banka-langfuse-dev108-2026-04-17-r7
banka-langfuse-prod-2026-04-17-r7
```

## Apply Order

Use this order on a target VM:

1. Extract the shared install bundle.
2. Extract the encrypted config image.
3. If needed, upload Ragflow volume export to `/opt/orbina/incoming/ragflow_volumes_export`.
4. Continue with the relevant Banka rollout runbook.

## Notes

- `106` is the only target that should be seeded before the first production bootstrap.
- `107` gets the encrypted config too, but not the Ragflow volume export.
- `108` uses the same encrypted config image flow before the dev bootstrap.
- Every active bootstrap now performs a fresh reset for all non-Ragflow app state.
