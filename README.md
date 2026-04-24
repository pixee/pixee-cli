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
brew install pixee/tap/pixee
```

### Direct download

Pre-compiled binaries for `linux-x64`, `darwin-arm64`, `darwin-x64`, and `windows-x64` are published as
assets on each [GitHub Release](https://github.com/pixee/pixee-cli/releases/latest). Download the archive
for your platform, extract the `pixee` binary, and place it on your `PATH`.

## Getting started

```bash
# Authenticate against a Pixee deployment
pixee auth login --server https://pixee.example.com --token <your-token>

# Send an authenticated request to any Pixee REST API endpoint
pixee api /api/v1/repositories --paginate

# List workflows configured for a repository
pixee workflow list --repo my-repo
```

Run `pixee --help` to see every subcommand.

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
- [`pixee-auth`](./skills/pixee-auth/SKILL.md) — login, status, credential precedence, and
  fixing exit-code-2 failures.
- [`pixee-api`](./skills/pixee-api/SKILL.md) — the `pixee api` escape hatch and HAL discovery.
- [`pixee-repo`](./skills/pixee-repo/SKILL.md) — `pixee repo list` and the shared `--repo`
  resolution protocol.
- [`pixee-workflow`](./skills/pixee-workflow/SKILL.md) — workflow list/create/delete, event
  kinds, and severity filters.
