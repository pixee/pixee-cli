---
name: pixee-repo
description: "List, view, and delete Pixee repositories with shared name-or-UUID resolution used by every targeted subcommand."
metadata:
  version: 1.0.0
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

`pixee repo` manages repositories registered with the Pixee platform: list, view, and delete. It
also documents the `--repo` resolution protocol used by every other subcommand that targets a
specific repository.

## pixee repo list

List registered repositories. Pagination is transparent — the CLI walks every page automatically.
Text output is tab-separated with columns `name`, `full_name`, `type`, `default_branch`, `id`.

Flags:

- `--name <pattern>` — case-insensitive partial-match filter against the repository's `name` field.
  Server-side filter; reduces payload before pagination.
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

A non-existent UUID returns the standard not-found error and exits 3.

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

## Examples

```bash
# List every repository
pixee repo list

# Machine-readable listing piped to jq for further filtering
pixee repo list --output json | jq '.[] | select(.type == "github") | .full_name'

# Filter server-side to reduce payload
pixee repo list --name pixee-platform

# Inspect a single repo's common fields in text mode
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d

# Pull the full HAL body to see provider-specific fields like github_app_installation_id
pixee repo view a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d --json \
  | jq '{type, full_name, github_app_installation_id}'

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
