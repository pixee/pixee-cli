---
name: pixee-scan
description: "List, view, analyze, create, and delete Pixee scans with filters for repository, branch, detector tool, and analysis state."
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
> `../pixee-analysis/SKILL.md` for the analysis UUID `pixee scan analyze` returns, and
> `../pixee-integration/SKILL.md` for the `--integration-id` discovery flow used by `create`.

`pixee scan` manages scans imported into the Pixee platform: list, view, kick off an analysis,
upload a new scan, and delete. A scan is the raw output of one detector tool (`sonar`, `appscan`,
`dependabot`, `datadog_sast`, `semgrep`, `codeql`, etc.) imported on a specific branch and
commit; analyses, findings, and downstream patches all attach back to a scan. Most production
scans land via the platform's CI integrations; `pixee scan create` is the manual import path for
bulk-loading historical scans, smoke-testing detector formats, or one-shot uploads. Scans expire
roughly seven days after import, and fetching an expired UUID returns a not-found error.

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

## pixee scan view

```
pixee scan view <scan-id>
```

Fetch a single scan by UUID. `<scan-id>` is the value shown in the first column of
`pixee scan list`.

Default text mode prints a sectioned `Key: value` block of the scan's headline fields —
`Id`, `Detector`, `Branch`, `Sha`, `Imported at`, `Expires at` — colon-separated, one field per
line. The `Branch` line is omitted for detectors that import scans without a branch context
(e.g., `appscan`) rather than emitting an empty value. Use `--output json` (or `--json`) for the
full HAL representation: `_links` to the scan's `analyses`, `findings`, `repository`, and
`scale`, plus the body fields `id`, `detector`, `sha`, `imported_at`, `branch` (omitted when
blank), and `expires_at`. A non-existent or expired UUID returns the standard not-found error
and exits 3.

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

## pixee scan create

```
pixee scan create <repository> --tool <tool> [--file <path>...] [scan metadata flags...]
```

Upload a scan to a repository. `<repository>` is name-or-UUID resolved via the protocol in
`pixee-repo`. On success the CLI prints `Created scan <scan-id>` and exits 0; the upload is
multipart, so each `--file` is attached to the same POST.

**Not idempotent.** The platform creates a new scan on every successful POST. If a call fails
after the upload may have reached the server (timeout, dropped connection), run
`pixee scan list --repo <id>` to check for a freshly-imported scan before retrying.

Flags:

- `--tool <tool>` — **required**. Scanner tool that produced the scan. One of `codeql`, `sonar`,
  `semgrep`, `polaris_sast`, `polaris_sca`, `appscan`, `defectdojo`, `datadog_sast`,
  `dependabot`, `contrast`, `gitlab_sast`, `gitlab_dependency_scanning`, `snyk`, `checkmarx`,
  `veracode`, `fortify`, `arnica_sast`. The CLI validates against the enum before sending.
- `--file <path>` — **repeatable**. Attach a scan output file (SARIF, SCA report, etc.) to the
  multipart upload. Most detector tools require at least one file; integration-driven tools
  whose data the platform pulls from the integration directly (e.g., sonar, snyk) can omit it.
- `--sha <sha>` — commit SHA scanned (40 hex chars).
- `--branch <name>` — branch scanned.
- `--integration-id <id>` — integration identifier to attribute the upload to. Discover valid
  values with `pixee integration list` (see `pixee-integration`).
- `--workflow-execution-policy <policy>` — `execute` (default — fire matching workflows on the
  new scan) or `prevent-execution` (import the scan but skip any matching workflows). Use
  `prevent-execution` when bulk-loading historical scans so a backfill doesn't fan out a wave
  of patches.
- `--pr-number <int>` — pull request number for PR-scoped scans.
- `--gitlab-pipeline-id <int>` — GitLab pipeline id when the scan came from a GitLab CI run.
- `--base-branch <name>` / `--base-sha <sha>` — base branch and base commit for a PR-scoped
  scan. `--base-sha` requires `--base-branch`.

