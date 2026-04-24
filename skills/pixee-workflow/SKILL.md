---
name: pixee-workflow
description: "Pixee CLI: list, create, and delete Pixee workflows on a repository. Event kind is selected via a subcommand (schedule / new-scan / pull-request-scan)."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee workflow --help"
---

# pixee workflow

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, `../pixee-auth/SKILL.md` if authentication needs to be configured, and
> `../pixee-repo/SKILL.md` for the `--repo` resolution protocol.

`pixee workflow` manages Pixee workflows for a single repository: list, create, and delete.

## pixee workflow list

```
pixee workflow list --repo <name-or-uuid>
```

- `--repo` is **required**.
- Text output is tab-separated with columns `id`, `event`, `action`, `tool`.
- Pagination is transparent — every workflow on the repo is emitted in one call. There is no
  `--paginate` flag here; `--paginate` only lives on `pixee api`.

## pixee workflow create

`pixee workflow create` does not take an `--event` flag. Event kind is selected via a subcommand:

- `pixee workflow create schedule` — cadence-based.
- `pixee workflow create new-scan` — triggered when a new scan is uploaded on a branch.
- `pixee workflow create pull-request-scan` — triggered on pull-request scans.

All three share the [shared create flags](#shared-create-flags) below; event-specific flags
differ:

**schedule** — `--cadence <daily|weekly>` (required), `--start <iso8601>` (optional start time
with timezone, e.g. `2026-05-01T00:00:00Z`), `--branch <name>` (exact branch name; defaults to
the repo's default branch).

**new-scan** — `--branch <pattern>` (optional; supports a `*` suffix, e.g. `release/*`; defaults
to the repo's default branch).

**pull-request-scan** — `--target-branch <pattern>`, `--source-branch <pattern>` (each optional;
supports `feature/*` style patterns).

### Shared create flags

Every `create` subcommand accepts:

- `--repo <name-or-uuid>` — **required**. Target repository.
- `--tool <tool>` — **required**. Scanner tool (`sonar`, `semgrep`, `codeql`, etc.).
- `--action <kind>` — **required**. `create-patch` or `none`.
- `--severity-labels <csv>`, `--min-severity-score <int>`, `--max-severity-score <int>`,
  `--min-fix-confidence <high|medium|low|no-rating>`, `--finding-limit <int|none>` — optional
  severity filters. **All require `--action create-patch`**; they have no meaning for
  `--action none`.

`--severity-labels` and `--min/max-severity-score` are **mutually exclusive**: pick either
label-based or score-based filtering. The CLI rejects mixed usage at parse time (exit code 1)
before any network call.

## pixee workflow delete

```
pixee workflow delete <workflow-id>
```

`<workflow-id>` is the workflow's UUID (shown in the `id` column of `pixee workflow list`). No
`--repo` flag — deletion targets the workflow ID directly.

## Examples

```bash
# List every workflow on a repo
pixee workflow list --repo pixee/pixee-platform

# Daily scheduled scan, patching high/critical Sonar findings on the default branch
pixee workflow create schedule \
  --cadence daily \
  --repo pixee/pixee-platform \
  --tool sonar --action create-patch --severity-labels high,critical

# Patch every incoming scan on any release branch
pixee workflow create new-scan \
  --branch 'release/*' \
  --repo pixee/pixee-platform \
  --tool semgrep --action create-patch --min-severity-score 7

# Evaluate PR scans from feature/* into main, without creating patches
pixee workflow create pull-request-scan \
  --target-branch main --source-branch 'feature/*' \
  --repo pixee/pixee-platform \
  --tool codeql --action none

# Delete a workflow by UUID
pixee workflow delete a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
```

## Best practices

- For scripts, pass `--repo` as a UUID — stable under rename and never ambiguous. Names are fine
  for humans when the match is unique.
- Use `--output json` (or the `--json` shorthand) when piping `workflow list` into `jq`; the
  default text output drops fields that are not in the four-column set.
- Keep severity filters to one mode (labels *or* scores); the CLI rejects mixed usage before the
  network call, but the failure still spends a CI cycle.
