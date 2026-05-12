---
name: pixee-finding
description: "List, filter, and view Pixee findings for a scan with aggregate counts across triage, fix, and SCA outcomes."
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee finding --help"
---

# pixee finding

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-scan/SKILL.md` to discover the `--scan` UUID this skill requires.

`pixee finding` lists and views findings produced by a scan. A finding hangs off a single scan and
is not addressable on its own, so every invocation requires `--scan <scan-id>`. Findings carry the
output of every analysis Pixee runs against them — triage, fix, sca — and the CLI inlines the
representative result for each analysis type so an agent rarely needs a second HTTP call.

Before asking the user which repository, branch, scan, or pull request to target, derive that
context from the working environment with whatever facilities the host agent already has — current
directory, git state, PR tooling, project conventions. The user is almost always asking about
findings tied to wherever `cwd` already points. Use `pixee scan list --repo <name-or-uuid>` (with
`--branch` and `--tool` to narrow) to pin down the scan UUID, and only fall back to asking when the
derivation comes back empty or ambiguous.

## pixee finding list

```
pixee finding list --scan <scan-id> [filter flags...]
```

`--scan` is **required**. The response always carries cross-section aggregate counts (triage
status/outcome, fix status/outcome/confidence, sca status/classification, and the composite
`ready_to_fix` / `no_fix_necessary` views) plus, by default, the paginated `items` list with each
item's representative analysis results inlined.

Text output is the aggregate table only — one tab-separated `key\tvalue` row per metric. Items are
not surfaced in text mode; use `--json` to access them. The JSON shape:

- Top-level aggregate fields: `total`, `completed_analysis`, `in_progress_analysis`, `triage`,
  `fix`, `sca`, `composite`, `page`, `_links`.
- `_embedded.items[]` carries the paginated findings (omitted under `--stats`). Each item has
  `id`, `title`, `rule`, `severity` (`{label, rank}`), `html_url`, `_links`, and
  `_embedded["representative-results"]` — a paginated wrapper whose own `_embedded.items[]`
  contains one entry per analysis `type` (`triage`, `fix`, `sca`) with self/finding/analysis links
  and, for fix results, `changesets`, `patches`, and a one-page `latest-patch` shortcut.

Pagination is transparent: the CLI walks every page of findings in one call. Aggregate counts are
page-invariant for a given filter set, so `--stats` (below) returns them in a single HTTP
round-trip.

### `--stats`

```
pixee finding list --scan <scan-id> --stats [filter flags...]
```

Returns aggregate counts only, dropping `_embedded.items`. Sends `page-size=1` over the wire so it
answers questions like "how many critical findings have a completed fix on this scan?" without
streaming the items page. Combine with filter flags below to scope the counts.

### Filter flags

All filters are **repeatable** unless noted, and combine as AND across distinct flags / OR within
the same flag.

- `--severity <label>` — filter by representative severity label.
- `--suggested-severity <label>` — filter by triage's suggested severity label.
- `--min-severity-score <num>` / `--max-severity-score <num>` — bound the severity score (0.0–10.0).
  Not repeatable.
- `--triage-status <s>` — one of `completed`, `failed`, `no-recommendations-available`.
- `--triage-suggested <s>` — one of `true_positive`, `likely_true_positive`, `inconclusive`,
  `false_positive`, `wont_fix`, `blocked`, `excluded`, `not_triaged`.
- `--fix-status <s>` — one of `completed`, `failed`, `no-recommendations-available`, `blocked`,
  `excluded`.
- `--fix-confidence <s>` — one of `high`, `medium`, `low`, `no-rating`.
- `--sca-status <s>` — one of `completed`, `failed`, `blocked`, `excluded`, `not-analyzed`.
- `--sca-classification <s>` — one of `exploitable`, `not-exploitable`, `inconclusive`.
- `--patch-status <s>` — one of `issued`, `merged`.
- `--severity-update <s>` — one of `increased`, `decreased`, `no_update`. Filters by the relation
  between the scanner's severity and Pixee's representative severity.
- `--analyzed` / `--no-analyzed` — restrict to findings whose analysis pipeline is fully complete,
  or the inverse. Mutually exclusive.
- `--view validated` — composite view filter. Currently only `validated` is defined.
- `--query <text>` — case-insensitive search across finding id, title, rule, and file path.
- `--sort <field>` — `pixee-intelligence` (default), `severity`, or `pixee-severity`.
- `--order <asc|desc>` — sort direction. Default `desc`.

## pixee finding view

```
pixee finding view <finding-id> --scan <scan-id>
```

`<finding-id>` is the finding's scan-scoped id, surfaced in `_embedded.items[].id` from
`pixee finding list --json`. `--scan` is **required** — a finding id is only unique within a scan.

Text output prints the finding's headline fields followed by a `Representative Results:` table
with one row per analysis type (`type`, `analyzed_at`, `self_href`). JSON output is the full HAL
representation of the finding (`id`, `title`, `rule`, `severity`, `html_url`, `_links`) with
`_embedded["representative-results"]` already merged in — the same paginated wrapper documented
above. Use this when you need the per-analysis result hrefs (e.g., to walk a fix's `latest-patch`)
without making a second HTTP call.

## Examples

```bash
# How many findings are ready-to-fix on the latest main-branch sonar scan?
scan_id=$(pixee scan list --repo pixee/pixee-platform --branch main --tool sonar --json \
  | jq -r 'sort_by(.imported_at) | reverse | .[0].id')
