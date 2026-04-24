---
name: pixee-auth
description: "Store and validate Pixee API tokens and inspect the current authentication state."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee auth --help"
---

# pixee auth

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling. Exit code 2 is the signal that authentication failed — this skill is the fix.

`pixee auth` manages the credentials `pixee` uses to talk to a Pixee deployment: it stores an API
token, configures which server to target, validates, and surfaces the current authentication
state.

## Commands

### pixee auth login

Store and validate a Pixee API token. The token is written to a platform-appropriate config file
(`~/Library/Preferences/pixee` on macOS, `$XDG_CONFIG_HOME/pixee` on Linux,
`%APPDATA%\pixee\Config` on Windows) with `0600` permissions on Unix (Windows inherits the
per-user directory's NTFS ACL). `pixee auth login` confirms the token against
`GET /api/v1/users/me` — success exits 0, invalid token exits 2.

Flags:

- `--server <url>` — deployment to authenticate against. Required on first login.
- `--token <value>` — API token from the admin console's **API Tokens** page.
- `--token -` — read the token from stdin. Prefer this over `--token <value>`: flag arguments land
  in shell history.

```bash
# Interactive login
pixee auth login --server https://pixee.example.com --token pixee_xxx

# Stdin form — keeps the token off the command line
echo -n "$PIXEE_TOKEN" | pixee auth login --server https://pixee.example.com --token -
```

### pixee auth status

Print the current authentication state: configured server, whether the stored token validates, and
the authenticated identity. API-token auth surfaces a generic `api-token` identity rather than a
real user's name or email — the device-code flow (future) provides real identity.

```bash
pixee auth status
# Logged in to https://pixee.example.com as api-token
# Token: valid
```

## Credential resolution

For every subcommand except `pixee auth login`, token and server are resolved in order:

- **Token:** `PIXEE_TOKEN` env var → stored config.
- **Server:** `--server` flag → `PIXEE_SERVER` env var → stored config.

Setting `PIXEE_TOKEN` + `PIXEE_SERVER` is the CI/CD and agent-automation path — no
`pixee auth login` step is required. The `--token` flag exists only on `pixee auth login` itself
(to *store* a token); it is not a per-invocation override for other subcommands.

There is no hardcoded default server. If no server is configured via any mechanism, commands exit
with an error directing the user to run `pixee auth login` or set `PIXEE_SERVER`.

## Fixing exit code 2

When a command exits with code 2 ("Authentication failed"):

1. Run `pixee auth status` to check which server is configured and whether the current token
   validates.
2. If the server is wrong, re-run `pixee auth login --server <correct-url>` or set
   `PIXEE_SERVER`.
3. If the token is expired or revoked, generate a new one in the admin console's **API Tokens**
   page and log in again — preferably via `--token -` stdin or the `PIXEE_TOKEN` env var.

## Best practices

- Generate a separate API token per automation context so tokens can be rotated or revoked
  independently.
- Prefer `PIXEE_TOKEN` / `PIXEE_SERVER` env vars for CI/CD and agent automation — no local state,
  nothing to commit.
- Use `pixee auth status` to confirm the configured server matches the deployment where the token
  was issued; mismatched server is the most common cause of 401s.
