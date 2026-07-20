---
name: pixee-o11y
description: "Authenticate to a Pixee deployment's observability stack via the OAuth2 device flow and mint per-user bearer tokens to query VictoriaMetrics, VictoriaLogs, and VictoriaTraces over HTTP."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee o11y --help"
---

# pixee o11y

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes,
> and error handling.

`pixee o11y` authenticates you to a Pixee deployment's **observability stack**
(VictoriaMetrics, VictoriaLogs, VictoriaTraces, served under `/o11y/` behind the
deployment's identity provider) and mints a short-lived, **per-user** bearer
token you can send to those HTTP APIs.

This is a **separate credential** from `pixee auth` (see `../pixee-auth/SKILL.md`):
`pixee auth` stores the Pixee REST API token used by every other subcommand;
`pixee o11y` obtains an OAuth token from the deployment's identity provider for
the observability endpoints. The two do not interchange — the REST API token is
rejected by the observability proxy, and vice versa. `pixee o11y` reuses only the
**server** resolution (`--server` → `PIXEE_SERVER` → stored config); an explicit
`[server]` positional argument overrides it.

## Commands

### pixee o11y login

Run the OAuth2 device-authorization flow against the deployment's identity
provider. Prints a verification URL (and opens your browser unless
`--no-browser`), waits for you to approve, then caches the access and refresh
tokens locally with `0600` permissions. Tokens are stored per-server, so you can
be logged in to several deployments at once.

```bash
# Uses the configured server (from `pixee auth login` or PIXEE_SERVER)
pixee o11y login

# Or target a specific deployment (URL or bare host)
pixee o11y login https://pixee.example.com
pixee o11y login edge.getpixee.com

# Headless / SSH: print the URL instead of trying to open a browser
pixee o11y login pixee.example.com --no-browser
```

### pixee o11y token

Print a currently-valid bearer token, refreshing it silently if it has expired.
Designed for scripts and coding agents — feed it straight into `curl`:

```bash
TOKEN=$(pixee o11y token https://pixee.example.com)

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

If no session is stored (or it expired and cannot be refreshed), `token` exits
non-zero with a message directing you to run `pixee o11y login`.

### pixee o11y status

Show the stored session for a server: identity, token validity, and whether a
refresh token is present. Read-only; never refreshes. Always exits 0, so it is a
safe "am I logged in?" probe. Add `--json` for machine-readable output.

```bash
pixee o11y status https://pixee.example.com
# Server: https://pixee.example.com
# Identity: dan.dunning@pixee.ai
# Token: valid (expires in 58m)
# Refresh token: present
```

### pixee o11y logout

Remove the stored observability credentials for a server (local only; does not
revoke the token server-side).

```bash
pixee o11y logout https://pixee.example.com
```

## Typical workflow

```bash
pixee o11y login pixee.example.com          # once, opens the browser
TOKEN=$(pixee o11y token pixee.example.com) # any time, refreshes as needed
curl -sG -H "Authorization: Bearer $TOKEN" \
  https://pixee.example.com/o11y/logs/select/logsql/query \
  --data-urlencode 'query=_time:15m level="ERROR" | limit 50'
```

## Notes

- **Per-user identity.** The token carries your identity from the deployment's
  IdP, so observability access is governed by your existing IdP policies and
  actions are attributable to you — there is no shared key.
- **Availability.** Programmatic observability access requires the observability
  stack (and its `pixee-cli` provider) to be enabled on the deployment. If
  `login` reports it cannot discover the endpoints, that deployment isn't set up
  for it yet.
- **Query languages** are the backends' native ones — LogsQL (VictoriaLogs),
  PromQL/MetricsQL (VictoriaMetrics), and the Jaeger query API (VictoriaTraces);
  `pixee o11y` handles only authentication, not query composition.

## See also

- `../pixee-auth/SKILL.md` — the Pixee REST API token used by every other
  subcommand (distinct from the observability token here).
- `../pixee-shared/SKILL.md` — global flags, exit codes, and TLS trust.
