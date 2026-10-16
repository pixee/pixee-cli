---
name: pixee-repo
description: "List, view, create, and delete Pixee repositories and their integration mappings with shared name-or-UUID resolution."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.3.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee repo --help"
---

# pixee repo

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling. Those conventions apply to every command in this skill. See `../pixee-auth/SKILL.md`
> if authentication needs to be configured.

`pixee repo` manages repositories registered with the Pixee platform: list, view, create, and
delete, plus the integration mappings that bind a repository to a scanner project. It also
documents the `--repo` resolution protocol used by every other subcommand that targets a specific
repository.

## pixee repo list

List registered repositories. Pagination is transparent — the CLI walks every page automatically.
Text output is tab-separated with columns `name`, `full_name`, `type`, `default_branch`, `id`.
GitHub repositories on which the Pixee GitHub App is no longer installed are left out unless you
pass `--include-uninstalled` (see "Uninstalled repositories").

Flags:

- `--name <pattern>` — case-insensitive partial-match filter against the repository's `name` field.
  Server-side filter; reduces payload before pagination.
- `--include-uninstalled` — also list GitHub repositories on which the Pixee GitHub App is no
  longer installed. Text output gains a sixth column, `installed`: `true` or `false` for a GitHub
  repository, empty for every other type. Combines with `--name` and the other `list` filters.
  Older binaries reject the flag with `unknown option`; upgrade the CLI (see `pixee-shared`).
- `--output text|json` — see `pixee-shared`.
- `--server <url>` — see `pixee-shared`.

Each repository has a `type` discriminator (`github`, `gitlab`, `azure`, `git`, `bitbucket`), a
UUID `id`, a `name`, a `full_name` (e.g., `pixee/pixee-platform`), and a `default_branch`.
Type-specific fields (`owner`, `html_url` for GitHub, etc.) appear only in `--output json`.

## pixee repo view

```
pixee repo view <repo-id>
```

Fetch a single repository by UUID. `<repo-id>` is the value shown in the `id` column of
`pixee repo list`.

Default text mode prints a sectioned `Key: value` block of the common fields shared by every
git-provider variant — `Name`, `Full name`, `Default branch`, `Type`, `ID` — colon-separated, one
field per line. Use `--output json` (or `--json`) for the full HAL body, which adds the
provider-specific fields (`github_app_installation_id` for GitHub, `azure_project` for Azure
DevOps, etc.) and the `_links` envelope. The text view intentionally omits the provider-specific
fields because the union over five integration types would render inconsistently; reach for
`--json` when an agent needs them.

A non-existent UUID returns the standard not-found error and exits 3. `view` takes a UUID only; a
name or `owner/name` answers not found, so resolve it with `pixee repo list --name` first.

- `--expand <relation>` — **repeatable**. Follow one of the repository's `_links` and render it
  inline. The `Expand:` line names the relations on offer; `repository-integrations` lists the
  repository's integration mappings (see **pixee repo integration** below).

## pixee repo create

```
pixee repo create [options]
```

Create a **generic git repository** — the `git` provider type, for a repository reached over
plain HTTP(S) with a username/password or access token, as opposed to a GitHub, GitLab, Azure, or
Bitbucket repository, which are registered through their respective platform integrations instead
of this verb.

Flags:

- `--name <name>` — repository display name.
- `--url <url>` — HTTP(S) Git repository URL.
- `--username <username>` — Git username.
- `--password [password]` — Git password or access token. Pass the flag with no value to enter it
  securely, or `--password -` to read it from stdin; an inline value works but lands in shell
  history.

## pixee repo delete

```
pixee repo delete <repo-id>
```

Delete a repository by UUID. **Cascading:** the server also removes the repository's scans,
workflows, and findings as part of the same operation, so this is more destructive than the verb
name suggests. On success the CLI prints `Deleted repo <id>` and exits 0; a missing repo exits 3.

