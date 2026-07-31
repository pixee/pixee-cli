---
name: pixee-auth
description: "Authenticate to a Pixee deployment — the per-user OAuth2 device flow or the deployment's shared API key — choose which deployment commands target, mint bearer tokens for the REST API and observability endpoints, and inspect the current authentication state."
metadata:
  version: 1.3.0
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

`pixee auth` manages the credentials `pixee` uses to talk to a Pixee deployment. Two kinds exist,
and picking the right one matters:

| | Device flow (default) | Shared API key (`--token`) |
| --- | --- | --- |
| Issued by | the deployment's identity provider, per user | the KOTS admin console, one per deployment |
| Identity | you, by name — attributable | none; a shared `api-token` principal |
| Lifetime | short-lived, refreshes silently | static until an operator rotates it |
| Revoking one person | revoke them in the IdP | impossible without rotating for everyone |
| Reaches `/o11y/` endpoints | yes | no |
| Works unattended | no — one interactive approval | yes |

Prefer the device flow whenever a human is present. Ordinary commands (`repo list`, `scan list`,
`api`, …) use the session automatically once you have logged in, so an interactive user needs no
API key at all. Reserve the key for CI and unattended automation, where no one can approve a
browser prompt.

The two are stored separately, so adopting the device flow never disturbs an existing API-key
setup — an existing key stays on disk and keeps working as the fallback.

## Commands

### pixee auth login

With no `--token`, runs the OAuth2 device-authorization flow (RFC 8628) against the deployment's
identity provider. Prints a verification URL (and opens your browser unless `--no-browser`), waits
for you to approve, then caches the access and refresh tokens with `0600` permissions. Tokens are
stored per-server, so you can be logged in to several deployments at once.

```bash
# Device flow against the configured server
pixee auth login

# Or target a specific deployment (URL or bare host)
pixee auth login --server https://pixee.example.com
pixee auth login --server edge.getpixee.com

# Headless / SSH: print the URL instead of trying to open a browser
pixee auth login --server pixee.example.com --no-browser
```

Because the device flow needs no redirect back to the CLI, **the browser does not have to be on
the machine running `pixee`.** You can log in over SSH and approve the printed URL from your
laptop — as long as that device can reach the deployment's URL.

With `--token`, stores and validates the deployment's shared Pixee API key instead, confirming it
against `GET /api/v1/users/me`. Success exits 0; an invalid key exits 2.

```bash
# Stdin form — keeps the key off the command line and out of shell history
echo -n "$PIXEE_TOKEN" | pixee auth login --server https://pixee.example.com --token -

# Bare --token prompts interactively
pixee auth login --server https://pixee.example.com --token
```

Flags:

- `--server <url>` — deployment to authenticate against. The global `--server` and `PIXEE_SERVER`
  work too, and after a successful login the server is remembered, so `status` and `logout` need no
  flag. **`auth token` is the exception — it always requires `--server`** (see below).
- `--token [value]` — use the shared API key instead of the device flow. Bare `--token` prompts;
  `--token -` reads stdin; `--token <value>` takes it inline (lands in shell history).
- `--no-browser` — device flow only: print the verification URL, don't try to open a browser.

### pixee auth use

Set the deployment that later commands target when no `--server` and no `PIXEE_SERVER` are given.

```bash
pixee auth use ddunning.getpixee.com
# Now using https://ddunning.getpixee.com.
```

That default also gets set by a successful `auth login`, but only as a side effect of whichever
login happened last. `auth use` makes it deliberate — the same idea as `kubectl config use-context`.
Only the server changes: device-flow sessions live in their own per-server files and any shared API
key in the config is preserved, so switching deployments never logs you out or clears a key that CI
depends on.

It does not require an existing session, so you can point at a deployment before logging in to it;
it says so on stderr rather than failing.

### pixee auth token

Print a currently-valid device-flow bearer token, refreshing it silently if it has expired.
Designed for scripts and coding agents — feed it straight into `curl`:

**`--server` is required here**, unlike every other command. Everywhere else the server and the
credential are resolved together and used together, so they cannot disagree. This command returns a
bare token and *you* choose the URL, so a defaulted server would let you pipe one deployment's
credential into a request against another — silently, with neither half able to detect it.
`PIXEE_SERVER` and the stored default are deliberately not honored. Run `pixee auth status` to see
which servers you have sessions for.

```bash
TOKEN=$(pixee auth token --server https://pixee.example.com)

# Pixee REST API
curl -s -H "Authorization: Bearer $TOKEN" https://pixee.example.com/api/v1/users/me

# Logs — VictoriaLogs / LogsQL
curl -sG -H "Authorization: Bearer $TOKEN" \
  https://pixee.example.com/o11y/logs/select/logsql/query \
  --data-urlencode 'query=_time:1h | limit 100'

# Metrics — VictoriaMetrics / PromQL
curl -sG -H "Authorization: Bearer $TOKEN" \
  https://pixee.example.com/o11y/metrics/prometheus/api/v1/query \
  --data-urlencode 'query=up'

# Traces — VictoriaTraces / Jaeger API
curl -s -H "Authorization: Bearer $TOKEN" \
  https://pixee.example.com/o11y/traces/select/jaeger/api/services
```

When the server you name is not the one `auth use` currently points at, `token` says so on
**stderr** — a note, not a warning, since wanting another environment's token is routine:

```bash
$ pixee auth token --server edge.getpixee.com
note: token for https://edge.getpixee.com; 'pixee auth use' currently points at https://ddunning.getpixee.com
eyJhbGciOi…
```

stdout stays exactly one token, so `$(pixee auth token --server …)` and `2>/dev/null` both behave.

