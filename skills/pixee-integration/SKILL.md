---
name: pixee-integration
description: "List Pixee integrations to discover the id, type, and capabilities of each scanner integration registered with the org."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee integration --help"
---

# pixee integration

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-auth/SKILL.md` if authentication needs to be configured. See
> `../pixee-scan/SKILL.md` for the `--integration-id` consumer this skill's `list` verb feeds.

`pixee integration` enumerates the third-party scanner integrations registered with the Pixee
organization. Each integration is the org-side configuration that lets the platform attribute an
uploaded scan to a known source (GitHub App installation, GitLab CI token, Sonar host token,
etc.) and grants the platform any extra capabilities that integration exposes — pushing triage
verdicts back, polling for scans on a cadence, and so on.

The discovery flow exists primarily so an agent calling `pixee scan create --integration-id <id>`
has a canonical way to look up the integration id without dropping to `pixee api`.

## pixee integration list

```
pixee integration list
```

List integrations registered with the org. Pagination is transparent: the CLI walks every page
in one call.

Text output is tab-separated with columns `id`, `type`, `capabilities`. The `capabilities`
column is a JSON-array literal (e.g., `[]` for an integration with no extras, `["triage-push"]`
when the integration can push triage verdicts back to the source). JSON output is a flat array
of integration records with the HAL envelope stripped — each record carries `id`, `type`,
`capabilities`, and a `_links` object for HAL traversal.

The default integration registered for each scanner type often uses the id pattern
`<type>-default` (e.g., `sonar-default`, `polaris-default`, `github-default`), but that is a
convention, not a contract. List the integrations and read the `id` rather than constructing it
by hand.

The `type` discriminator names the scanner family (e.g., `sonar`, `polaris`, `gitlab`,
`appscan`). It is **not** identical to the `--tool` enum on `pixee scan create` — the latter
distinguishes scan kinds at a finer grain (e.g., `polaris_sast` vs `polaris_sca`,
`gitlab_sast` vs `gitlab_dependency_scanning`), while the integration `type` collapses to the
provider family.

## Examples

```bash
# List every integration registered with the org
pixee integration list

# JSON shape for programmatic consumption
pixee integration list --json | jq '.[] | {id, type, capabilities}'

# Find integrations that can push triage verdicts back to the source
pixee integration list --json | jq '.[] | select(.capabilities | index("triage-push"))'

# Discover the sonar integration id and use it in a scan-create call
integration_id=$(pixee integration list --json \
  | jq -r '.[] | select(.type=="sonar") | .id' | head -n1)
pixee scan create pixee/pixee-platform \
  --tool sonar --integration-id "$integration_id" \
  --branch main --sha "$(git rev-parse HEAD)"

# Walk to an integration's HAL self link rather than re-listing
href=$(pixee integration list --json | jq -r '.[] | select(.id=="polaris-default") | ._links.self.href')
pixee api "$href"
```

## Best practices

- The integration id is stable across calls; cache it per-org rather than re-listing on every
  invocation. Resolve it from `pixee integration list` rather than constructing a
  `<type>-default` string by hand, since that pattern is a convention the platform can change.
- Filter by `type` when looking for a specific scanner family. The org may have multiple
  integrations of the same type (different GitHub Apps, multiple GitLab tenants) and `type`
  alone is not unique.
- Read `capabilities` before assuming an integration can do more than receive uploads.
  `triage-push` is the load-bearing one today; treat the array as forward-compatible and check
  for membership (`jq '.capabilities | index("...")'`) rather than equality.
- Don't conflate integration `type` with `pixee scan create --tool`. The mapping is one-to-many
  for some providers (one `polaris` integration backs both `polaris_sast` and `polaris_sca`
  scans). Pick the `--tool` value from the scan's true kind, and the `--integration-id` from
  whatever integration attributes the upload.
- Prefer the dedicated subcommand over `pixee api /api/v1/integrations` for discovery. The
  subcommand pages transparently and surfaces the same fields without the HAL envelope when
  text mode is enough.
