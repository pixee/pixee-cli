---
name: add-resource-skill
description: Authors a new skills.sh-formatted skill for the pixee CLI under skills/pixee-<noun>/SKILL.md. Trigger on requests like "add a resource skill", "write a skill for pixee X", "author a pixee skill", or "publish a skill for the new Y subcommand". Captures pixee-specific conventions (one skill per sub-command with a shared prerequisite, frontmatter schema, picker-friendly descriptions, HAL-first doctrine, sibling cross-references) and defers to /plugin-dev:skill-development for general skill-writing craft. Also covers updates to existing skills under skills/pixee-*.
---

# Author a Pixee CLI Resource Skill

Guided authoring of a new skill under `skills/pixee-<noun>/SKILL.md`. This repo distributes the skills that teach coding agents (Claude Code, Codex, others) to drive the `pixee` binary. Consistency across siblings is load-bearing for discoverability and the skills.sh install picker.

For general skill-writing fundamentals (what a SKILL.md is, progressive disclosure, how triggering works), invoke `/plugin-dev:skill-development` first if available. This skill layers pixee conventions on top; it does **not** repeat them. If that plugin is not installed, a one-paragraph refresher: a SKILL.md is a Markdown file with YAML frontmatter; the `description` field is how the model decides to invoke it, so it must enumerate concrete trigger phrases; keep the body scannable with clear H2 sections; front-load the most common use case.

## Pixee context you must know

- **Skills modularize around sub-commands.** One skill per top-level `pixee <subcommand>` plus a single shared prerequisite skill (`pixee-shared`) that every domain skill references. This keeps each skill scoped to what an agent needs for one command group, and lets the install picker present a small menu of composable pieces.
- **Install channel.** Skills are fetched by agents via `npx skills add pixee/pixee-cli --all` (or the interactive picker without `--all`). A picker-breaking `description` silently drops the skill from the picker.
- **Release cadence.** Skill iteration is decoupled from `pixee` binary releases — revise a skill without waiting for the next CLI tag, and ship a subcommand now and its skill later if the surface isn't finalized.
- **`pixee-shared` is a hard prerequisite** for every domain skill. It covers global flags, exit codes, error rendering, and token security.
- **`pixee-api` is the canonical HAL reference.** Cross-reference it for discovery guidance. Never restate HAL. Never embed OpenAPI specs or long JSON schemas.

## Before you author

The `pixee` binary on PATH is the authoritative source for what a skill should teach. Everything in the skill you write must be something you've seen the binary actually do.

1. **Study the CLI by invoking it.** Start with `pixee --help` for the top-level surface; then `pixee <subcommand> --help` and each nested `pixee <subcommand> <verb> --help`. Run realistic invocations end-to-end: try each flag, observe exit codes, run `--output text` and `--output json` against the same call to see the shape difference, and follow HAL links with `pixee api <href>` where the endpoint exposes them. Do not document flags or behaviors you haven't seen the binary produce.
2. **Read two files in full:** `skills/pixee-shared/SKILL.md` (every domain skill references it) and the **single** sibling closest to the new domain — the skill whose H1 shape you will copy. For a command-backed list/CRUD surface, `pixee-repo` (single verb) or `pixee-workflow` (subcommand-per-variant) is almost always the right reference.
3. **Decide the slot.** New `pixee-<noun>` skill versus extending an existing one. Prefer extension when the new surface is fewer than three subcommands and lives naturally inside an existing skill's H1 (e.g., a new `pixee api --new-flag` belongs in `pixee-api`, not a new skill).

## Naming rules

- Slug is `pixee-<noun>` in kebab-case, where `<noun>` is a top-level subcommand or a cross-cutting concern (`shared` is the only current exception). Non-command cross-cutting slugs need discussion before landing.
- Directory layout: `skills/pixee-<noun>/SKILL.md` — single file. No `references/` sidecar unless the skill exceeds ~150 lines; inline is the default.
- The H1 matches the command surface (`# pixee workflow`) or the skill name (`# Pixee CLI — Shared Reference`).

## Frontmatter template

Copy this exactly and fill in the angle-bracket placeholders:

```yaml
---
name: pixee-<noun>
description: "<verb-first, 100-130 chars, no colons, em-dashes, or parens>"
metadata:
  version: 1.0.0
  openclaw:
    category: "developer-tools"
    requires:
      bins:
        - pixee
    cliHelp: "pixee <subcommand> --help"
---
```

The `description` has a triple constraint, each one load-bearing:

