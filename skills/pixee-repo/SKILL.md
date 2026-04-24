---
name: pixee-repo
description: "Pixee CLI: list repositories and resolve --repo arguments to repository UUIDs."
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

`pixee repo` lists repositories registered with the Pixee platform and documents the `--repo`
resolution protocol used by every other subcommand that targets a specific repository.

## Commands

### pixee repo list

List registered repositories. Pagination is transparent — the CLI walks every page automatically.

Flags:

- `--name <pattern>` — case-insensitive partial-match filter against the repository's `name` field.
  Server-side filter; reduces payload before pagination.
- `--output text|json` — see `pixee-shared`.
- `--server <url>` — see `pixee-shared`.

Each repository has a `type` discriminator (`github`, `gitlab`, `azure`, `git`, `bitbucket`), a
UUID `id`, a `name`, a `full_name` (e.g., `pixee/pixee-platform`), and a `default_branch`.
Type-specific fields (`owner`, `html_url` for GitHub, etc.) appear only in `--output json`.

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
     have `pixee-platform`) → exit with an error listing each candidate with its UUID and `type`.
     Retry with the UUID.

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
