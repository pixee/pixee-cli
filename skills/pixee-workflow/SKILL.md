---
name: pixee-workflow
description: "List, create, update, run, and delete Pixee workflows on a repository with partial-update semantics across event kinds."
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

`pixee workflow` manages Pixee workflows for a single repository: list, create, update, run, and
delete.

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

## pixee workflow update

`pixee workflow update` is a **partial update**: only the flags you pass are changed; everything
else is left as-is on the server. Like `create`, the event kind is selected via subcommand, and
the workflow ID is a positional argument:

- `pixee workflow update schedule <workflow-id>` — for cadence-based workflows.
- `pixee workflow update new-scan <workflow-id>` — for new-scan workflows.
- `pixee workflow update pull-request-scan <workflow-id>` — for PR-scan workflows.

The subcommand must match the workflow's existing event kind; you cannot retype a `schedule`
workflow into a `new-scan` via update. There is no `--repo` flag — the workflow UUID
disambiguates by itself.

Event-specific flags mirror `create`:

- **schedule** — `--cadence`, `--branch`, `--start`.
- **new-scan** — `--branch`.
- **pull-request-scan** — `--target-branch`, `--source-branch`.

### Shared update flags

Every `update` subcommand also accepts:

- `--name <name>` — rename the workflow.
- `--enabled` / `--disabled` — toggle the workflow on or off. **Mutually exclusive**; pass at
  most one.
- `--action <kind>`, `--severity-labels`, `--min-severity-score`, `--max-severity-score`,
  `--min-fix-confidence`, `--finding-limit` — same semantics and same `--action create-patch`
  requirement as on `create`. The `--severity-labels` vs `--min/max-severity-score` mutual
  exclusion still applies.
- `--unset <field>` — repeatable. **Clears** a nullable field back to `null` instead of setting
  it; use this to drop a filter rather than change it. Per-subcommand fields:
  - schedule: `start`, `severity-labels`, `min-severity-score`, `max-severity-score`,
    `min-fix-confidence`, `finding-limit`.
  - new-scan: `severity-labels`, `min-severity-score`, `max-severity-score`,
    `min-fix-confidence`, `finding-limit`.
  - pull-request-scan: `target-branch`, `source-branch`, `severity-labels`,
    `min-severity-score`, `max-severity-score`, `min-fix-confidence`, `finding-limit`.

  Action-scoped fields (`severity-labels`, `min/max-severity-score`, `min-fix-confidence`,
  `finding-limit`) require `--action create-patch` on the same call, even when only unsetting.

## pixee workflow run

```
pixee workflow run <workflow-id>
```

Trigger a scheduled workflow on demand. `<workflow-id>` is the UUID shown in the `id` column of
`pixee workflow list`.

`run` targets `schedule` workflows specifically — `new-scan` and `pull-request-scan` workflows
fire on their own events (incoming scan, pull-request scan) and there is nothing for the agent
to trigger manually. Pairs naturally with `pixee workflow update schedule --enabled` for the
"re-enable, then kick off once now" flow, and with `--disabled` to suspend the cadence after a
single manual run.

No flags. No `--repo` flag — the workflow UUID disambiguates by itself.

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

# Disable a workflow without changing anything else
pixee workflow update schedule a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --disabled

# Re-enable and rename a new-scan workflow
pixee workflow update new-scan a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d \
  --enabled --name release-scans

# Tighten the severity floor on an existing pull-request-scan workflow
pixee workflow update pull-request-scan a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d \
  --action create-patch --min-severity-score 8

# Drop the start time and clear the severity-labels filter on a schedule workflow
pixee workflow update schedule a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d \
  --unset start --action create-patch --unset severity-labels

# Delete a workflow by UUID
pixee workflow delete a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d

# Re-enable a paused schedule workflow, then trigger it once on demand
pixee workflow update schedule a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --enabled
pixee workflow run a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
```

## Best practices

- For scripts, pass `--repo` as a UUID — stable under rename and never ambiguous. Names are fine
  for humans when the match is unique.
- Use `--output json` (or the `--json` shorthand) when piping `workflow list` into `jq`; the
  default text output drops fields that are not in the four-column set.
- Keep severity filters to one mode (labels *or* scores); the CLI rejects mixed usage before the
  network call, but the failure still spends a CI cycle.
- `update` is partial — pass only the flags that need to change. Re-sending unchanged values
  works but adds noise to scripts and audit logs.
- To clear a nullable filter on `update`, use `--unset <field>` rather than passing an empty
  value to the regular flag (which is a parse error). Action-scoped fields still require
  `--action create-patch` on the same call when unsetting.
- `--enabled` and `--disabled` are mutually exclusive on `update`; pass at most one per call.
- The `update` subcommand must match the workflow's existing event kind. To change event kind,
  delete and recreate.
- `pixee workflow run` only makes sense for `schedule` workflows; `new-scan` and
  `pull-request-scan` workflows fire on their own events. Use `run` for the "re-enable, then
  trigger once now" or "kick off the cadence ahead of schedule" patterns.
