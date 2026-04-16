# Banka Prod 106/107 Short Runbook Superseded

Date: 2026-04-15

This short runbook is superseded. Use the single full prod runbook instead:

```text
/opt/orbina/internal_services/RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md
```

It covers the same banka production machines:

- VM1 active first: `10.11.115.106`
- VM2 passive later: `10.11.115.107`
- no load balancer at first
- HTTP first
- Podman runtime
- all installer pulls from `docker.io/aliennor/...`
- Podman pulls use `--tls-verify=false`

Full runbook:

```text
/opt/orbina/internal_services/RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md
```

Banka 106/107 SSH trust runbook:

```text
/opt/orbina/internal_services/RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md
```

## Published Packs

Installer pack:

```text
docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
```

Prod encrypted config pack:

```text
docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2
```

The prod config pack was not regenerated for this handoff. Rebuilding it creates new generated secrets and should only be done intentionally with a known prod passphrase.

## VM1 106 First Commands

Run on `10.11.115.106`:

```bash
set -euo pipefail
mkdir -p /opt/orbina

if [ -d /opt/orbina/internal_services/ops/install/katilim/certs/generated ]; then
  TS=$(date +%Y%m%d_%H%M%S)
  mkdir -p "/root/orbina-generated-certs-backup_$TS"
  cp -a /opt/orbina/internal_services/ops/install/katilim/certs/generated \
    "/root/orbina-generated-certs-backup_$TS/"
fi

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output

find /opt/orbina -name '._*' -delete
find /opt/orbina -name '.DS_Store' -delete

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE

grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|CONTAINER_ENGINE|CONTAINER_TLS_VERIFY)=' \
  /opt/orbina/incoming/ha.vm1.env || true
```

If the existing `r2` prod config pack does not print `CONTAINER_ENGINE` or
`CONTAINER_TLS_VERIFY`, continue. The `r19` installer scripts default to
`podman` and `CONTAINER_TLS_VERIFY=false`.

Then follow the full runbook section for:

```text
Transfer Ragflow Export To VM1 106
Install And Bootstrap VM1 Active
Validate VM1 Active
```

Do not upload the Ragflow export to `10.11.115.107`.

## VM2 107 Later Commands

Run on `10.11.115.107` only after VM1 is healthy and you are ready to prepare passive:

```bash
set -euo pipefail
mkdir -p /opt/orbina

if [ -d /opt/orbina/internal_services/ops/install/katilim/certs/generated ]; then
  TS=$(date +%Y%m%d_%H%M%S)
  mkdir -p "/root/orbina-generated-certs-backup_$TS"
  cp -a /opt/orbina/internal_services/ops/install/katilim/certs/generated \
    "/root/orbina-generated-certs-backup_$TS/"
fi

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21
podman run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-15-r21 \
  /output

find /opt/orbina -name '._*' -delete
find /opt/orbina -name '.DS_Store' -delete

podman pull --tls-verify=false docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
podman run --rm \
  -e CONFIG_BUNDLE_MODE=force \
  -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" \
  -v /opt/orbina:/output \
  docker.io/aliennor/internal-services-katilim-config-encrypted:banka-langfuse-prod-2026-04-13-r2 \
  /output
unset CONFIG_BUNDLE_PASSPHRASE

grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|CONTAINER_ENGINE|CONTAINER_TLS_VERIFY)=' \
  /opt/orbina/incoming/ha.vm2.env || true
```

If the existing `r2` prod config pack does not print `CONTAINER_ENGINE` or
`CONTAINER_TLS_VERIFY`, continue. The `r16` installer scripts default to
`podman` and `CONTAINER_TLS_VERIFY=false`.

Then follow the full runbook section for:

```text
Install And Bootstrap VM2 Passive
Enable Sync On VM1
Validate Active/Passive
```

## Stop Conditions

Stop and do not bootstrap if any of these happen:

- `podman pull --tls-verify=false docker.io/aliennor/...` fails with a network or manifest error
- the config image passphrase fails
- `/opt/orbina/incoming/ha.vm1.env` or `/opt/orbina/incoming/ha.vm2.env` is missing
- VM1 Ragflow export is missing `SHA256SUMS.txt`
- VM2 is being prepared before VM1 is healthy
