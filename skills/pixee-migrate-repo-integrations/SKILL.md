---
name: pixee-migrate-repo-integrations
description: "Migrate repository integration mappings from one Pixee scanner integration to another while keeping scans and history."
license: Apache-2.0
compatibility: Requires the pixee CLI binary on PATH
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee repo integration --help"
---

# Migrate repository integration mappings

> **PREREQUISITES:** Read `../pixee-shared/SKILL.md` for global flags, exit codes, and error
> handling, `../pixee-repo/SKILL.md` for `repo view`, `repo list`, and `repo integration`, and
> `../pixee-integration/SKILL.md` for `integration list`. HAL link semantics live in
> `../pixee-api/SKILL.md`.

A **mapping** binds one repository to one project on a scanner integration (a Sonar project key,
an AppScan application id, and so on). To move repositories from integration A to integration B,
change the mappings and leave the repositories alone: deleting a repository cascades to its scans,
SBOMs, patches, and workflows.

Re-pointing a mapping is **delete, then create**. The API has no update (PATCH and PUT answer 405),
a repository holds one mapping per type (a second create answers 409 "Duplicate repository
integration"), and the two calls are not atomic. Every step below exists to make that pair safe.

## 1. Gate on the capability

```bash
pixee repo integration --help
```

Continue when this lists `create` and `delete`. When the command is unknown, upgrade the CLI first
(install instructions in `pixee-shared`) and run the gate again. Trust `--help` over this skill for
flag names.

## 2. Preflight

Confirm the target before any write; a stored credential can be stale or point at another
deployment.

```bash
pixee auth status
pixee --json api /api/v1/users/me | jq '{login, roles}'
```

Tell the user which server and which identity the migration will run as. Continue when the server
is the one they intend. Never print or echo a token.

## 3. Resolve the integrations

```bash
pixee integration list --type <type> --json > integrations.json
```

Pick the **old** and **new** integrations by `id`. When the user's wording does not identify one
unambiguously, show the candidates and ask.

Accept one of two inputs:

- **Old to new.** Every mapping of `<type>` that points at the old integration moves to the new one.
- **Explicit map.** The user supplies repository to integration pairs. Move exactly those
  repositories; leave every other mapping alone.

`repository_count` in `integration list` reads 0 for these integrations, so it cannot find
mappings. Enumerate through repositories (step 4).

## 4. Enumerate mappings

`pixee repo view` takes a UUID. Get UUIDs from `pixee repo list --json`, then for each repository:

A mapping's integration is its `_links.integration.href`. Hrefs are opaque; never parse an id out
of one. Match by **equality** against each integration's own `_links.self.href` from
`integrations.json`:

```bash
pixee repo view <repo-uuid> --expand repository-integrations --json \
  | jq --slurpfile ints integrations.json '$ints[0] as $I
      | ._embedded."repository-integrations"[] | select(.type == "<type>")
      | ._links.integration.href as $h
      | {mapping: .id, project_key, integration: ($I[] | select(._links.self.href == $h) | .id)}'
```

Swap `project_key` for the type's identifier field; the text view of `repo view` lists each
mapping's identifiers as `name=value`. Done when every repository has been read and every mapping of the type is paired with its current
integration. Every target identifier (project key, application id, and so on) comes from that
mapping's JSON; never invent or edit one.

## 5. Approval gate

Show the human the complete plan, one row per mapping: repository, mapping id, type, target
identifier, old integration, new integration. State that each move is delete then create and is
not atomic. **Wait for explicit approval.** Write nothing before it.

## 6. Migrate one repository, then the rest

Run the loop for a single repository first and verify it. Continue with the remainder only after
that repository passes. Stop at the first failure of any kind.

For each repository:

1. **Snapshot.** Save the mapping's full JSON and the scan count.
   ```bash
   pixee repo view <repo-uuid> --expand repository-integrations --json > snapshot-<repo-uuid>.json
   pixee scan list --repo <repo-uuid> --json | jq length
   ```
2. **Delete** the old mapping: `pixee repo integration delete <repo-uuid> <mapping-id>`.
3. **Create** it on the new integration with the same target identifier (flags in the table below):
   `pixee repo integration create <type> <repo-uuid> --<identifier-flag> <value> --integration-id <new-id>`.
   Under an explicit map, `<new-id>` is that repository's own entry. Touch only the mapping of the
   migrating type; leave the repository's other mappings alone.
4. **Verify.** Re-read the repository. The mapping now shows the new integration href, the
   identifier equals the snapshot, and the scan count equals the snapshot count. The mapping id
   changes on re-create; that is expected.

Deleting a mapping did not cascade to scans in the observed migrations. Verify the count per
repository rather than assuming it.

### When create fails after delete

The repository now has no mapping. Recreate the old one from the snapshot: same identifier and
the old integration's id, then tell the user what failed and where you stopped. Omit
`--integration-id` when the old integration is the system default; the CLI rejects the default's
id (for example `sonar-default`) with "Unknown integration", and omitting the flag selects the
default. The same rule applies when the *new* integration is the system default.

## 7. Audit

After the last repository, re-enumerate every repository as in step 4. Done when no mapping of the
type points at the old integration (apart from repositories the explicit map excluded) and every
target identifier matches its snapshot.

## 8. Report

Tell the user, in this order: outcome, repositories moved, anything that failed or was rolled
back, side findings (for example a missing webhook secret; report these, do not fix them). State
that the **old integration is still in place**; removing it is the user's decision.

## Create flags by type

`--integration-id <id>` is optional on every type except `black-duck-hub` and
`checkmarx-enterprise`, which have no default instance. Omitting it selects the type's system
default instance.

| Type | Subcommand | Identifier flags |
| ---- | ---------- | ---------------- |
| Sonar | `create sonar` | `--project-key` |
| AppScan | `create appscan` | `--application-id` |
| Arnica | `create arnica` | `--asset-key` |
| Black Duck Hub | `create black-duck-hub` | `--project-id`, `--version-id`, plus required `--integration-id` |
| Checkmarx | `create checkmarx` | `--project-id` |
| Checkmarx Enterprise | `create checkmarx-enterprise` | `--project-id` (integer), plus required `--integration-id` |
| Datadog | `create datadog` | `--repository-id` |
| Polaris | `create polaris` | `--polaris-project-id` |
| Veracode | `create veracode` | `--application-guid`, optional `--sandbox-guid` |

Each flag mirrors a field on the mapping record (`--project-key` is `project_key`). Run
`pixee repo integration create <type> --help` before the first create of a type.
