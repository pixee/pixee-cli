---
name: audit-skills
description: "Detects and closes drift between the latest released Pixee CLI surface and the published `skills/pixee-*` skills on `origin/main`. Trigger after a new pixee release, on a `/audit-skills` request, or when the contributor asks 'are the skills up to date?', 'is there a missing pixee skill?', 'does the CLI match the skills?', 'check skill drift', or 'do we need to update the skills for vX.Y.Z?'. Always audits against `origin/main` (the source of truth for what users see), never the local working tree. Produces a structured drift report first, then closes the highest-severity gap in a pull request. Accepts `--headless` for unattended post-release runs."
---

# Audit Pixee CLI Skills for Drift

A maintenance workflow that compares the **live `pixee` binary on PATH** (the release the contributor actually shipped) against the **published `skills/pixee-*/SKILL.md` on `origin/main`** (what users actually pull via `npx skills add pixee/pixee-cli`), then closes the most severe gap it finds in a pull request.

The skills shipped from this repo (`pixee/pixee-cli`) teach coding agents to drive `pixee`. Whenever a new subcommand, verb, or flag lands in the CLI without a corresponding skill update, agents silently fall back to guessing — that is what this skill exists to prevent.

## When to run

- Right after a new `pixee` release — the canonical trigger, paired with `--headless` if you want a hands-off run.
- Ad-hoc when a contributor suspects drift after merging a `pixee-cli-private` PR that adds a subcommand or flag.
- As a scheduled CI job or cloud coding agent, paired with `--headless`, closing one gap per run.

`pixee` must be on `PATH` and must point at the release the contributor wants to audit. If `pixee --version` does not match the latest tag on `pixee/pixee-cli`, stop and ask the contributor whether to upgrade first (skip the prompt under `--headless` — note the version mismatch in the report and proceed).

**A binary that will not run ends the audit.** `pixee <cmd> --help` is the only evidence this skill accepts for what the CLI exposes. If `pixee --version` fails for any reason (not installed, wrong architecture, no network to fetch a release), stop and report that. Never reconstruct a CLI surface from this repo's own skills, from a changelog, or from memory: the whole point of the audit is to compare the skills against something independent of them, and substituting a remembered surface inverts the result into a report that confirms whatever the skills already say.

## Hard rules

1. **Map skills to subcommands by `cliHelp`, not by slug.** The skill that covers `pixee organization preferences` is called `pixee-preferences`, not `pixee-organization`. Skill slugs are stable across renames; CLI subcommand names evolve, so joining by slug silently diverges as the surface moves. Read each skill's frontmatter `cliHelp` field (`cliHelp: "pixee <subcommand> --help"`) to learn what it covers; only use slug as a tiebreaker for cross-cutting skills like `pixee-shared`.
2. **Audit first, remediate second.** Never edit a `skills/pixee-*/SKILL.md` before producing the drift report and getting approval. Under `--headless` the report is the approval — remediate immediately after producing it. Editing before the report means the report describes work already done, which is how a run talks itself into a gap that was never there.
3. **One gap per run.** Close the single highest-severity gap: category A or E first, then B, then C or D, breaking ties by the busier subcommand. Authoring several unrelated skills in one branch produces a diff no reviewer will read closely, which is how drift gets replaced by wrong content.
4. **`pixee --help` is the binary's source of truth.** Skill content is correct when it matches the help output of the binary on `PATH`.
5. **Don't invent skills.** When a CLI surface is small and naturally belongs inside an existing skill, **extend** the sibling rather than adding a new `pixee-<noun>` skill. See `.claude/skills/add-resource-skill/SKILL.md` for the slot-decision rule.

## Headless mode

Pass `--headless` for unattended runs (post-release CI, scheduled cron). The skill behaves the same except:

- **No `AskUserQuestion` calls.** Decisions that would normally prompt the contributor (e.g., "is this surface big enough to warrant its own skill?") default to the most defensible choice; the choice is recorded explicitly in the pull request description so the reviewer can correct it.
- **No "confirm to remediate" stop.** The audit phase runs, the report is produced, and remediation proceeds without waiting for approval.
- **Notification at the end.** Notify the user with the audited version and the pull request URL.
- **Version mismatch is a warning, not a stop.** If `pixee --version` lags `origin/main`'s latest tag, note it in the report header and proceed. A human can decide whether to act on the report.

