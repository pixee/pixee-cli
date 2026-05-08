---
name: pixee-scan
description: "List, fetch, and filter Pixee scans by repository, branch, detector tool, analysis state, and presence of analyses."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee scan --help"
---

# pixee scan

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, `../pixee-auth/SKILL.md` if authentication needs to be configured, and
> `../pixee-repo/SKILL.md` for the `--repo` resolution protocol.

`pixee scan` lists scans imported into the Pixee platform and fetches a single scan by UUID. A
scan is the raw output of one detector tool (`sonar`, `appscan`, `dependabot`, `datadog_sast`,
`semgrep`, `codeql`, etc.) imported on a specific branch and commit; analyses, findings, and
downstream patches all attach back to a scan. Scans expire roughly seven days after import, and
fetching an expired UUID returns a not-found error.

## pixee scan list

```
pixee scan list [filter flags...]
```

All flags are optional. With none, every scan visible to the token is returned. Pagination is
transparent: the CLI walks every page in one call. There is no `--paginate` flag here;
`--paginate` only lives on `pixee api`.

Text output is tab-separated with columns `id`, `detector`, `branch`, `sha`, `imported_at`. The
`branch` column is empty for detectors that import scans without a branch context (e.g.,
`appscan`); JSON output omits the `branch` field entirely in that case rather than emitting an
empty string.

Filter flags:

- `--repo <name-or-uuid>` — **repeatable**. Restrict to one or more repositories. Names resolve
  via the protocol documented in `pixee-repo`. Multiple `--repo` flags OR together; a scan is
  returned if it matches any of them.
- `--branch <name>` — exact branch name (case-sensitive). Works with or without `--repo`.
- `--tool <name>` — **repeatable**. Filter by detector. Multiple `--tool` flags OR together.
- `--analysis-state <state>` — one of `completed`, `in-progress`, `not-analyzed`. Filters by the
  state of the scan's downstream analysis pipeline, not the scan import itself.
- `--has-analysis <true|false>` — narrow to scans that have at least one analysis associated
  (`true`) or none (`false`).

`--analysis-state not-analyzed` and `--has-analysis false` overlap but are not interchangeable:
`--has-analysis` filters on existence, while `--analysis-state` filters on pipeline state. Pick
whichever matches the question being asked.

## pixee scan get

```
pixee scan get <id>
```

Fetch a single scan. `<id>` is the scan's UUID, surfaced in the first column of `pixee scan
list`. Text output is one tab-separated row with the same columns as `list`. JSON output is the
full HAL representation: `_links` to the scan's `analyses`, `findings`, `repository`, and
`scale`, plus the body fields `id`, `detector`, `sha`, `imported_at`, `branch` (omitted when
blank), and `expires_at`. A non-existent or expired UUID returns the standard not-found error.

## Examples

```bash
# Every scan visible to the token (paginated transparently)
pixee scan list

# Cross-repo OR query, JSON piped to jq for downstream processing
pixee scan list --repo pixee/pixee-platform --repo analysis-service --json \
  | jq '.[] | {id, detector, branch, repo: ._links.repository.title}'

# Sonar scans on main that have not been analyzed yet
pixee scan list --branch main --tool sonar --has-analysis false

# Fetch one scan as JSON
pixee scan get e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --json

# Walk from a scan to its findings via HAL — never hardcode the path
scan_id=$(pixee scan list --repo pixee/pixee-platform --branch main --json | jq -r '.[0].id')
findings_href=$(pixee scan get "$scan_id" --json | jq -r '._links.findings.href')
pixee api "$findings_href" --paginate
```

## Best practices

- Filter aggressively. The unfiltered scan list grows with every imported scan; combining
  `--repo`, `--branch`, and `--tool` keeps payloads small enough to reason about.
- Pass UUIDs in scripts for both `--repo` and the `<id>` argument; names work for humans but
  carry the rename and multi-match risks documented in `pixee-repo`.
- For full per-scan detail (HAL links to analyses, findings, repository, scale), use
  `pixee scan get <id> --json`. The `list` JSON contains the same per-element shape, so a single
  `list --json` call often replaces a list-then-N-gets pattern.
- To traverse from a scan to its analyses, findings, or owning repository, follow the `_links`
  returned by `scan get --json` with `pixee api <href>` rather than hardcoding paths. See
  `pixee-api` for HAL conventions and `--paginate`.
- Treat scan UUIDs as short-lived: cache them only as long as the active workflow needs them,
  and expect lookups to start failing once a scan ages past its `expires_at`.
