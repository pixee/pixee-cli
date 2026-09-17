---
name: pixee-system-status
description: "Show Pixee platform health, license status, and AI model availability for the currently connected deployment."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee system-status --help"
---

# pixee system-status

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling. See `../pixee-auth/SKILL.md` if authentication needs to be configured.

`pixee system-status` reports the health of the connected Pixee deployment itself, distinct from
any repository, scan, or finding: platform components, license state, and which AI models are
currently available for fix generation. Reach for it when a command that should work is failing
in a way that looks like a deployment problem rather than a request problem — an expired license
or an unavailable model can produce errors that otherwise look like ordinary API failures.

## pixee system-status list

```
pixee system-status list
```

No flags beyond the global ones. Pagination is transparent — the CLI walks every page in one
call.

Text output is tab-separated with columns `type`, `name`, `status`, `description`, `id`. The
`type` discriminator distinguishes platform components (`version`), license entries (`license`),
and AI model entries (`ai-model`) in a single flat listing. A healthy entry reports
`status: "up"`. Use `--output json` (or `--json`) for the full HAL record per entry, which adds
type-specific fields not shown in text mode: `version` on `version` entries, `expires_at` and
`features_enabled` on `license` entries, and `model` (the underlying model identifier, distinct
from the human-readable `name`) on `ai-model` entries.

## Examples

```bash
# Full status listing
pixee system-status list

# Machine-readable, filtered to entries that are not up
pixee system-status list --json | jq '.[] | select(.status != "up")'

# Check whether a specific AI model is currently available
pixee system-status list --json | jq '.[] | select(.type == "ai-model" and .model == "gpt-5.4-mini")'
```

## Best practices

- Check `pixee system-status list` before escalating an otherwise-unexplained failure across
  many repositories or scans — a single unhealthy component or expired license can present as
  scattered per-request errors.
- Filter on `type` and `status` in `jq` rather than assuming a fixed row order; the set of
  reported components and models can grow between releases.
- To key on the underlying AI model, filter `--json` output on `.model`, not `.name` — `name` is
  a human-readable label (e.g. `"Analysis Service - Fast Model"`) and does not contain the model
  identifier.
