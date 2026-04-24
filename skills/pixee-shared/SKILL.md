---
name: pixee-shared
description: "Describe the global flags, output format, exit codes, and error handling used by every Pixee CLI subcommand."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee --help"
---

# Pixee CLI — Shared Reference

Conventions shared by every `pixee` subcommand. Read this before using any command-group skill
(`pixee-api`, `pixee-repo`, `pixee-workflow`, `pixee-auth`).

## Installation

```bash
brew tap pixee/pixee
brew install pixee
# or grab the archive for your platform from:
#   https://github.com/pixee/pixee-cli/releases/latest

pixee --version   # prints the release version baked into the binary
```

## Credentials at a glance

`pixee` reads an API token and server URL from environment variables (`PIXEE_TOKEN`,
`PIXEE_SERVER`) or from a config file written by `pixee auth login`. Env vars take precedence over
stored config.

When credentials are missing, invalid, or point at the wrong server, commands exit with code 2 and
a message like:

```
Authentication failed. Run `pixee auth login` to reconfigure.
```

For the *fix* — storing a token, the `--token -` stdin pattern, config file locations,
server-precedence rules, and `pixee auth status` — see `pixee-auth`.

## Global flags

- `--server <url>` — override the configured server for a single invocation.
- `--output text|json` — choose the output format. Default is `text` (flat, line-oriented output
  suitable for `grep`/`awk`). Use `json` for machine-readable output and pipe to `jq` for
  filtering; `pixee` does not embed a jq implementation.
- `--json` — shorthand for `--output json`.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0    | Success |
| 1    | General error |
| 2    | Authentication failure — token missing, expired, invalid, or wrong server. Fix via `pixee-auth`. |
| 3    | Resource not found |

Scripts and agents can branch on these codes without parsing stderr.

## Token security

- Never log token values. Never commit them to source control.
- Prefer `PIXEE_TOKEN` (env var) or `pixee auth login --token -` (stdin) over passing a token as a
  flag argument; flag arguments land in shell history. See `pixee-auth` for the full stdin
  pattern.

## Error responses

The Pixee API returns errors as `application/problem+json`. With `--output text`, `pixee` renders
the problem document's `title`, `detail`, and `instance` fields in a compact, human-readable form.
With `--output json`, the raw document is passed through unchanged.

Authentication failures exit with code 2. Not-found responses exit with code 3. Other problem
responses exit with code 1.
