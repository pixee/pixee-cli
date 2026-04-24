---
name: pixee-workflow
description: "List, create, update, and delete Pixee workflows on a repository."
metadata:
  version: 1.2.0
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

`pixee workflow` manages Pixee workflows for a single repository: list, create, update, and
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

`pixee workflow update` applies a **partial update** to an existing workflow. Event kind is
selected via a subcommand — it must match the existing workflow's event kind, so the CLI never
has to guess:

- `pixee workflow update new-scan <workflow-id>` — update a new-scan workflow.
- `pixee workflow update pull-request-scan <workflow-id>` — update a pull-request-scan workflow.
- `pixee workflow update schedule <workflow-id>` — **always rejected**. Schedule workflow updates
  are not exposed via the CLI; fall back to `pixee api -X PUT /api/v1/workflows/{id}` with a
  hand-crafted body when you need them.

Every flag is **optional**. Omitted flags are left out of the request body and the server
preserves the existing value (true partial update — no merge-vs-replace guesswork). Clearing a
field back to `null` is supported for create-patch action sub-filters via repeatable
`--unset <field>` (see [Clearing fields](#clearing-fields) below). Event-level fields
(`branch`, `target-branch`, `source-branch`) are not currently clearable through the CLI —
fall back to `pixee api -X PUT /api/v1/workflows/{id}` if you need to null one out.

Event-kind-specific flags mirror `create`:

**new-scan** — `--branch <pattern>` (optional; supports a `*` suffix, e.g. `release/*`).

**pull-request-scan** — `--target-branch <pattern>`, `--source-branch <pattern>` (each optional).

### Shared update flags

Every `update` subcommand accepts:

- `--enabled` / `--disabled` — mutually exclusive; pass either to toggle the workflow's enabled
  state, or neither to leave it unchanged.
- `--name <name>` — rename the workflow.
- `--action <kind>` — `create-patch` or `none`. Note: the server requires the action type in the
  payload to match the existing action type, so this flag is primarily useful for touching the
  current action's nested fields — not for swapping between action kinds.
- `--severity-labels <csv>`, `--min-severity-score <int>`, `--max-severity-score <int>`,
  `--min-fix-confidence <high|medium|low|no-rating>`, `--finding-limit <int|none>` — optional
  create-patch sub-filters. Each requires `--action create-patch`; mixing them with
  `--action none` is rejected at parse time (exit code 1). `--severity-labels` and
  `--min/max-severity-score` remain mutually exclusive.

Unlike `create`, there is no `--tool` flag on `update`: the tool is immutable after creation.

### Clearing fields

`--unset <field>` clears a create-patch action sub-filter back to `null`. The flag is
**repeatable** — pass it once per field:

```bash
pixee workflow update new-scan <id> --action create-patch --unset severity-labels
pixee workflow update new-scan <id> --action create-patch --unset min-fix-confidence --unset finding-limit
```

Valid fields: `severity-labels`, `min-severity-score`, `max-severity-score`,
`min-fix-confidence`, `finding-limit`. All require `--action create-patch`. Passing both a
setter and its `--unset` for the same field (e.g. `--severity-labels critical --unset
severity-labels`) is rejected at parse time.

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

# Update only the branch pattern of an existing new-scan workflow
pixee workflow update new-scan a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --branch 'release/*'

# Disable a workflow without changing anything else
pixee workflow update new-scan a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --disabled

# Clear the severity-labels filter back to null (apply to all severities)
pixee workflow update new-scan a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d \
  --action create-patch --unset severity-labels

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
