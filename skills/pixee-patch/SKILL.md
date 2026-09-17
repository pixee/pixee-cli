---
name: pixee-patch
description: "List and view Pixee patches created from fix results, filterable by scan, finding, repository, state, and creation date."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee patch --help"
---

# pixee patch

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-auth/SKILL.md` if authentication needs to be configured. See
> `../pixee-scan/SKILL.md` for the scan UUIDs `--scan` filters on and `../pixee-finding/SKILL.md`
> for the finding IDs `--finding` filters on.

`pixee patch` lists and views patches: the pull requests (or other fix artifacts) the Pixee
platform generates from fix results after an analysis runs. A patch is a downstream artifact of
an analysis — it does not create or apply fixes itself; `pixee scan analyze` and workflows with
`--action create-patch` are what generate the patches this skill reads.

## pixee patch list

```
pixee patch list [filter flags...]
```

All flags are optional. With none, every patch visible to the token is returned. Pagination is
transparent — the CLI walks every page in one call.

Text output is tab-separated with columns `id`, `state`, `type`, `pr_number`, `branch_name`,
`merge_state`, `html_url`.

Filter flags:

- `--scan <scan-id>` — restrict to patches generated from a single scan UUID. See `pixee-scan`
  for how to obtain scan IDs.
- `--finding <finding-id>` — restrict to patches generated from a single finding. **Requires
  `--scan`** — a finding ID alone does not disambiguate across scans.
- `--repo <repository-id>` — restrict to a single repository. This flag takes a **UUID only**;
  unlike `pixee scan list --repo` and `pixee workflow list --repo`, it does not resolve names via
  the `pixee-repo` protocol.
- `--created-after <iso8601>` / `--created-before <iso8601>` — bound the patch's creation time.
  Both take an ISO-8601 date-time with timezone, e.g. `2026-05-01T00:00:00Z`.
- `--state <state>` — **repeatable**. One of `completed-failed`,
  `completed-fixes-overcome-by-events`, `completed-success`, `in-progress`. Multiple `--state`
  flags OR together.
- `--sort-by <order>` — `created-asc` or `created-desc`.

## pixee patch view

```
pixee patch view <patch-id>
```

Fetch a single patch by ID. `<patch-id>` is the value shown in the `id` column of
`pixee patch list`.

Default text mode emits a sectioned `Key: value` block. Use `--output json` (or `--json`) for the
full HAL body. A non-existent ID returns the standard not-found error and exits 3.

## Examples

```bash
# Every patch visible to the token
pixee patch list

# Successful patches on a single scan
pixee patch list --scan e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --state completed-success

# Patches generated from one finding within a scan
pixee patch list --scan e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --finding AZ4JOwsipJDH8099SpHt

# Patches created in the last week, newest first
pixee patch list --created-after "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --sort-by created-desc

# Failed or overcome-by-events patches, for triage
pixee patch list --state completed-failed --state completed-fixes-overcome-by-events

# Inspect one patch as JSON and pull the PR URL
pixee patch view f3a1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --json | jq -r '.html_url'

# Walk to a patch's HAL self link rather than re-listing
href=$(pixee patch list --json | jq -r '.[0]._links.self.href')
pixee api "$href"
```

## Best practices

- Filter by `--scan` (and `--finding`, which requires it) whenever the agent already knows the
  scan it triggered a patch from — it's the narrowest, cheapest filter available.
- `--repo` here takes a UUID only. If the agent only has a repository name, resolve it first with
  `pixee repo list --name <pattern>` (see `pixee-repo`) before filtering patches.
- Use `--state` to separate patches worth reviewing (`completed-success`) from ones that need
  attention (`completed-failed`, `completed-fixes-overcome-by-events`) or are still running
  (`in-progress`).
- Prefer `pixee patch list --json` over N calls to `pixee patch view` when scanning many patches
  for a single field (e.g., `html_url`); `list` and `view` return the same per-patch shape.
