---
name: pixee-analysis
description: "View a single Pixee analysis by UUID and poll until it reaches a terminal state with an adjustable interval."
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

`pixee analysis` fetches a single analysis by UUID and optionally polls it until completion. An
analysis is one run of Pixee's triage, fix, or sca pipeline against a scan; its UUID surfaces in
two places — the response from `pixee scan analyze <scan-id>` (the CLI prints `Started analysis
<analysis-id> on scan <scan-id>`) and the `analysis` HAL link on every finding's representative
result (see `pixee-finding`).

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

## Examples

```bash
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

# Inspect just the terminal state and updated_at of an analysis
pixee analysis view 7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d --json | jq '{state, updated_at}'
```

## Best practices

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
