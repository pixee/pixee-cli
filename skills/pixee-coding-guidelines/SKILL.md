---
name: pixee-coding-guidelines
description: "List Pixee organization coding-guidelines documents to discover their filename, status, and size for fix guidance."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee organization coding-guidelines --help"
---

# pixee organization coding-guidelines

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, and `../pixee-auth/SKILL.md` if authentication needs to be configured. See
> `../pixee-preferences/SKILL.md` for the sibling `organization preferences` resource — a
> freeform markdown blob, distinct from the uploaded documents this skill lists.

Coding-guidelines documents are organization-level files (style guides, security standards,
internal conventions) that the Pixee platform can apply alongside org preferences when
generating fixes. Unlike `pixee organization preferences`, which manages a single freeform
markdown blob inline, coding-guidelines are a set of uploaded documents, each with its own
filename and processing status.

## pixee organization coding-guidelines list

```
pixee organization coding-guidelines list
```

No flags beyond the global ones. Pagination is transparent — the CLI walks every page in one
call.

Text output is tab-separated with columns `display_name`, `filename`, `status`, `size`, `id`.
Use `--output json` (or `--json`) for the full HAL record per document.

## Examples

```bash
# List every coding-guidelines document for the organization
pixee organization coding-guidelines list

# Machine-readable listing piped to jq
pixee organization coding-guidelines list --json | jq '.[] | {display_name, status}'

# Find documents that failed processing
pixee organization coding-guidelines list --json | jq '.[] | select(.status != "ready")'
```

## Best practices

- Check `status` before assuming a recently uploaded document is already in effect — processing
  is asynchronous, and a document in a non-ready state won't yet influence fix generation.
- This skill only lists documents; uploading, replacing, or deleting a coding-guidelines document
  is done through the Pixee web app or the API directly. See `pixee-api` for the HAL-first
  discovery pattern if scripting against those endpoints.
- Don't conflate this resource with `pixee organization preferences` (see `pixee-preferences`):
  preferences are one inline markdown blob; coding-guidelines are a set of uploaded documents.
