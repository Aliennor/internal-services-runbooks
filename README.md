# Internal Services Runbooks

This repo is the visible runbook library for internal-services work.

Layout:

- `source_paths/` preserves each runbook at its original project-relative path.
- Known hard-coded credential examples are sanitized in this repo copy.
- Patch images may still include runbooks, but runbook-only edits should be reviewed here.
- Do not rebuild or repush deployment images just to update embedded runbook text.

Refresh command from the parent project root:

```bash
rtk proxy sh -c 'rg --files -g "RUNBOOK*.md" | cpio -pdm internal_services_runbooks/source_paths'
```
