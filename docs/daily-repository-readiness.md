# Daily repository readiness audit

## What it does

The scheduled workflow inventories repositories owned by `Garrettc123`, measures basic governance completeness, and creates or updates one deduplicated audit issue in `systems-master-hub`.

It is intentionally read-only outside the hub repository. It does not modify other repositories, merge PRs, deploy services, rotate secrets, send outreach, or operate payment or crypto accounts.

## Token setup

`github.token` can read and create issues in the hub repository. To inventory private repositories reliably, create a fine-grained GitHub token with read-only metadata access to the selected repositories and issue-write access only to `systems-master-hub`, then save it as `GARCAR_AUDIT_TOKEN` in `systems-master-hub` Actions secrets.

## Safe expansion path

After reviewing several reports, add checks incrementally: security alerts, stale branches, CI state, dependency updates, or contract conformance. Keep remediation separate: create reviewed work items or PRs rather than permitting direct autonomous production changes.
