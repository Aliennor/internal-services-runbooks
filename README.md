# Internal Services Runbooks

This repo is the visible runbook library for internal-services work.

Remote: `https://github.com/Aliennor/internal-services-runbooks`

## Public Root Runbooks

The root-level runbooks are convenience copies published only for the runbooks
that need to be easy to reach from the GitHub landing page.

Public rule:

- publish the current Banka operator runbooks we are actively going to execute
- keep one-off fix, reset, patch, and workaround runbooks private
- keep the LiteLLM UI auth fix runbook out of this public repo

<!-- CURRENT_RUNBOOKS_START -->
Currently published on the repo root:

- [RUNBOOK_BANKA_START_HERE_2026_04_09.md](RUNBOOK_BANKA_START_HERE_2026_04_09.md)
- [RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_09.md](RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_2026_04_09.md)
- [RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md](RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_2026_04_13.md)
- [RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md](RUNBOOK_BANKA_DNS_TLS_CUTOVER_2026_04_09.md)
- [RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md](RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md)
- [RUNBOOK_BANKA_ENCRYPTED_CONFIG_IMAGE_2026_04_09.md](RUNBOOK_BANKA_ENCRYPTED_CONFIG_IMAGE_2026_04_09.md)
- [RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md](RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_2026_04_09.md)
- [RUNBOOK_BANKA_RAGFLOW_PROFILE_QDRANT_NGINX_RECOVERY_2026_04_17.md](RUNBOOK_BANKA_RAGFLOW_PROFILE_QDRANT_NGINX_RECOVERY_2026_04_17.md)
- [RUNBOOK_BANKA_DEV108_HTTPS_LITELLM_CUTOVER_2026_04_17.md](RUNBOOK_BANKA_DEV108_HTTPS_LITELLM_CUTOVER_2026_04_17.md)
- [RUNBOOK_BANKA_DEV108_R33_POST_INSTALL_TRIAGE_2026_04_17.md](RUNBOOK_BANKA_DEV108_R33_POST_INSTALL_TRIAGE_2026_04_17.md)

<!-- CURRENT_RUNBOOKS_END -->

## Quick Checks

- [Banka dev108 browser connectivity](checks/CHECK_BANKA_DEV108_BROWSER_CONNECTIVITY_2026_04_17.md)

Layout:

- `source_paths/` preserves each runbook at its original project-relative path.
- The root-level runbooks are the current public operator set for GitHub.
- The mirrored `source_paths/` tree is filtered to the same public-safe runbook set.
- Known hard-coded credential examples are sanitized in this repo copy.
- Patch images may still include runbooks, but runbook-only edits should be reviewed here.
- Do not rebuild or repush deployment images just to update embedded runbook text.

Refresh command from the parent project root:

```bash
rtk python3 10_reference/runbooks/internal_services_runbooks/scripts/refresh_runbooks.py
```
