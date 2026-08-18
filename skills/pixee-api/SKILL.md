---
name: pixee-api
description: "Send authenticated requests to any Pixee REST API endpoint."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee api --help"
---

# pixee api

> **PREREQUISITE:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling. Those conventions apply to every command in this skill. See `../pixee-auth/SKILL.md`
> if authentication needs to be configured.

The escape-hatch subcommand. `pixee api` sends authenticated HTTP requests to any Pixee REST API
endpoint, modeled on `gh api`. Use it when a dedicated subcommand does not yet exist, or when an
agent needs to compose multi-step operations directly against the API.

## HAL discovery

The Pixee API is a HAL (Hypertext Application Language) API: every response contains `_links` that
name the related resources. Start at `/api/v1` and follow `_links` to reach every other endpoint.
Do not hardcode paths beyond the root.

```bash
# Inspect the root to find the available resources
pixee api /api/v1

# Follow a link — here, the "repositories" link on the root
pixee api /api/v1/repositories --paginate

# Each resource has its own _links; follow them to related resources
pixee api /api/v1/repositories/<id>
```

## Conventions

`pixee api` closely mirrors `gh api`:

- Default method is `GET`. `pixee api` switches to `POST` automatically when any `-f` / `-F` field
  is supplied. Override explicitly with `--method <VERB>`.
- `-f key=value` adds a raw string field.
- `-F key=value` adds a typed field, converting `true`/`false` to booleans and numeric strings to
  numbers.
- `--input <file>` reads a pre-constructed JSON body from a file. Use `--input -` to read from
  stdin.
- Output is raw JSON. `pixee` does not embed a jq implementation; pipe to `jq` externally for
  filtering or transformation.

## Pagination

By default, paginated endpoints return only the first page. Add `--paginate` to let `pixee` walk
the collection automatically:

```bash
pixee api /api/v1/repositories --paginate
```

With `--paginate`, `pixee` follows `_links.next` until it is absent, merges each page's
`_embedded.items` array, and emits a single flat JSON array. The HAL envelope (`_links`, `page`,
`total`) is stripped from the output.

This is pagination-strategy-agnostic: the CLI does not construct `page-number` query parameters
itself, so if the API migrates to a different strategy the same `--paginate` flag continues to
work.

## Non-JSON resources

`pixee api` always sends `Accept: application/json` and has **no flag to override request
headers** — there is no `-H`/`--header`. That is fine for the HAL API itself, but a handful of
endpoints serve a specific representation of a resource in a non-JSON format (for example, a
triage result's `report` and `article` links from `pixee-finding`, which render as markdown). Hit
one of those through `pixee api` and it returns `406 Not Acceptable`, not JSON — that response is
expected behavior for a mismatched Accept header, not a broken endpoint or a sign to keep probing
with different flags.

For those endpoints, drop to `curl` directly, using `pixee auth token` to mint the bearer token
(same pattern `pixee-auth` documents for the `/o11y/` endpoints — the token is a bare string, so
the `Authorization` header still needs an explicit `Bearer ` prefix):

```bash
TOKEN=$(pixee auth token --server https://pixee.example.com)
curl -sS -H "Authorization: Bearer ${TOKEN}" -H "Accept: text/markdown" \
  https://pixee.example.com/api/v1/triage-results/<id>/report
```

Reach for this only when a link's whole purpose is a non-JSON representation. If the resource is
ordinary JSON, `pixee api` already sends the right `Accept` header and needs no help.

## Examples

```bash
# POST a workflow with typed fields (auto-switches to POST because fields are present)
pixee api /api/v1/repositories/<id>/workflows \
  -f event=new-scan \
  -F branch=main \
  -f action=none

# Or submit a pre-constructed body
pixee api /api/v1/repositories/<id>/workflows --input workflow.json

# Filter a paginated response externally with jq
pixee api /api/v1/repositories --paginate | jq '.[] | .full_name'
```

## Best practices

- Always use `--paginate` to collect a full collection; do not hand-roll `page-number` query
  parameters.
- Discover endpoints by following `_links` from `/api/v1`; do not inject the OpenAPI specification
  into agent context.
- Prefer dedicated subcommands (`pixee repo list`, `pixee workflow list`) when they exist — they
  encode best practices on top of `pixee api`. Use `pixee api` as the escape hatch for operations
  that do not yet have a subcommand.
- A `406 Not Acceptable` from `pixee api` means the resource only serves non-JSON content — see
  **Non-JSON resources** above for the `curl` fallback. Don't retry with different `pixee api`
  flags; there is no header override to reach for.