Pair with `pixee scan analyze` (or `--watch` it directly) to kick off triage/fix/sca immediately
after the upload — see the chained example below.

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

# Fetch one scan as JSON
pixee scan view e5e1ebe6-93f3-4426-a98a-6dc6af41b468 --json

# Walk from a scan to its findings via HAL — never hardcode the path
scan_id=$(pixee scan list --repo pixee/pixee-platform --branch main --json | jq -r '.[0].id')
findings_href=$(pixee scan view "$scan_id" --json | jq -r '._links.findings.href')
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

# Import a CodeQL SARIF as a new scan on pixee-platform, then analyze it to completion
scan_id=$(pixee scan create pixee/pixee-platform \
  --tool codeql --file ./codeql.sarif.json \
  --branch main --sha "$(git rev-parse HEAD)" \
  | sed -n 's/^Created scan \(.*\)$/\1/p')
pixee scan analyze "$scan_id" --watch

# Bulk-load a historical Sonar scan without firing matching workflows
pixee scan create pixee/pixee-platform \
  --tool sonar --integration-id sonar-default \
  --branch main --sha abcdef1234567890abcdef1234567890abcdef12 \
  --workflow-execution-policy prevent-execution

# Upload a PR-scoped scan from a GitLab CI job
pixee scan create pixee/pixee-platform \
  --tool gitlab_sast --file ./gl-sast-report.json \
  --branch "feature/sso" --sha "$CI_COMMIT_SHA" \
  --base-branch main --base-sha "$CI_MERGE_REQUEST_DIFF_BASE_SHA" \
  --pr-number "$CI_MERGE_REQUEST_IID" \
  --gitlab-pipeline-id "$CI_PIPELINE_ID"
```

## Best practices

- Filter aggressively. The unfiltered scan list grows with every imported scan; combining
  `--repo`, `--branch`, and `--tool` keeps payloads small enough to reason about.
- Pass UUIDs in scripts for both `--repo` and the `<id>` argument; names work for humans but
  carry the rename and multi-match risks documented in `pixee-repo`.
- For full per-scan detail (HAL links to analyses, findings, repository, scale), use
  `pixee scan view <id> --json`. The `list` JSON contains the same per-element shape, so a single
  `list --json` call often replaces a list-then-N-views pattern.
- To traverse from a scan to its analyses, findings, or owning repository, follow the `_links`
  returned by `pixee scan view <id> --json` with `pixee api <href>` rather than hardcoding paths.
  See `pixee-api` for HAL conventions and `--paginate`.
- Treat scan UUIDs as short-lived: cache them only as long as the active workflow needs them,
  and expect lookups to start failing once a scan ages past its `expires_at`.
- Prefer `pixee scan analyze --watch` over a hand-rolled poll loop. The flag chains the start
  call into the same poll-and-narrate behavior `pixee analysis view --watch` provides and
  preserves the start-time analysis UUID on stdout so scripts can still reuse it.
- Scoping `pixee scan analyze` with `--finding` is the right answer when re-running just a
  subset of findings after a triage adjustment. Omit `--finding` for the initial analysis pass
  on a freshly imported scan.
- `pixee scan create` is not idempotent, so a network-layer retry can duplicate a scan. When a
  call fails ambiguously (timeout, dropped connection), reach for `pixee scan list --repo <id>`
  to look for a freshly-imported scan before retrying.
- For backfill imports (loading historical scans into a fresh repo), pass
  `--workflow-execution-policy prevent-execution` to avoid a wave of patch PRs the team did not
  expect. Re-run analysis on individual scans later via `pixee scan analyze` once you're ready.
- The `--integration-id` flag and `pixee integration list` together let an agent attribute an
  upload to a known integration without hand-rolling the id; reach for the discovery flow
  before falling back to `pixee api /api/v1/integrations`.
