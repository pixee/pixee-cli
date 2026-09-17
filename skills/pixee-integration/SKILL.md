---
name: pixee-integration
description: "List, view, create, update, and delete Pixee integrations to discover and manage scanner connections registered with the org."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.2.0
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
has a canonical way to look up the integration id without dropping to `pixee api`. `create`,
`update`, and `delete` manage integrations directly, but `create`/`update` are currently scoped
to Datadog only — see below.

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

Filter flags:

- `--search <text>` — substring match against integration metadata (server-side).
- `--type <type>` — filter by integration type. One of `appscan`, `arnica`, `azure`, `bitbucket`,
  `checkmarx`, `datadog`, `github`, `gitlab`, `polaris`, `sonar`, `veracode`.

## pixee integration view

```
pixee integration view <integration-id>
```

Fetch a single integration by ID. `<integration-id>` is the value shown in the `id` column of
`pixee integration list`.

Default text mode emits a sectioned `Key: value` block; use `--output json` (or `--json`) for the
full HAL body. An `Expand:` line names the relations the integration offers via its `_links`.

- `--expand <relation>` — **repeatable**. Follow one of the integration's `_links` and render it
  inline, saving a second `pixee api` call. Pass the relation name shown on the `Expand:` line.

A non-existent ID returns the standard not-found error and exits 3.

## pixee integration create

```
pixee integration create [options]
```

Create a **managed Datadog integration**. This is currently the only integration type the CLI can
create directly — GitHub, GitLab, Sonar, and the other types listed under `--type` on `list` are
provisioned through their own onboarding flow (a GitHub App install, a CI token exchange, etc.),
not through this verb.

Flags:

- `--name <name>` — human-readable integration name.
- `--base-uri <url>` — Datadog API endpoint URL.
- `--api-key [key]` / `--application-key [key]` — Datadog credentials. Pass the flag with no
  value to enter the secret interactively, or `-` to read it from stdin; passing the value inline
  works but lands in shell history. See `pixee-shared` for the same stdin pattern used by
  `--token`.

## pixee integration update

```
pixee integration update [options] <integration-id>
```

Replace connection details for a managed Datadog integration. `<integration-id>` is the value
shown in the `id` column of `pixee integration list`.

Flags mirror `create`: `--name <name>`, `--base-uri <url>`, `--api-key [key]`,
`--application-key [key]`, with the same secure-entry (`[key]` prompts, `-` reads stdin) and
stdin conventions. Pass the credential flags together when rotating both at once. A non-existent
ID returns the standard not-found error and exits 3.

## pixee integration delete

```
pixee integration delete <integration-id>
```

Delete an integration by ID. On success the CLI exits 0; a missing ID exits 3. There is no
client-side confirmation prompt, matching `scan delete`, `repo delete`, and `workflow delete`.
Deleting an integration a scan was uploaded with (`pixee scan create --integration-id`) does not
retroactively affect that scan's history.

## Examples

```bash
# List every integration registered with the org
pixee integration list

# JSON shape for programmatic consumption
pixee integration list --json | jq '.[] | {id, type, capabilities}'

# Filter to GitHub integrations only, server-side
pixee integration list --type github

# Substring search against integration metadata
pixee integration list --search sonar

# Find integrations that can push triage verdicts back to the source
pixee integration list --json | jq '.[] | select(.capabilities | index("triage-push"))'

# Inspect a single integration by ID
pixee integration view sonar-default

# Follow one of the integration's expandable relations inline (see its Expand: line for names)
pixee integration view sonar-default --expand <relation>

# Discover the sonar integration id and use it in a scan-create call
integration_id=$(pixee integration list --json \
  | jq -r '.[] | select(.type=="sonar") | .id' | head -n1)
pixee scan create pixee/pixee-platform \
  --tool sonar --integration-id "$integration_id" \
  --branch main --sha "$(git rev-parse HEAD)"

# Walk to an integration's HAL self link rather than re-listing
href=$(pixee integration list --json | jq -r '.[] | select(.id=="polaris-default") | ._links.self.href')
pixee api "$href"

# Create a Datadog integration, entering the API key from stdin
echo -n "$DD_API_KEY" | pixee integration create \
  --name datadog-prod --base-uri https://api.datadoghq.com --api-key -

# Rotate the application key on an existing Datadog integration
echo -n "$DD_APP_KEY" | pixee integration update datadog-prod --application-key -

# Delete an integration by ID
pixee integration delete datadog-prod
```

## Best practices

- The integration id is stable across calls; cache it per-org rather than re-listing on every
  invocation. Resolve it from `pixee integration list` rather than constructing a
  `<type>-default` string by hand, since that pattern is a convention the platform can change.
- Filter by `type` when looking for a specific scanner family. The org may have multiple
  integrations of the same type (different GitHub Apps, multiple GitLab tenants) and `type`
  alone is not unique. `--search` and `--type` are both server-side, so prefer them over
  post-filtering `list --json` in `jq`.
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
- `create` and `update` only provision Datadog integrations today. For every other `type`, direct
  the user to that provider's onboarding flow rather than trying to script it through this verb.
- Never pass `--api-key` or `--application-key` with an inline value in a script or CI job; use
  `-` to read from stdin (or the bare flag to prompt interactively) so the secret never lands in
  shell history or process listings.
