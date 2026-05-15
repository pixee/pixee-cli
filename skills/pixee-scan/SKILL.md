---
name: pixee-scan
description: "List, view, analyze, and delete Pixee scans with filters for repository, branch, detector tool, and analysis state."
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
> `../pixee-repo/SKILL.md` for the `--repo` resolution protocol. See
> `../pixee-analysis/SKILL.md` for the analysis UUID `pixee scan analyze` returns.

`pixee scan` manages scans imported into the Pixee platform: list, view a single scan by UUID,
kick off an analysis on a scan, and delete a scan. A scan is the raw output of one detector tool
(`sonar`, `appscan`, `dependabot`, `datadog_sast`, `semgrep`, `codeql`, etc.) imported on a
specific branch and commit; analyses, findings, and downstream patches all attach back to a scan.
Scans expire roughly seven days after import, and fetching an expired UUID returns a not-found
error.

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

## pixee scan &lt;scan-id&gt;

```
pixee scan <scan-id>
```

Fetch a single scan by UUID. The view-by-id form is a **positional argument on the top-level
`pixee scan` command** — there is no `pixee scan get` or `pixee scan view` subcommand. `<scan-id>`
is the value shown in the first column of `pixee scan list`.

Text output is one tab-separated row with the same columns as `list`. JSON output is the full
HAL representation: `_links` to the scan's `analyses`, `findings`, `repository`, and `scale`,
plus the body fields `id`, `detector`, `sha`, `imported_at`, `branch` (omitted when blank), and
`expires_at`. A non-existent or expired UUID returns the standard not-found error.

## pixee scan analyze

```
pixee scan analyze <scan-id> [--finding <finding-id>...] [--watch] [--interval <seconds>]
```

Start an analysis on a scan. On success the CLI prints `Started analysis <analysis-id> on scan
<scan-id>` and exits 0. The analysis runs asynchronously on the server — capture the UUID from
stdout and hand it to `pixee analysis view --watch` (see `pixee-analysis`) to poll until terminal
state.

Flags:

- `--finding <finding-id>` — **repeatable**. Scope the analysis to one or more specific findings.
  When omitted, every finding in the scan is analyzed (the common case after an import).
- `--watch` — after starting the analysis, poll until it reaches a terminal state. Equivalent
  to chaining the start call into `pixee analysis view --watch` on the returned UUID; reach for
  it when the agent's next step depends on completion.
- `--interval <seconds>` — polling cadence with `--watch` (default 5). Has no effect without
  `--watch`.

A scan that's not analyzable (e.g., already deleted, or a scan kind the server cannot run
analyses on) returns a 422-shaped problem document and exits non-zero — `pixee-shared` documents
the rendering.

## pixee scan delete

```
pixee scan delete <scan-id>
```

Delete a scan by UUID. On success the CLI prints `Deleted scan <id>` and exits 0; a missing scan
exits 3. There is no `--repo` flag — deletion targets the scan ID directly — and no client-side
confirmation prompt, matching `pixee workflow delete` and `pixee repo delete`.

## Examples

```bash
# Every scan visible to the token (paginated transparently)
pixee scan list

# Cross-repo OR query, JSON piped to jq for downstream processing
pixee scan list --repo pixee/pixee-platform --repo analysis-service --json \
  | jq '.[] | {id, detector, branch, repo: ._links.repository.title}'

# Sonar scans on main that have not been analyzed yet
pixee scan list --branch main --tool sonar --has-analysis false

# Fetch one scan as JSON (positional, not "pixee scan get")
pixee scan e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --json

# Walk from a scan to its findings via HAL — never hardcode the path
scan_id=$(pixee scan list --repo pixee/pixee-platform --branch main --json | jq -r '.[0].id')
findings_href=$(pixee scan "$scan_id" --json | jq -r '._links.findings.href')
pixee api "$findings_href" --paginate

# Kick off an analysis on every finding in a scan and block until it finishes
pixee scan analyze e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --watch

# Re-analyze just two findings in an existing scan, with a longer poll interval
pixee scan analyze e5e1ebe6-93f3-4426-a98a-6dc6af41b468 \
  --finding AZ4JOwsipJDH8099SpHt --finding AZ4JOwsipJDH8099TqIu \
  --watch --interval 15

# Capture the analysis UUID and watch it separately (e.g., to detach into another task)
analysis_id=$(pixee scan analyze e5e1ebe6-93f3-4426-a98a-6dc6af41b468 \
  | sed -n 's/^Started analysis \([^ ]*\) on scan .*/\1/p')
pixee analysis view "$analysis_id" --watch

# Delete a scan by UUID
pixee scan delete e5e1ebe6-93f3-4426-a98a-6dc6af41b468
```

## Best practices

- Filter aggressively. The unfiltered scan list grows with every imported scan; combining
  `--repo`, `--branch`, and `--tool` keeps payloads small enough to reason about.
- Pass UUIDs in scripts for both `--repo` and the `<id>` argument; names work for humans but
  carry the rename and multi-match risks documented in `pixee-repo`.
- For full per-scan detail (HAL links to analyses, findings, repository, scale), use
  `pixee scan <id> --json` (positional, not `pixee scan get <id>`). The `list` JSON contains the
  same per-element shape, so a single `list --json` call often replaces a list-then-N-views
  pattern.
- To traverse from a scan to its analyses, findings, or owning repository, follow the `_links`
  returned by `pixee scan <id> --json` with `pixee api <href>` rather than hardcoding paths. See
  `pixee-api` for HAL conventions and `--paginate`.
- Treat scan UUIDs as short-lived: cache them only as long as the active workflow needs them,
  and expect lookups to start failing once a scan ages past its `expires_at`.
- Prefer `pixee scan analyze --watch` over a hand-rolled poll loop. The flag chains the start
  call into the same poll-and-narrate behavior `pixee analysis view --watch` provides and
  preserves the start-time analysis UUID on stdout so scripts can still reuse it.
- Scoping `pixee scan analyze` with `--finding` is the right answer when re-running just a
  subset of findings after a triage adjustment. Omit `--finding` for the initial analysis pass
  on a freshly imported scan.