Interactive mode is the default. When in doubt, ask.

## Workflow

Track these as an explicit checklist from the start of the run, using whatever task mechanism the harness provides, so the assumption-verification steps in the remediate phase don't get skipped under pressure:

1. Resolve binary version + `origin/main` SHA
2. Enumerate the CLI surface
3. Enumerate the published skills (from `origin/main`)
4. Compare and classify each gap
5. Produce the drift report
6. (Interactive) Stop for approval. (Headless) Skip.
7. Author the highest-severity gap and open the pull request
8. (Headless) Notify

### Step 1. Resolve binary version and the published skill set

Pin both ends of the comparison and put them in the report header.

```bash
pixee --version                                       # e.g. 0.12.0
git fetch origin --quiet
git rev-parse origin/main                             # SHA being audited
git log --oneline origin/main -1                      # human label
gh release list --repo pixee/pixee-cli --limit 1      # latest published release tag
```

If `pixee --version` is lower than the latest `gh release list` tag, treat the binary as stale. Interactive: ask whether to upgrade. Headless: continue and note the mismatch as the first line of the report header.

### Step 2. Enumerate the CLI surface

From the live binary, walk the help tree and record per top-level subcommand:

```bash
pixee --help                                          # top-level subcommand list
pixee <subcommand> --help                             # verbs + top-level flags
pixee <subcommand> <verb> --help                      # per-verb flag list
```

Capture per top-level subcommand: name, top-level help line, verbs, per-verb flags with their value types/enums.

Audit names and shape parity, not field-by-field documentation parity. HAL / response-shape coverage is out of scope.

### Step 3. Enumerate the published skills from `origin/main`

Read the skill set from `origin/main`, never from the local working tree — local checkouts go stale (old `main`, feature branches, worktrees on tags), and auditing against them silently inverts the result (false positives on skills that actually exist upstream, false negatives on real gaps masked by uncommitted work). If `git fetch origin` fails, stop and report rather than falling back to the local tree.

```bash
# Enumerate directories
git ls-tree -d --name-only origin/main skills/ | grep '^skills/pixee-' \
  | sed 's|^skills/||'

# Read each SKILL.md content
git show origin/main:skills/<pixee-noun>/SKILL.md
```

Per skill, extract:

- The slug (`pixee-scan`, `pixee-preferences`, ...).
- The frontmatter `description` field.
- **The frontmatter `cliHelp` field — `pixee <subcommand> --help` is the skill's claim of coverage.** This is what you join against the CLI surface from Step 2.
- The H2 sections (conventionally name the verbs documented: `## pixee scan list`, `## pixee scan get`).
- Flag mentions inside code fences and backticked tokens. Best-effort grep, not full Markdown parsing.

The cross-cutting `pixee-shared` skill has `cliHelp: "pixee --help"` and documents global flags, not a subcommand — handle it separately in Step 4 category D.

### Step 4. Compare and classify each gap

For every top-level subcommand the binary exposes, walk this decision tree:

- **A. Missing skill.** The subcommand is in `pixee --help` but no `origin/main` skill claims it via `cliHelp`. Example today on `pixee` 0.12.0 if `pixee-preferences` is absent: `organization` would be a category A gap.
- **B. Missing verb.** A skill claims the subcommand but a verb in `pixee <subcommand> --help` has no `## pixee <subcommand> <verb>` H2 or equivalent body coverage.
- **C. Flag drift.** A flag shown in `pixee <subcommand> <verb> --help` is missing from the skill, or the skill documents a flag the binary no longer accepts. Be conservative: a flag named in a single bash example counts as documented.
- **D. Shared-skill drift.** A global flag in `pixee --help` (`--server`, `--output`, `--json`, etc.) is missing from `pixee-shared`, or `pixee-shared` lists a global flag the binary no longer accepts.
- **E. Orphan skill.** A `origin/main` skill claims a subcommand (`cliHelp: "pixee <X> --help"`) but `pixee --help` no longer shows `X`. The skill documents a removed surface.

For each gap record: category, affected subcommand/verb/flag, severity (high for A/E, medium for B, low for C/D unless the flag is on a high-traffic list/get verb), one-line rationale citing the help-output line.

Severity is what Step 7 selects on, so record it for every gap even though a run closes only one.

Include low-severity items when they are real and verified. A genuine omission on a single flag is still drift; flagging it costs little and serves the same maintenance loop. Drop items you can't verify against `pixee <cmd> --help` output.

