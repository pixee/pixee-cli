---
name: pixee-preferences
description: "Read and write Pixee organization preferences from files or stdin with optimistic concurrency handled by the CLI."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee organization preferences --help"
---

# pixee organization preferences

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-auth/SKILL.md` if authentication needs to be configured.

Organization preferences are a freeform markdown blob (≤10,000 characters) that the Pixee
platform applies to every analysis run for the organization. The content shapes both *triage*
(is a given finding a real risk for this org?) and *remediation* (how should the fix look in
this codebase?), and is stored as a single document with audit metadata: `content`,
`updated_at`, `updated_by`, `org_id`. The MVP hardcodes `org_id` to `default-organization`;
an `--org-id` flag is planned once the platform supports multi-org.

## pixee organization preferences get

```
pixee organization preferences get [--content-only]
```

- Default text output: a two-line `Org: <id>` / `Updated: <iso> by <actor>` header (colon
  separated, no tabs, because the markdown body is multiline and tabs are reserved for list
  commands), a blank line, then the `content` body emitted verbatim with no synthetic
  trailing newline.
- `--content-only` prints the body alone, byte-for-byte. Designed for piping into a file,
  `less`, `bat`, or a diff tool. No header, no trailing newline added.
- `--output json` (or `--json`) emits the full record including the HAL `_links` envelope.
  See `../pixee-api/SKILL.md` for HAL conventions; do not restate them in scripts.
- When no preferences have ever been set, the command exits 0 with no stdout and writes a
  single line to stderr: `no organization preferences set`. Branch on this for
  fresh-organization flows.

## pixee organization preferences set

```
pixee organization preferences set (--from-file <path> | --content <string>)
```

- Exactly one of `--from-file` or `--content` is required; passing both, or neither, is a
  parse error (exit 1) before any network call.
- `--from-file -` reads `content` from stdin, enabling get-transform-set pipelines.
- Content over 10,000 characters is rejected client-side before the round-trip with the
  observed character count in the error.
- Optimistic concurrency is handled internally: the CLI performs a GET, then PUTs with
  `If-Match: <etag>` (or `If-None-Match: *` on first creation). Agents and scripts never
  touch ETag headers directly.
- On HTTP 412, the CLI exits 1 with a friendly stderr line:
  `concurrent modification: another writer updated organization preferences between read and
  write; re-run to refresh`. Re-running typically succeeds; if multiple writers race
  repeatedly, refresh and re-author against the latest content.
- On success, output mirrors `get` (default header + body in text mode, full record in JSON
  mode).

## Precedence and scope

Pixee resolves preferences per-analysis with strict fallback, no merging:

1. If the repository has `PIXEE.md` at its root (even if empty), it is used exclusively.
2. Else if organization preferences exist with non-empty `content`, they are used.
3. Else the analysis runs without preference guidance.

An empty `PIXEE.md` is a deliberate opt-out: a repo with one is treated as having
preferences, which silently shadows org preferences for that repo. Agents working in a
specific repo should check for `PIXEE.md` before assuming org preferences will apply.

Humans can author preferences in the Pixee web app under an organization's
*Settings → Preferences*; the CLI and the web UI write the same resource.

## Writing effective preferences

Preferences come in three flavors:

- **Remediation guidance.** How the team prefers to fix specific vulnerability classes:
  preferred libraries, internal utility classes, code patterns to use or avoid.
- **Triage context.** Why a finding may not be a real risk here: deployment architecture,
  compensating controls (WAF, network isolation, MFA), intentional patterns, false-positive
  zones.
- **Rule preferences.** Enable or disable specific scanner rules by tool name and rule ID,
  including marking rules as remediable when Pixee should attempt an automatic fix.

For worked examples of each flavor, see [`references/preferences-authoring.md`](references/preferences-authoring.md).
Treat those examples as starting points and adapt them to the org's stack, tone, and
compliance posture.

## Examples

```bash
# Print the body verbatim, suitable for piping into an editor or less
pixee organization preferences get --content-only

# Pretty-print the record as JSON, then pull a single field with jq
pixee organization preferences get --json | jq -r '.updated_by'

# Walk to the canonical resource via HAL (do not hardcode the path)
href=$(pixee organization preferences get --json | jq -r '._links.self.href')
pixee api "$href"

# Author offline and push from a file
pixee organization preferences set --from-file ./pixee-preferences.md

# Compose inline from a heredoc for a quick one-off
pixee organization preferences set --content "$(cat <<'EOF'
# Risk Guidance

## SQL Injection
Prefer Spring NamedParameterJdbcTemplate with :namedParameters.
EOF
)"

# Round-trip through stdin (byte-identical when the transform is a no-op)
pixee organization preferences get --content-only \
  | sed 's/old-vendor/new-vendor/g' \
  | pixee organization preferences set --from-file -

# Retry the set on concurrent-modification conflicts
until pixee organization preferences set --from-file ./pixee-preferences.md; do
  echo "retrying"
  sleep 1
done
```

## Best practices

- Author non-trivial preferences as a file (typically `pixee-preferences.md` in a repo root
  or an internal docs repo) and push with `--from-file`. Reserve `--content` for one-liners
  and shell heredocs.
- Use `--content-only` when piping into editors, diffs, or `less`. Use `--output json` for
  programmatic inspection and HAL traversal.
- When composing preferences with help from external context (Notion pages, internal wikis,
  MCP-connected knowledge bases), draft the candidate document, route it through a human
  owner if the agent does not have authority to set org-wide policy, then push via
  `--from-file` once approved.
- Treat HTTP 412 as expected when multiple agents or humans edit concurrently. The friendly
  retry message is the contract; loop the `set` call or refresh and re-author against the
  latest content.
- Repo-level `PIXEE.md` silently overrides org preferences for that repo. Agents working
  inside a specific repository should check for `PIXEE.md` before assuming the org-level
  document applies.