pixee finding list --scan "$scan_id" --stats --json \
  | jq '.composite.ready_to_fix'

# Critical, fully-analyzed findings with a high-confidence fix, sorted by Pixee severity
pixee finding list --scan "$scan_id" \
  --severity Critical --fix-confidence high --analyzed \
  --sort pixee-severity --json \
  | jq '._embedded.items[] | {id, title, rule, severity}'

# Walk every finding's representative fix result without a second HTTP call per item
pixee finding list --scan "$scan_id" --json \
  | jq '._embedded.items[]
        | {id, fix: ._embedded["representative-results"]._embedded.items[]
            | select(.type=="fix") | ._links}'

# Pull a single finding plus its merged representative results
pixee finding view AZ4JOwsipJDH8099SpHt --scan "$scan_id" --json \
  | jq '._embedded["representative-results"]._embedded.items[] | {type, _links}'

# Chase the latest patch href from a finding view
pixee finding view AZ4JOwsipJDH8099SpHt --scan "$scan_id" --json \
  | jq -r '._embedded["representative-results"]._embedded.items[]
           | select(.type=="fix") | ._links["latest-patch"].href' \
  | xargs pixee api
```

## Best practices

- Derive `--scan` from the working environment first. The host agent already has the user's repo,
  branch, and PR context — pin the scan with `pixee scan list` filtered by `--repo` and `--branch`
  before prompting the user for a UUID.
- Use `--stats` whenever the question is purely aggregate. It drops `_embedded.items`, which can
  be the bulk of the payload on large scans, and answers in one HTTP call.
- The list response inlines `representative-results.latest-patch` on each item. Do not loop
  `pixee finding view` for data that's already on the item; reach for `view` only when you need
  the finding plus its merged result page as a single response.
- Combine filters at the CLI rather than post-filtering in `jq`. The CLI translates filter flags
  into server-side query params, which keeps the items list small and pagination cheap.
- Severity-score and label flags coexist: pass `--severity Critical` plus
  `--min-severity-score 9.0` and both apply. Use `--analyzed` / `--no-analyzed` to slice on
  pipeline completeness rather than re-checking each item's analysis state in `jq`.
- HAL-first when fields are absent. The `_links` on a finding (`results`, `representative-results`)
  and on each result (`analysis`, `changesets`, `patches`, `latest-patch`) are the canonical way to
  reach related resources — follow them with `pixee api <href>` rather than guessing API paths.
  See `pixee-api` for HAL conventions and `--paginate`.