There is no confirmation prompt — `pixee` does not ship interactive guards for any destructive
verb (`scan delete`, `workflow delete`, `repo delete` all behave the same way). Scripts that want
a guard should add their own check before calling.

## pixee repo integration

A **mapping** binds a repository to a project on a scanner integration (a Sonar project key, an
AppScan application id, and so on). A repository holds one mapping per type.

**List** a repository's mappings with the expand flag on `view`:

```
pixee repo view <repo-id> --expand repository-integrations
```

Text output gives one row per mapping: type, mapping id, integration href, and the type's
identifiers as `name=value`. `--json` returns the full records under
`_embedded."repository-integrations"`; each carries `id`, `type`, the type's identifier fields, and
`_links.integration.href` naming the integration it uses. Treat that href as opaque and compare it
for equality against an integration's own `_links.self.href` (see `pixee-integration`).

**Create** one mapping, with the type before the repository:

```
pixee repo integration create <type> <repository> --<identifier-flag> <value> [--integration-id <id>]
```

`<type>` is one of `sonar`, `appscan`, `arnica`, `black-duck-hub`, `checkmarx`,
`checkmarx-enterprise`, `datadog`, `polaris`, `veracode`; each has its own identifier flags, so run
`pixee repo integration create <type> --help`. `<repository>` accepts a name, `owner/name`, or UUID.
`--integration-id` is optional except for `black-duck-hub` and `checkmarx-enterprise`; omitting it
selects the type's system default instance, and the default instance's own id (for example
`sonar-default`) is rejected with "Unknown integration". A second mapping of the same type exits 1
with "Duplicate repository integration". A missing required flag exits 1; an unknown repository
exits 3.

**Delete** one mapping:

```
pixee repo integration delete <repository> <mapping-id>
```

`<mapping-id>` is the `id` from the listing. A mapping that does not exist exits 3. Mappings cannot
be edited in place: re-pointing a repository is delete, then create, and the new mapping gets a new
id. To move many repositories between integrations safely, follow
`../pixee-migrate-repo-integrations/SKILL.md`.

Older binaries lack these commands, and on them `pixee repo integration --help` prints the parent
`pixee repo` help instead of an error. Run it first: its usage line must read
`pixee repo integration`, otherwise upgrade the CLI (see `pixee-shared`).

## Uninstalled repositories

A GitHub repository can outlive the Pixee GitHub App's access to it. Pixee does not delete it: its
scans and findings stay, and they are still reachable by UUID. What changes is where it shows up:

- **`pixee repo list` omits it by default.** Only GitHub repositories are affected. GitLab, Azure
  DevOps, Bitbucket, and generic git repositories have no install state and are always listed.
- **`pixee repo list --include-uninstalled` includes it.** Each GitHub repository then carries a
  boolean `installed`: the text view adds it as the sixth column, and `--output json` shows it as
  the `installed` property (`pixee repo view <repo-id> --json` shows it too).
