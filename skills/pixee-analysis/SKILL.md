---
name: pixee-analysis
description: "List, view, and delete Pixee analyses with filters and optional polling until the analysis reaches a terminal state."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee analysis --help"
---

# pixee analysis

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-auth/SKILL.md` if authentication needs to be configured. See
> `../pixee-scan/SKILL.md` (the `analyze` verb) and `../pixee-finding/SKILL.md` (the
> `representative-results` HAL link) — both produce the analysis UUID this skill operates on.
> See `../pixee-repo/SKILL.md` for the `--repo` resolution protocol used by `list`.

`pixee analysis` lists analyses across the platform, fetches a single analysis by UUID with
optional polling on `view`, and deletes an analysis (and its associated findings and patches)
by UUID. An analysis is one run of Pixee's triage, fix, or sca pipeline against a scan; its
UUID surfaces in two places — the response from `pixee scan analyze <scan-id>` (the CLI prints
`Started analysis <analysis-id> on scan <scan-id>`) and the `analysis` HAL link on every
finding's representative result (see `pixee-finding`). `list` is the discovery primitive for
analyses that didn't originate from a `pixee scan analyze` call the agent made.

## pixee analysis list

```
pixee analysis list [filter flags...]
```

All flags are optional. With none, every analysis the token can see is returned. Pagination is
transparent: the CLI walks every page in one call.

Text output is tab-separated with columns `id`, `state`, `branch`, `sha`, `updated_at`. JSON
output is a flat array of analyses with the HAL envelope stripped.

Filter flags:

- `--repo <name-or-uuid>` — **repeatable**. Restrict to one or more repositories. Names resolve
  via the protocol documented in `pixee-repo`. Multiple `--repo` flags OR together.
- `--branch <name>` — exact branch name (case-sensitive).
- `--state <state>` — **repeatable**. One of `queued`, `in-progress`, `skipped`, `completed`,
  `failed`. Multiple values OR together.
- `--tool <name>` — **repeatable**. Filter by detector tool (`sonar`, `semgrep`, `codeql`, etc.).
- `--updated-after <iso8601>` / `--updated-before <iso8601>` — bound the `updated_at` window
  using full ISO-8601 with timezone (e.g. `2026-05-01T00:00:00Z`). Server validates the format.

## pixee analysis view

## pixee analysis view

```
pixee analysis view <analysis-id> [--watch] [--interval <seconds>]
```

`<analysis-id>` is the analysis UUID.

Default text mode prints the analysis's headline fields — `id`, `type`, `state`, `updated_at`,
and the scan/repository the analysis was run against. JSON mode (`--output json` or `--json`)
returns the full HAL representation including `_links.scan`, `_links.findings`, and the
per-section result objects that downstream tooling consumes. As with every Pixee resource, follow
HAL links via `pixee api <href>` rather than hardcoding paths.

### `--watch`

```
pixee analysis view <analysis-id> --watch [--interval <seconds>]
```

With `--watch`, the CLI polls the analysis on a fixed cadence and narrates each state transition
to stderr until the analysis reaches a terminal state (`completed` or `failed`). Final output goes
to stdout in the same shape as a non-watching `view`, so `--watch` is safe to use in scripts that
consume stdout. Exit code matches the terminal state: 0 for `completed`, non-zero for `failed`.

`--interval <seconds>` (default 5) sets the polling cadence. Lower intervals surface progress
sooner; higher intervals reduce server load on long-running analyses. Only meaningful with
`--watch` — passing it without `--watch` has no effect.

## pixee analysis delete

```
pixee analysis delete <analysis-id>
```

Delete an analysis by UUID. The platform also removes the analysis's associated findings and
patches as part of the operation, so this is more destructive than the verb name suggests. On
success the CLI prints `Deleted analysis <id>` and exits 0; a missing analysis exits 3. There
is no client-side confirmation prompt, matching `pixee scan delete`, `pixee repo delete`, and
`pixee workflow delete`.

## Examples

```bash
# Every analysis visible to the token (paginated transparently)
pixee analysis list

# Failed analyses on main across two repos in the last 24h
pixee analysis list --repo pixee/pixee-platform --repo analysis-service \
  --branch main --state failed --updated-after 2026-05-19T00:00:00Z

# Completed sonar analyses, JSON for downstream processing
pixee analysis list --tool sonar --state completed --json \
  | jq '.[] | {id, state, updated_at}'

# View an analysis by UUID
pixee analysis view 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d

# Block until an analysis finishes, narrating progress
pixee analysis view 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d --watch

# Block until done with a 15-second poll interval (lighter on the server for long runs)
pixee analysis view 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d --watch --interval 15

# Chain: start an analysis on a scan, capture the analysis id, then watch it to completion
analysis_id=$(pixee scan analyze <scan-id> 2>&1 \
  | sed -n 's/^Started analysis \([^ ]*\) on scan .*/\1/p')
pixee analysis view "$analysis_id" --watch

# Follow the analysis HAL link from a finding's representative result without a second view call
href=$(pixee finding view <finding-id> --scan <scan-id> --json \
  | jq -r '._embedded["representative-results"]._embedded.items[]
           | select(.type=="fix") | ._links.analysis.href')
pixee api "$href"

# Delete an analysis by UUID (also removes its findings and patches)
pixee analysis delete 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d

# Inspect just the terminal state and updated_at of an analysis
pixee analysis view 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d --json | jq '{state, updated_at}'
```

## Best practices

- Filter `pixee analysis list` aggressively. The unfiltered set grows with every imported scan;
  combining `--repo`, `--branch`, and `--state` keeps payloads small and pagination cheap.
  `--updated-after` is the right tool for "what changed since I last looked" rather than
  re-walking the whole set.
- For the `pixee scan analyze` follow-up case, prefer the analysis UUID the start call printed
  over re-listing — `list` is the discovery primitive for analyses you didn't kick off yourself.
- Reach for `--watch` when the agent's next step depends on the analysis having reached a
  terminal state (e.g., presenting a fix patch to the user, gating a workflow on a pass).
  Without `--watch`, the agent gets the analysis's current state at fetch time and has to poll
  itself.
- Pick `--interval` based on expected duration. The default 5 seconds is right for the typical
  triage/fix latency; longer-running sca analyses are kinder to the server at 15–30 seconds.
- Don't loop `pixee analysis view` yourself — that's what `--watch` is for. Hand-rolled polling
  in a shell loop pays an extra `pixee` startup cost per iteration and lacks the CLI's
  state-transition narration.
- Prefer the HAL link approach for finding-driven flows: `pixee finding view` already inlines
  the `_links.analysis.href` on each representative result, so an agent walking from a finding
  to its analysis can `pixee api <href>` instead of re-fetching by UUID.
- Treat the analysis UUID as the durable handle. Unlike scan UUIDs (which expire roughly seven
  days after import — see `pixee-scan`), analyses persist for the life of their scan; once the
  scan expires the analysis is no longer reachable, so cache the UUID only as long as the parent
  scan would be useful.
- `pixee analysis delete` cascades to the analysis's findings and patches server-side. Confirm
  scope (and any depending scripts) before running it; there is no client-side confirmation
  prompt.
