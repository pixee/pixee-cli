---
name: pixee-migrate-repo-integrations
description: "Move repository integration mappings from an admin console scanner instance to a managed Pixee integration."
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
> handling. Sections used below: `pixee repo integration` and `pixee repo view` in
> `../pixee-repo/SKILL.md`, `pixee integration list` in `../pixee-integration/SKILL.md`,
> `pixee auth status` in `../pixee-auth/SKILL.md`, and following a HAL link with `pixee api` in
> `../pixee-api/SKILL.md`.

A **mapping** binds one repository to one project on a scanner integration (a Sonar project key,
an AppScan application id, and so on). The intended case: an organization configured a scanner in
the admin console, which Pixee lists as a read-only **system** instance (`source: system`, an id
like `sonar-default`), and has since created a **managed** instance in the product
(`source: managed`, a UUID id). Repositories keep using the system instance until their mappings
move. This skill moves the mappings from the system instance to a managed one. Moving between two
managed instances, or back to the system instance, uses the same steps; see **Other directions**.

Change the mappings and leave the repositories alone: deleting a repository cascades to its scans,
SBOMs, patches, and workflows.

Re-pointing a mapping is **delete, then create**. The API has no update (PATCH and PUT answer 405),
a repository holds one mapping per type (a second create answers 409 "Duplicate repository
integration"), and the two calls are not atomic. Every step below exists to make that pair safe.

## 1. Gate on the capability

```bash
pixee repo integration --help
```

Done when the output begins `Usage: pixee repo integration` and lists `create` and `delete` as its
commands. An older binary answers this with the parent `pixee repo` help (usage line
`pixee repo`), which means the feature is missing: upgrade the CLI (install instructions in
`pixee-shared`) and run the gate again.

## 2. Preflight

Confirm the target before any write; a stored credential can be stale or point at another
deployment.

```bash
pixee auth status --json
```

Record `server` and the `identity` of the credential in use (`credentialInUse`). Both go into the
plan at the approval gate, where the user confirms them. Create a scratch directory outside any
repository checkout for this run and tell the user its path.

## 3. Resolve the integrations

`<type>` is the scanner type to migrate (`sonar`, `appscan`, `black-duck-hub`, and so on).

```bash
pixee integration list --type <type> --json \
  | jq 'map({id, name, source, health, webhook_secret_configured, self: ._links.self.href})'
```

Zero integrations for a type the user expects is a stop-and-ask, not a success.

The **old** integration is the one with `source: "system"`; the **new** one is a
`source: "managed"` integration. When several managed instances exist, show their names and ask the
user to choose. When the user names other instances, use those. A type with no system instance
(`black-duck-hub` and `checkmarx-enterprise` have no default instance) goes through **Other
directions**.

Check every **new** integration before planning, because a failed create after a delete is the
expensive failure. `health` of `{"status": "healthy", ...}` is good; report anything else to the
user, who decides at the approval gate whether to go on.

Sonar and AppScan scanners call back into Pixee, which adds two items. Report
`webhook_secret_configured: false` on the new instance as a side finding. Then, whatever that field
says, tell the user the scanner must be pointed at the managed instance's own webhook address
(shown when the instance was set up) and ask them to confirm it is; the CLI cannot check the
scanner side.

Accept one of two inputs:

- **System to managed.** Every mapping of `<type>` that points at the system instance moves to the
  new one. This is the default.
- **Explicit map.** The user supplies repository to integration pairs. Resolve each repository to a
  UUID by exact `full_name` or `name` match in `pixee repo list --json` (the protocol in
  `pixee-repo`) and stop on an ambiguous or missing match. Move exactly those repositories, each to
  its own integration, and leave every other mapping alone.

`repository_count` in `integration list` reads 0 for these integrations, so it cannot find
mappings. Enumerate through repositories (step 4).

## 4. Enumerate mappings

`pixee repo view` takes a UUID. Get UUIDs from `pixee repo list --json`. Read every repository, or
only those in the explicit map.

A mapping's integration is its `_links.integration.href`. Hrefs are opaque; compare them for
**equality** against each integration's own `_links.self.href` from step 3 and read no id out of
one. Fetch the integration list once and reuse it for every repository:

```bash
ints=$(pixee integration list --json)
pixee repo view <repo-uuid> --expand repository-integrations --json \
  | jq --argjson ints "$ints" --arg repo <repo-uuid> '._embedded."repository-integrations"[]
      | ._links.integration.href as $h | del(._links)
      | . + {repository: $repo,
             integration: (first($ints[] | select(._links.self.href == $h) | .id)
                           // "UNMATCHED " + $h)}'
```

Each output record is a whole mapping plus its repository and integration id. Keep the records whose `type` is the
migrating type. An `UNMATCHED` integration names a mapping whose integration is missing from the
list: report it at the approval gate and leave it alone. No output means the repository has no
mappings. Zero mappings of a type the user expected is a stop-and-ask.

Done when every repository has been read and every mapping of the type is paired with its current
integration. Every target identifier comes from that mapping's record.

## 5. Approval gate

Show the human the complete plan: the server and identity from step 2, then one row per mapping
with repository, mapping id, type, **every** identifier field the record carries, old integration,
new integration, and the new integration's `type` and `health`. State that each move is delete then
create and is not atomic. **Wait for explicit approval.** Write nothing to Pixee before it.

Save the approved plan in the scratch directory; a resumed run needs it.

## 6. Migrate one repository, then the rest

Run the loop for a single repository first and verify it. Continue with the remainder only after
that repository passes. Stop at the first failure of any kind. Skip a repository whose mapping
already shows the new integration.

For each repository:

1. **Snapshot.** Save the repository's mappings and its scan count to the scratch directory and
   keep them until the audit passes. A snapshot is write-once: when the file exists, go to
   **Resuming an interrupted run** instead of overwriting it.
   ```bash
   pixee repo view <repo-uuid> --expand repository-integrations --json \
     > <scratch>/snapshot-<repo-uuid>.json
   pixee --json api "$(jq -r '._links.scans.href' <scratch>/snapshot-<repo-uuid>.json)" \
     | jq .total > <scratch>/scans-<repo-uuid>.txt
   ```
   Done when the snapshot is non-empty, parses as JSON, and contains the mapping about to be
   deleted, and the count file holds a number. The scans link answers with the first page and a
   `total`, so the count costs one request however many scans the repository has; `pixee scan list`
   would download every scan. With no writable filesystem, print the snapshot (it holds no
   credentials) and the count to the user instead; resuming then depends on that transcript.
2. **Delete** the old mapping: `pixee repo integration delete <repo-uuid> <mapping-id>`.
3. **Create** it on the new integration with the same target identifier, and every optional
   identifier the snapshot holds (for example Veracode's `--sandbox-guid`); flags are in the table
   below:
   `pixee repo integration create <type> <repo-uuid> --<identifier-flag> <value> --integration-id <new-id>`.
   Pass `--integration-id` for a managed instance. For the system instance, omit the flag: the CLI
   rejects the system instance's id (for example `sonar-default`) with "Unknown integration", and
   omitting the flag selects it. Touch only the mapping of the migrating type.
4. **Verify.** Re-read the repository. The mapping shows the new integration href, every
   identifier equals the snapshot, and the scan count is at least the snapshot count. Scans can
   arrive during the move, so an increase is fine. The mapping id changes on re-create; that is
   expected. When the count drops, stop and tell the user: rollback restores the mapping, not scans.

### Resuming an interrupted run

A session can die between a delete and its create. Before continuing, re-read the scratch
directory, the saved plan, and each repository's live mappings, and compare them to the snapshots.
Stop and ask the user when the scratch directory or the saved plan is missing.

- Snapshot exists, live repository has no mapping of the type: an interrupted move. Restoring the
  deleted mapping is permitted without a new approval: recreate it from the snapshot as under
  **When create fails after delete**, tell the user, and ask whether to continue the migration.
- Snapshot exists, live mapping equals the snapshot: not yet moved; continue the loop at step 2.
- Snapshot exists, live mapping shows the new integration with the snapshot's identifiers: moved;
  skip it.
- Anything else, including no snapshot and no mapping, a mapping on a third integration, or
  identifiers that differ from the snapshot: stop and ask the user.

### When create fails after delete

The repository now has no mapping. Recreate the old one from the snapshot: same identifiers and
the old integration, with `--integration-id` handled as in step 3 of the loop. Then re-verify the
repository as in step 4 of the loop (the mapping id will differ from the snapshot) and tell the
user what failed and where you stopped. When the rollback create also fails, tell the user
immediately with the repository, the snapshot path, and the identifiers.

## 7. Audit

After the last repository, re-enumerate every repository as in step 4, including any `UNMATCHED`
rows. Done when no mapping of the type points at the old integration (apart from repositories the
explicit map excluded), no `UNMATCHED` mapping is new, and every target identifier matches its
snapshot.

## 8. Report

Tell the user, in this order: outcome, repositories moved, anything that failed or was rolled
back, what was not verified, side findings (report only; leave them unfixed). Findings and scan
attribution were not compared, only mappings and scan counts; suggest the user spot-check one
migrated repository in the UI. State that the **system instance is still in place**: it is
read-only and disappears when the operator retires the admin console configuration, and removing
anything else is the user's decision.

## Other directions

- **Managed to managed.** Same steps; the old integration is the one the user names, and the new
  one is passed with `--integration-id`.
- **Managed back to the system instance.** Same steps; create without `--integration-id`.
- **A type with no system instance.** The old integration is the one the user names.

## Create flags by type

`--integration-id <id>` is optional on every type except `black-duck-hub` and
`checkmarx-enterprise`, which have no default instance. Omitting it selects the type's system
instance.

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

Each flag mirrors a field on the mapping record (`--project-key` is `project_key`). The
`create <type> --help` output is the final word on flags.
