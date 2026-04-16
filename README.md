# Internal Services Runbooks

This repo is the visible runbook library for internal-services work.

Remote: `https://github.com/Aliennor/internal-services-runbooks`

## Public Root Runbooks

The root-level runbooks are convenience copies published only for the runbooks
that need to be easy to reach from the GitHub landing page.

<!-- CURRENT_RUNBOOKS_START -->
Currently published on the repo root:

- [RUNBOOK_BANKA_LITELLM_UI_AUTH_FIX_2026_04_15.md](RUNBOOK_BANKA_LITELLM_UI_AUTH_FIX_2026_04_15.md)

<!-- CURRENT_RUNBOOKS_END -->

Layout:

- `source_paths/` preserves each runbook at its original project-relative path.
- The root-level runbooks are convenience copies for the GitHub landing page.
- Known hard-coded credential examples are sanitized in this repo copy.
- Patch images may still include runbooks, but runbook-only edits should be reviewed here.
- Do not rebuild or repush deployment images just to update embedded runbook text.

Refresh command from the parent project root:

```bash
rtk python3 10_reference/runbooks/internal_services_runbooks/scripts/refresh_runbooks.py
```