### Step 5. Produce the drift report

Lead with a one-line verdict so a maintainer skimming the report knows the answer immediately. Then the structured body.

```
# Pixee CLI Skill Drift Report

Verdict: NOT in sync — 3 gaps detected.

Audited binary: pixee 0.12.0
Origin SHA: <sha> on origin/main (`<short commit message>`)
Latest release tag: v0.12.0
Published skills audited: pixee-api, pixee-auth, pixee-finding, pixee-preferences, pixee-repo, pixee-scan, pixee-shared, pixee-workflow

## A. Missing skill (high)
- <subcommand>: `pixee <subcommand> ...` — no origin/main skill claims `cliHelp: "pixee <subcommand> --help"`.

## C. Flag drift (low)
- <skill>: `<flag>` <described/removed>

## No gaps for
- <subcommand1>, <subcommand2>, <subcommand3>, shared.
```

Three lines are load-bearing:

- **Verdict line.** One sentence. "NOT in sync — N gaps." or "In sync — no gaps detected." Anyone skimming should know the answer without reading the body.
- **Origin SHA line.** Records what was actually audited. Lets a follow-up run reproduce the comparison even if `origin/main` has moved.
- **"No gaps for" line.** Enumerates subcommands that were checked and clean. Without this the report only proves the gaps were found, not that the rest was checked.

"In sync — no gaps detected" is a complete and successful outcome. Report it and stop: there is nothing to remediate, and a run that finds nothing has done its job.

### Step 6. Interactive checkpoint (skipped under `--headless`)

After the report, ask: *"Close the highest-severity gap in a pull request?"* Treat anything short of an explicit yes as "report only" and exit cleanly.

Under `--headless`, skip this step.

### Step 7. Author the highest-severity gap and open the pull request

Close the single gap selected by hard rule 3.

- **Author through `add-resource-skill`.** Invoke `.claude/skills/add-resource-skill/SKILL.md` so its conventions govern the content, rather than editing a `SKILL.md` freehand.
- **The full report travels with the pull request.** Put the complete drift report in the description, including the gaps this run did not close, so both the next run and a human reader can see what is still outstanding. A gap dropped from the report is a gap nobody tracks.
- **Record the decisions you made alone.** Any choice taken without contributor input, most often "new skill or extend a sibling?", belongs in the description where the reviewer can correct it.
- **The pull request is the deliverable.** A branch pushed without one is an unfinished run. Report the PR URL, or report plainly that no PR was opened and why; never describe a run as complete without one.

### Step 8. Notify (`--headless` only)

Notify the user with a single message containing the audited `pixee` version, the gap that was closed, the pull request URL, and how many gaps remain outstanding.

Interactive mode uses the chat itself as the notification channel — skip this step.

## Boundaries

- The skill does not modify `skills/pixee-*/SKILL.md` freehand. All authoring goes through `add-resource-skill`, which preserves the conventions documented there.
- The skill does not bump `pixee-cli-private` versions, retag, or touch the release pipeline.
- The skill does not audit *content quality* — only naming and shape parity. "The pixee-workflow skill is hard to read" is a separate concern.
- The skill assumes `git fetch origin` works against `pixee/pixee-cli`. If it fails, stop and report — do not fall back to the local working tree, which is the one comparison guaranteed to be wrong.
- `gh` is used only to resolve the latest release tag for the version check in Step 1. Where `gh` is unavailable or unauthenticated, note that the tag could not be resolved and continue: the audit compares the binary against the skills, and the tag only tells you whether the binary itself is current.
- Opening the pull request needs push access to a branch on `pixee/pixee-cli`. Without it, stop after Step 5 and hand the contributor the report.

## Dry-run behavior

If the contributor invokes the skill without an obvious "remediate" intent — for example, "what skill drift is there?" or "run an audit" — execute steps 1–5 and stop. Treat silence after the report as "report only." `--headless` overrides this — under `--headless`, always remediate.

## Why this matters

Every skill bug an agent hits in the wild is paid for twice: once by the agent doing wrong work, once by the contributor cleaning it up after. Catching drift at release time, when the diff between binary and skill set is smallest, is the cheapest place to fix it. Routing the fix through a pull request means it lands the way every other change to this repo lands: a small diff, a clear title, and a rationale recorded where a reviewer will see it.