- **Names no longer resolve to it.** `--repo <name>` and `--repo <owner/name>` look the repository
  up in the default list, so for an uninstalled repository they exit 3 ("no repository named X
  found"). A UUID skips the lookup, so `--repo <uuid>` and `pixee repo view <uuid>` keep working.

To find uninstalled repositories, list with `--include-uninstalled` and keep the rows where
`installed` is `false`; each row's `id` is the UUID to pass on.

## Repository name resolution

The `--repo` flag accepted by `pixee workflow` and other subcommands resolves names to UUIDs using
the same protocol. Three cases:

1. **UUID** (matches `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` pattern): used as the repository ID
   directly — no lookup.
2. **Name or full_name**: the CLI queries `GET /api/v1/repositories?name=<value>` and filters the
   response client-side for an exact, case-insensitive match against either the `name` field
   (e.g., `pixee-platform`) or the `full_name` field (e.g., `pixee/pixee-platform`).
3. **Outcome**:
   - No exact match → exit code 3 ("no repository named X found").
   - One exact match → use it.
   - Multiple exact matches (same `name` across integrations; for example, GitHub and GitLab both
     have `pixee-platform`) → exit code 1 with an error listing each candidate with its UUID and
     `type`. Retry with the UUID.

Both `--repo pixee-platform` and `--repo pixee/pixee-platform` resolve correctly when the match is
unambiguous.

Step 2 searches the default list, so a name never matches an uninstalled GitHub repository (see
"Uninstalled repositories"). When a repository you expect is "not found", look its UUID up with
`pixee repo list --include-uninstalled` before concluding it was never registered.

## Examples

```bash
# List every repository
pixee repo list

# Machine-readable listing piped to jq for further filtering
pixee repo list --output json | jq '.[] | select(.type == "github") | .full_name'

# Filter server-side to reduce payload
pixee repo list --name pixee-platform

# Include GitHub repositories the Pixee GitHub App can no longer reach; the sixth column is installed
pixee repo list --include-uninstalled

# Which repositories are uninstalled? Print each one's UUID and full name
pixee repo list --include-uninstalled --output json \
  | jq -r '.[] | select(.installed == false) | "\(.id)  \(.full_name)"'

# Inspect a single repo's common fields in text mode
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d

# Pull the full HAL body to see provider-specific fields like github_app_installation_id
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --json \
  | jq '{type, full_name, github_app_installation_id}'

# Create a generic git repository, reading the password/token from stdin
echo -n "$GIT_ACCESS_TOKEN" | pixee repo create \
  --name internal-tool --url https://git.example.com/team/internal-tool.git \
  --username ci-bot --password -

# List a repository's integration mappings, then read the full records
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --expand repository-integrations
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --expand repository-integrations --json \
  | jq '._embedded."repository-integrations"[] | {id, type, integration: ._links.integration.href}'

# Map a repository to a Sonar project on a specific integration, then remove the mapping
pixee repo integration create sonar pixee/pixee-platform \
  --project-key pixee_pixee-platform --integration-id <integration-id>
pixee repo integration delete pixee/pixee-platform <mapping-id>

# Delete a repository by UUID (also removes its scans, workflows, and findings)
pixee repo delete a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d

# Ambiguous --repo: the CLI prints each match with its UUID; retry with the UUID
pixee workflow list --repo pixee-platform
# Error: Multiple repositories named "pixee-platform":
#   a1b2c3d4-...  github  pixee/pixee-platform
#   e5f6g7h8-...  gitlab  pixee-group/pixee-platform
```

## Best practices

- When a repository name is unambiguous, prefer the short name (`pixee-platform`) or full_name
  (`pixee/pixee-platform`) — it is more readable than a UUID and both forms resolve identically.
- When scripting across many repositories, use UUIDs: they are stable under rename and never
  ambiguous.
- Pagination is transparent on `pixee repo list`; `--paginate` exists only on `pixee api`.
- Reach for `pixee repo view --json` when an agent needs provider-specific fields; the default
  text view is intentionally pared down to the fields every integration shares.
- `pixee repo delete` cascades to scans, workflows, and findings server-side. Confirm scope (and
  any depending scripts) before running it; there is no client-side confirmation prompt.
- `pixee repo create` only registers the generic `git` provider type. For GitHub, GitLab, Azure,
  or Bitbucket repositories, use that provider's own integration/App-install flow instead of this
  verb.
- Do not delete a repository just because it is uninstalled. Uninstalling the app hides the
  repository from the default list and from name lookups, but its scans and findings remain; confirm
  with the user before running `pixee repo delete` on it.
- Deleting a mapping leaves the repository in place; deleting the repository cascades to its scans.
  To change which integration a repository uses, change the mapping, never the repository.
- Never pass `--password` with an inline value in a script or CI job; use `-` to read from stdin
  (or the bare flag to prompt interactively) so the credential never lands in shell history.
