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
an AppScan application id, and so on). The intended case: an organization configured a scanner in
the admin console, which Pixee shows as a read-only **system** instance (named like "Sonar (admin
console)", `source: system`, id like `sonar-default`), and now has a **managed** instance created in
the product (named like "SonarQube Cloud", `source: managed`, a UUID id). Repositories keep using
the system instance until their mappings are moved, and the system instance goes away when the
admin console is retired. This skill moves the mappings from the system instance to a managed one.
Moving between two managed instances, or back to the system instance, uses the same steps; see
**Other directions**.

Change the mappings and leave the repositories alone: deleting a repository cascades to its scans,
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
deployment. Create a scratch directory outside any repository checkout for this run and tell the
user its path. Scratch files are not "writes" for the approval gate; only `pixee` calls that change
Pixee are.

```bash
pixee auth status
pixee --json api /api/v1/users/me | jq '{login, roles}'
```

Record the server and the identity; they go into the plan at the approval gate, which is where the
user confirms them. Never print or echo a token.

## 3. Resolve the integrations

`<type>` is the scanner type the user wants to migrate (`sonar`, `appscan`, and so on). Ask when it
is not clear. List that type's integrations by filtering in `jq`, which also works for
`black-duck-hub` and `checkmarx-enterprise`, types the `--type` flag of `integration list` does not
accept:

```bash
pixee integration list --json | jq '[.[] | select(.type == "<type>")]
  | map({id, name, source, health, webhook_secret_configured, self: ._links.self.href})'
```

Zero integrations for a type the user expects is a stop-and-ask, not a success.

Take the **old** integration to be the one with `source: "system"` and the **new** one to be a
`source: "managed"` integration. When several managed instances exist, show their names and ask
which one; never guess. If the user names different instances, use theirs.

Check every **new** integration before planning, because a failed create after a delete is the
expensive failure. Its `type` must equal the mapping type. `health` of `{"status": "healthy", ...}`
is good; anything else you report to the user, who decides at the approval gate whether to go on.
Read `webhook_secret_configured` too and report `false` as a side finding.

For webhook-driven types (Sonar, AppScan), a managed instance has its own webhook address, shown in
its setup form in the product, and the scanner must be pointed at it. Tell the user this before the
approval gate and ask them to confirm the scanner side is handled; the CLI cannot check it.

Accept one of two inputs:

- **System to managed.** Every mapping of `<type>` that points at the system instance moves to the
  new one. This is the default.
- **Explicit map.** The user supplies repository to integration pairs. Resolve each repository to a
  UUID with `pixee repo list --name <name> --json` and stop on an ambiguous or missing match. Move
  exactly those repositories, each to its own integration; leave every other mapping alone. A pair
  that names the system instance is created without `--integration-id` (see step 6).

`repository_count` in `integration list` reads 0 for these integrations, so it cannot find
mappings. Enumerate through repositories (step 4).

## 4. Enumerate mappings

`pixee repo view` takes a UUID. Get UUIDs from `pixee repo list --json`; the explicit map names the
repositories to read, and otherwise read every repository. Run the following for each one.

A mapping's integration is its `_links.integration.href`. Hrefs are opaque; never parse an id out
of one. Match by **equality** against each integration's own `_links.self.href` from step 3. The
integration list goes in as a jq argument, so no file is needed:

```bash
pixee repo view <repo-uuid> --expand repository-integrations --json \
  | jq --argjson ints "$(pixee integration list --json)" '
      ._embedded."repository-integrations"[] | select(.type == "<type>")
      | ._links.integration.href as $h
      | {mapping: .id, project_key,
         integration: (first($ints[] | select(._links.self.href == $h) | .id) // "UNMATCHED " + $h)}'
```

Swap `project_key` for the type's identifier fields; the text view of `repo view` lists each
mapping's identifiers as `name=value`. Copy the mapping's `type` string from this output; the
`create` subcommand name can differ from it. An `UNMATCHED` integration is a mapping whose
integration is not in the list: report it at the approval gate and leave it alone. Without the
fallback, jq silently drops it. Zero mappings found for a type the user expected is a stop-and-ask.

Done when every repository has been read and every mapping of the type is paired with its current
integration. Every target identifier (project key, application id, and so on) comes from that
mapping's JSON; never invent or edit one.

## 5. Approval gate