If no session is stored (or it expired and cannot be refreshed), `token` exits non-zero with a
message directing you to run `pixee auth login`. It never prints the shared API key — callers that
configured one already hold it.

### pixee auth status

Print the current authentication state: the configured server, whether the stored API key
validates, the per-user session's identity and expiry, and **every other server you hold a session
for**. Read-only; never refreshes. Always exits 0, so it is a safe "am I logged in?" probe.

`--json` is the machine-readable form: `configured` (whether any credential is set at all),
`apiKey` (a structured object: `server`, `serverSource`, `tokenSource`, `tokenValid`, `identity`,
`reachable`), `credentialInUse` (`"session"`, `"api-key"`, or `null`), and `sessions[]` with
`server`, `isDefault`, `identity`, `tokenValid`, `canRefresh`, and `expiresAt` per stored session.
Prefer these over parsing the text output.

Only the credentials that exist are printed: with no API key configured the `API key` lines are
omitted, and vice versa. Both appear when both are present, which is the case where the pairing
matters.

```bash
pixee auth status
# Server: https://pixee.example.com
# API key: stored (valid)
# API key identity: api-token
# Session: dan.dunning@pixee.ai
# Session token: valid (expires in 58m)
# Refresh token: present
# Commands will use: your session
#
# Other sessions:
#   https://edge.example.com  expired (will refresh on next use)
```

Expired sessions are listed too — they are the ones you cannot otherwise see, and this is where you
find out what to pass `auth token --server`. With nothing configured at all it collapses to one
line rather than repeating "not configured" for each credential.

### pixee auth logout

Remove the stored per-user credentials for a server. Local only — it does not revoke the token
server-side, and it deliberately leaves the shared API key in place, since that is deployment
configuration rather than a personal session.

```bash
pixee auth logout --server https://pixee.example.com
```

## Credential resolution

For every subcommand except `pixee auth login`:

- **Token:** `--token` flag → **device session for that server** → `PIXEE_TOKEN` env var → stored
  API key.
- **Server:** `--server` flag → `PIXEE_SERVER` env var → stored config (set by `auth use`, or by a
  successful `auth login`). A subcommand-level `--server` takes precedence over the global one.

The device session outranks both the env var and the stored key, so once you have logged in,
ordinary commands are already running as you. **An API key beats the session only when handed to
the CLI explicitly with `--token` on that invocation.** `PIXEE_TOKEN` sits below the session on
purpose: an env var is indistinguishable from an `export` in a shell profile, so treating it as a
deliberate choice meant anyone with one exported would log in, see a live session, and still have
every command quietly send the shared key.

Setting `PIXEE_TOKEN` + `PIXEE_SERVER` remains the CI/CD and agent-automation path — no
`pixee auth login` step required. CI is unaffected in practice because a runner has no session on
disk. On a workstation that has both, the session wins; use `--token` to force the key.

If you are unsure which credential is in play, `pixee auth status` states it outright:

```
Commands will use: your session
```

There is no hardcoded default server. If none is configured, commands exit with an error directing
the user to run `pixee auth login` or set `PIXEE_SERVER`.

## Fixing exit code 2

Both credential types exit 2 on an authentication failure, so you can branch on it uniformly — a
missing or expired device session and an invalid API key are the same exit code.

When a command exits with code 2 ("Authentication failed"):

1. Run `pixee auth status` to see which server is configured and which credentials are live.
2. If the server is wrong, re-run `pixee auth login --server <correct-url>` or set `PIXEE_SERVER`.
3. If a per-user session expired and cannot refresh, run `pixee auth login` again.
4. If the shared API key is invalid, rotate it in the admin console and log in again — preferably
   via `--token -` stdin or the `PIXEE_TOKEN` env var.
5. **If `auth status` looks healthy but other commands still 401**, read its
   `Commands will use:` line — it names the credential those commands actually send, which is not
   always the one you were looking at. The usual cause is a stored API key belonging to a
   *different* deployment than the current server: `server` and `token` in the config are a pair,
   and a device login repoints the server without touching the key. With no session for the current
   server, commands fall back to that mismatched key and 401. `auth login` prints a note on stderr
   when it creates that situation. Fix it by logging in to this deployment
   (`pixee auth login --server <url>`), storing a key for it
   (`pixee auth login --server <url> --token -`), or unsetting the old one.

## Notes

- **Per-user identity.** A device-flow token carries your identity from the deployment's IdP, so
  access is governed by your existing IdP policies and actions are attributable to you. The shared
  API key surfaces a generic `api-token` identity instead.
- **Availability.** The device flow requires the deployment's `pixee-cli` identity-provider client
  to be present. If `login` reports it cannot discover the endpoints, that deployment isn't set up
  for it yet — fall back to `--token`.
- **Query languages** for the observability endpoints are the backends' native ones — LogsQL
  (VictoriaLogs), PromQL/MetricsQL (VictoriaMetrics), and the Jaeger query API (VictoriaTraces).
  `pixee auth` handles only authentication, not query composition.

## Best practices

- Prefer the device flow for interactive work so actions are attributable to a person. After
  `auth login`, ordinary commands use it with no further configuration.
- Reserve the shared API key for CI/CD, and prefer `PIXEE_TOKEN` / `PIXEE_SERVER` env vars there —
  no local state, nothing to commit.
- To force the API key on a machine that also has a session, pass `--token` explicitly; exporting
  `PIXEE_TOKEN` will not override the session.
- Use `pixee auth status` to confirm the configured server matches the deployment the credential
  came from; a mismatched server is the most common cause of 401s.

## See also

- `../pixee-shared/SKILL.md` — global flags, exit codes, and TLS trust.
