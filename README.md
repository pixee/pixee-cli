# Pixee CLI

`pixee` is the official command-line interface for the [Pixee](https://pixee.ai) platform. It provides
authenticated access to the Pixee REST API through both dedicated subcommands and a generic `pixee api`
passthrough, and ships with coding agent skills so tools like Claude Code and OpenAI Codex can drive it
natively.

## Install

### Homebrew (macOS and Linux)

```bash
brew install pixee/tap/pixee-cli
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

_Coming soon._ The Pixee CLI ships with [skills.sh](https://skills.sh)-formatted skills that teach
coding agents (Claude Code, OpenAI Codex, and others) how to drive the CLI. Skills for `pixee api`,
`pixee auth`, `pixee repo`, and `pixee workflow` will live under the `skills/` directory of this
repository and be installable via `npx skills add`.