- **(a) Verb-first, bare infinitive.** Existing descriptions start with `Describe`, `Store`, `Send`, `List`, `List, create, and delete`. Match the shape — this is what the skills.sh picker renders well.
- **(b) Describes *what* the skill covers, not *how* it works.** "List Pixee repositories and resolve names to UUIDs" is right. "Runs `pixee repo list` and does name resolution via the API" is wrong.
- **(c) No colons, em-dashes, or parentheses.** They break the skills.sh picker silently. Commit `f0e73a3` (ISS-6922) rewrote all five existing descriptions for exactly this reason. Length: 100–130 chars.

`version` stays `1.0.0` until we agree to start bumping. Don't invent a scheme.

`cliHelp` is `pixee <subcommand> --help` for command-backed skills; `pixee --help` for cross-cutting skills like `pixee-shared`.

## Structural template

Don't try to invent shape. Open the closest sibling and follow its skeleton. Every skill in the set shares these invariants:

1. **PREREQUISITE blockquote immediately after the frontmatter.** Singular `> **PREREQUISITE:**` when only `pixee-shared` is referenced (see `pixee-api`, `pixee-repo`); plural `> **PREREQUISITES:**` when multiple are referenced (see `pixee-workflow`, which references shared + auth + repo).
2. **Reference rule.** Always reference `pixee-shared` first. Add `pixee-auth` when the subcommand authenticates (i.e., almost always, but only call it out when the skill's own content touches credential failure modes). Add `pixee-repo` when the skill uses the `--repo` name-or-UUID resolution protocol.
3. **H2 per subcommand or topic.** `pixee-workflow` shows the subcommand-per-H2 pattern; `pixee-shared` shows the topic-per-H2 pattern. Pick the one that matches your surface.
4. **Bash examples with inline comments**, realistic repo names (`pixee/pixee-platform`), and at least one example showing `--json` piped into `jq`.
5. **Best practices tail.** Short bulleted section covering scripting guidance: UUID vs name tradeoffs, pagination, mutually-exclusive flags, when to prefer the subcommand over the `pixee api` escape hatch.

## Content doctrine

- **Self-contained.** Don't assume the agent read anything beyond `pixee-shared`.
- **Cross-reference `pixee-api` for HAL.** Never embed OpenAPI specs or long JSON schemas in the body.
- **Mirror API field names in flag docs.** Don't invent CLI aliases. If the API field is `branch_pattern`, the flag is `--branch` or `--branch-pattern` — not `--branch-regex` or `--on-branch`.
- **Examples must work in both text and json output modes.** Show the `--json | jq` path at least once.
- **Audience is Claude Code *and* Codex (and future agents).** Avoid Anthropic-specific phrasing ("ask Claude to…"). Write to "the agent."

## After you author

1. **Update `README.md`.** Add a bullet under `## Coding agent skills` matching the shape of the existing five bullets:
   ```markdown
   - [`pixee-<noun>`](./skills/pixee-<noun>/SKILL.md) — <one-line description matching the frontmatter>.
   ```
2. **License.** The `skills/` directory is Apache-2.0 via `skills/LICENSE`. No per-file header. `skills/NOTICE` stays untouched unless the new skill pulls in third-party attributions (unlikely for documentation).
3. **Commit style.** Follow recent history: short imperative + issue tag, e.g. `Add pixee-scan skill (ISS-XXXX)`. Use a fresh issue number — ISS-6922 is closed.
4. **Picker smoke test.** Run `npx skills add pixee/pixee-cli` (no `--all`) and confirm the new entry appears in the interactive picker with its full description visible. If it's missing, the `description` has picker-breaking characters — fix before landing.

## Updating an existing skill

Same rules, applied on the edit:

- Preserve the description's verb-first, picker-friendly shape on any rewrite. A rewrite that introduces a colon or em-dash is a picker regression, not a prose polish.
- Keep `version` decisions consistent across siblings. Don't bump one skill's version in isolation — the set moves together or stays.
- Don't diverge PREREQUISITE phrasing from the rest of the set in a single-skill edit. If the convention needs to change, update all five siblings in one commit.

## Anti-patterns

- Emojis or Unicode punctuation in `description` — break the picker silently.
- Copy-pasting exit-code or global-flag content from `pixee-shared` instead of cross-referencing it.
- Hardcoded API paths or embedded OpenAPI fragments — violates HAL-first doctrine and dates fast.
- Anthropic-Claude-Code-specific phrasing. The skills serve Codex and others too.
- Per-file license headers. `skills/LICENSE` covers the directory.
