<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/dark_mode_logo.png">
  <source media="(prefers-color-scheme: light)" srcset="img/light_mode_logo.png">
  <img alt="Pixee Logo" src="https://github.com/pixee/pixee-cli/raw/main/img/light_mode_logo.png">
</picture>

# Pixee CLI

**Meet your autonomous product security engineer.** Pixee is the agentic AppSec platform that turns
scanner noise into validated, prioritized risk and writes fixes as your developers would — ending the
security backlog instead of growing it. Learn more at [pixee.ai](https://pixee.ai).

This repository distributes `pixee`, the official command-line interface for the Pixee platform. It
is intended for Pixee customers and gives authenticated access to the Pixee REST API through dedicated
subcommands and a generic `pixee api` passthrough, and ships with coding-agent skills so tools like
Claude Code and OpenAI Codex can drive it natively.

## Install

### Homebrew (macOS and Linux)

```bash
brew tap pixee/pixee
brew install pixee
```

### Direct download

Pre-compiled binaries for `linux-x64`, `darwin-arm64`, and `windows-x64` are published as
assets on each [GitHub Release](https://github.com/pixee/pixee-cli/releases/latest). Download the archive
for your platform, extract the `pixee` binary, and place it on your `PATH`.

### Verifying your download

Each release publishes a `SHA256SUMS` manifest listing the checksum of every archive. Download it into the
same directory as your archive, then confirm the archive matches its published checksum:

```bash
# Linux
sha256sum --ignore-missing -c SHA256SUMS

# macOS
shasum -a 256 --ignore-missing -c SHA256SUMS
```

`--ignore-missing` checks only the archives you actually downloaded; a line ending in `OK` confirms a match.

## Getting started

```bash
# Log in as yourself; opens your browser to sign in through your identity provider
pixee auth login --server https://pixee.example.com

# Send an authenticated request to any Pixee REST API endpoint
pixee api /api/v1/repositories --paginate

# List workflows configured for a repository
pixee workflow list --repo my-repo
```

Logging in this way gives you a short-lived token that identifies **you**, so your
actions are attributable and your permissions come from your identity provider.

For CI and other unattended contexts, where nobody can approve a browser prompt,
use your deployment's shared API key instead. Read it from stdin rather than
passing it inline, so it stays out of your shell history:

```bash
echo -n "$PIXEE_TOKEN" | pixee auth login --server https://pixee.example.com --token -
```

Working with more than one deployment? `pixee auth use <server>` sets the one
later commands target, and `pixee auth status` shows every session you hold.

Run `pixee --help` to see every subcommand.

## TLS configuration

To point `pixee` at a Pixee Enterprise Server with a privately signed certificate, configure trust through one of the
options below. `pixee` verifies certificates against its bundled Mozilla CA list, not the operating system's trust
store, so installing the CA in your OS keychain alone won't make the connection succeed.

### Add the internal CA to `pixee`'s trust set (recommended)

Set `NODE_EXTRA_CA_CERTS` to a PEM file containing the chain. Verification still happens; only your specific CA is
added to the trust set, so the bearer token stays protected from passive eavesdroppers and on-path attackers.

```sh
NODE_EXTRA_CA_CERTS=/etc/ssl/internal-ca.pem pixee --server https://pixee.internal scan list
```

For a persistent setup, export the variable from your shell profile or set it in your deployment environment (CI
variable, container env, Kubernetes secret, etc.).

### Disable verification (last resort)

If you genuinely cannot obtain the CA chain (short-lived sandbox, one-off connectivity check, ephemeral CI container
with no way to mount a PEM), pass `--insecure` or set `PIXEE_INSECURE_TLS=true` to skip certificate verification
entirely. A warning prints to stderr on every invocation so the choice stays visible in CI logs.

```sh
pixee --insecure --server https://pixee.internal scan list
PIXEE_INSECURE_TLS=true pixee --server https://pixee.internal scan list
```

Avoid this in production: with verification off, anyone who can intercept the connection can read your bearer token
and act as you against the API. Treat any persistent CI usage as a bug to come back and fix once the CA is available.

### Reference

See [Bun's `tls.getCACertificates`](https://bun.com/reference/node/tls/getCACertificates) for the full chain loading
order (bundled Mozilla CAs → system keychain when `NODE_USE_SYSTEM_CA=1` → `NODE_EXTRA_CA_CERTS` extras) and
[Node's `NODE_EXTRA_CA_CERTS` docs](https://nodejs.org/api/cli.html#node_extra_ca_certsfile) for the env-var contract
Bun inherits.

## Coding agent skills

The Pixee CLI ships with [skills.sh](https://skills.sh)-formatted skills that teach coding agents
(Claude Code, OpenAI Codex, and others) how to drive the CLI. The skills live under
[`skills/`](./skills/) and are licensed separately under the Apache License, Version 2.0.

Install every skill at once:

```bash
npx skills add pixee/pixee-cli --all
```

Omitting `--all` opens an interactive picker so you can choose which skills to install. Or add
individual skills directly with `npx skills add pixee/pixee-cli --skill <name>`:

- [`pixee-shared`](./skills/pixee-shared/SKILL.md) — global flags, exit codes, error handling.
  Prerequisite for the others.
- [`pixee-auth`](./skills/pixee-auth/SKILL.md): `pixee auth login/use/token/status/logout`,
  per-user device-flow login or the deployment's shared API key, bearer tokens for the REST API
  and the observability endpoints, credential precedence, and fixing exit-code-2 failures.
- [`pixee-api`](./skills/pixee-api/SKILL.md) — the `pixee api` escape hatch and HAL discovery.
- [`pixee-preferences`](./skills/pixee-preferences/SKILL.md) — read and write Pixee organization
  preferences from files or stdin.
- [`pixee-repo`](./skills/pixee-repo/SKILL.md) — `pixee repo list`, `view`, `delete`, and the
  shared `--repo` resolution protocol.
- [`pixee-scan`](./skills/pixee-scan/SKILL.md) — `pixee scan list`, `view`, `analyze`, `create`,
  and `delete`, with filters for repository, branch, detector tool, and analysis state.
- [`pixee-integration`](./skills/pixee-integration/SKILL.md) — `pixee integration list` to
  discover the integration ids consumed by `pixee scan create --integration-id`.
- [`pixee-analysis`](./skills/pixee-analysis/SKILL.md) — `pixee analysis list` (with filters for
  repo, branch, state, tool, and updated-at window), `pixee analysis view` with `--watch`
  polling until terminal state, and `pixee analysis delete`.
- [`pixee-finding`](./skills/pixee-finding/SKILL.md) — `pixee finding list` (with `--stats` and
  filters across triage, fix, sca) and `pixee finding view`, scoped to a scan with per-finding
  analysis results inlined.
- [`pixee-workflow`](./skills/pixee-workflow/SKILL.md) — workflow list/create/update/run/delete,
  event kinds, severity filters, and partial-update semantics.