Show the human the complete plan: the server and identity from step 2, then one row per mapping
with repository, mapping id, type, **every** identifier field the mapping carries, old integration,
new integration, and the new integration's `type` and `health`. State that each move is delete then
create and is not atomic. **Wait for explicit approval.** Write nothing to Pixee before it.

## 6. Migrate one repository, then the rest

Run the loop for a single repository first and verify it. Continue with the remainder only after
that repository passes. Stop at the first failure of any kind. Skip a repository whose mapping
already shows the new integration.

For each repository:

1. **Snapshot.** Save the repository's mappings and the scan count to the scratch directory and
   keep every snapshot until the audit passes. A snapshot is write-once: if the file already
   exists, do not overwrite it; go to **Resuming an interrupted run** first.
   ```bash
   pixee repo view <repo-uuid> --expand repository-integrations --json \
     > <scratch>/snapshot-<repo-uuid>.json
   pixee scan list --repo <repo-uuid> --json | jq length   # record beside the snapshot
   ```
   Snapshots are what survive a dead session, so they need somewhere durable. With no writable
   filesystem, print each snapshot (mapping JSON holds no credentials) and the scan count to the
   user instead; resuming then depends on that transcript.

   The scan count pages through every scan, so it is slow on repositories with thousands. It only
   has to match before and after.
2. **Delete** the old mapping: `pixee repo integration delete <repo-uuid> <mapping-id>`.
3. **Create** it on the new integration with the same target identifier, and every optional
   identifier the snapshot holds (for example Veracode's `--sandbox-guid`); flags are in the table
   below:
   `pixee repo integration create <type> <repo-uuid> --<identifier-flag> <value> --integration-id <new-id>`.
   Under an explicit map, `<new-id>` is that repository's own entry. Touch only the mapping of the
   migrating type; leave the repository's other mappings alone.
4. **Verify.** Re-read the repository. The mapping now shows the new integration href, every
   identifier equals the snapshot, and the scan count is at least the snapshot count. Scans can
   legitimately arrive during the move, so an increase is fine; a decrease is a failure. The
   mapping id changes on re-create; that is expected.

Deleting a mapping did not cascade to scans in the observed migrations. If a count ever drops, stop
and tell the user: rollback restores the mapping, not scans.

### Resuming an interrupted run

A session can die between a delete and its create. Before continuing a previous run, re-read the
scratch directory and each repository's live mappings, and compare them to the snapshots:

- Snapshot exists, live repository has no mapping of the type: an interrupted move. Recreate it
  from the snapshot (see below) before doing anything else, then tell the user.
- Snapshot exists, live mapping matches the snapshot: not yet moved; continue the loop at step 2.
- Snapshot exists, live mapping shows the new integration: already moved; skip it.
- No snapshot and no mapping of the type: stop and ask the user. The record of the old identifier
  may be gone.
- Scratch directory missing: stop and ask the user before touching anything.

### When create fails after delete

The repository now has no mapping. Recreate the old one from the snapshot: same identifiers and
the old integration's id. Omit `--integration-id` when the old integration is the system instance;
the CLI rejects its id (for example `sonar-default`) with "Unknown integration", and omitting the
flag selects it. Then re-verify the repository as in step 6.4 (the mapping id will differ from the
snapshot) and tell the user what failed and where you stopped. When the rollback create also fails,
tell the user immediately with the repository, the snapshot path, and the identifiers.

## 7. Audit

After the last repository, re-enumerate every repository as in step 4, including any `UNMATCHED`
rows. Done when no mapping of the type points at the old integration (apart from repositories the
explicit map excluded), no `UNMATCHED` mapping is new, and every target identifier matches its
snapshot.

## 8. Report

Tell the user, in this order: outcome, repositories moved, anything that failed or was rolled
back, what was not verified, side findings (for example a missing webhook secret; report these,
do not fix them). Findings and scan attribution were not compared, only mappings and scan counts;
suggest the user spot-check one migrated repository in the UI. State that the **system instance is
still in place**; it cannot be removed in the product and goes away only when the admin console is
retired, which is the operator's call.

## Other directions

- **Managed to managed.** Same steps; the old integration is the one the user names, and the new
  one is passed with `--integration-id`.
- **Managed back to system.** Create without `--integration-id`; the CLI rejects the system
  instance's id.

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
