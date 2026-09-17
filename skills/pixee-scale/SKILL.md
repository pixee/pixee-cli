---
name: pixee-scale
description: "List and view Pixee severity scales used to interpret finding severity scores across scan detectors."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee scale --help"
---

# pixee scale

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling. See `../pixee-auth/SKILL.md` if authentication needs to be configured.

`pixee scale` lists and views severity scales: the per-detector mapping from a raw severity value
(as the scanner reports it) to a normalized min/max score range Pixee uses for filtering and
triage. A scan's `_links.scale` (see `pixee scan view --json` in `pixee-scan`) points at the
scale that applies to its findings.

## pixee scale list

```
pixee scale list
```

No flags beyond the global ones. Pagination is transparent — the CLI walks every page in one
call.

Text output is tab-separated with columns `id`, `type`, `severities`, `min`, `max`, where
`severities` and `min`/`max` are populated based on `type` rather than together:

- `type: ranked-set` (e.g. `sonar-merged`, `fortify`, `semgrep`) — `severities` holds a
  JSON-array literal of `{"label": <string>, "rank": <int>}` objects, one per severity level the
  detector reports; `min`/`max` are empty.
- `type: score` (e.g. `cvss`) — `min`/`max` hold the scale's numeric bounds (e.g. `0` and `10`
  for CVSS); `severities` is empty.

## pixee scale view

```
pixee scale view <scale-id>
```

Fetch a single severity scale by ID. `<scale-id>` is the value shown in the `id` column of
`pixee scale list`.

Default text mode emits a sectioned `Key: value` block. Use `--output json` (or `--json`) for the
full HAL body, which adds the `_links` envelope and the per-severity score mapping. A
non-existent ID returns the standard not-found error and exits 3.

## Examples

```bash
# List every severity scale
pixee scale list

# Machine-readable listing piped to jq
pixee scale list --json | jq '.[] | {id, type, min, max}'

# Pull the severity labels out of a ranked-set scale
pixee scale list --json | jq '.[] | select(.id == "sonar-merged") | .severities[].label'

# Inspect a single scale
pixee scale view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --json

# Follow a scan to the scale it was analyzed against
scan_id=$(pixee scan list --repo pixee/pixee-platform --json | jq -r '.[0].id')
scale_href=$(pixee scan view "$scan_id" --json | jq -r '._links.scale.href')
pixee api "$scale_href"
```

## Best practices

- Cache scale IDs per detector `type` rather than re-listing on every invocation; a scale is
  static configuration, not per-scan state.
- Follow a scan's `_links.scale` (via `pixee api`, see `pixee-api` for HAL conventions) when the
  agent needs the exact scale a specific scan's findings were normalized against, rather than
  guessing from `type` alone.
