# Reusable process skills

Skills standardize capable agents' working conventions across projects. They do not teach expertise or improve the agent. Trust the agent's judgment; specify only the conventions that matter.

Installed from [curvedinf/dev-skills](https://github.com/curvedinf/dev-skills) at commit `a740ada51ce258f9907535776e8749b16fa14681`; see the [installation record](agents/scratch/dev-skills-install.md).

## Categories

- **Passive:** scoped, persistent guidance once enabled, like an MTG static ability.
- **Triggered:** a workflow initiated by a non-user event when its conditions hold, like an MTG triggered ability.
- **Activated:** an explicitly requested workflow, like an MTG activated ability. It may be finite or explicitly continuous.

Store skills in `agents/skills/<passive|activated|triggered>/<name>/SKILL.md`. Frontmatter requires `name`, a concise `description`, and `metadata.category`. Names are unique across categories. A triggered skill's `description` states its trigger conditions so agents can fire it without reading the body; when too complex to state fully, give encompassing initial conditions plus " and extra conditions." and specify the full condition list inside the skill. Activated Codex adapters set `policy.allow_implicit_invocation: false` in `agents/openai.yaml`; passive and triggered adapters allow implicit invocation. Directory names and adapters do not implement event dispatch.

## Installation

Use [install-dev-skills](agents/skills/activated/install-dev-skills/SKILL.md). For an unscoped request, the first response must ask **1. Project-wide** or **2. Agent-wide**, then stop until answered. Do not infer the choice from the current repository or begin installation while waiting. Install and verify, then ask about self-improvement and save the choice in the applicable `AGENTS.md`. Authoring this workflow does not execute it.

## Skill selection

Scan the request terms below or a skill's frontmatter `description`. Load the workflow matching the requested outcome and only the passive conventions enabled for that work. A keyword is a routing hint, not permission to start another task.

- **Testing:** `testing-doctrine` governs test cadence and coverage; `design-validation` designs the checks; `diagnose-and-repair` investigates a failing behavior.
- **Improvement:** `run-experiment` answers a bounded comparison; `indefinite-loop` repeats experiment batches only when continuous work is requested.
- **Documentation:** `documentation-style` shapes ordinary edits; `polish-docs` redesigns the first-use experience.
- **Delivery:** `git-discipline` governs repository changes; `operate-workflow` handles external operations; `audit-and-resolve` assesses findings; `coordinate-work` manages assignments.

Switch workflows when the objective changes; preserve the shared goal record. Cross-links provide related guidance; they do not require loading the whole collection or invoking every linked workflow.

| Request terms | Read |
| --- | --- |
| install dev-skills, project-wide, agent-wide | [install-dev-skills](agents/skills/activated/install-dev-skills/SKILL.md) |
| claims, citations, uncertainty | [evidence-discipline](agents/skills/passive/evidence-discipline/SKILL.md) |
| scope, requirements, ownership | [contract-discipline](agents/skills/passive/contract-discipline/SKILL.md) |
| pre-commit, PID/PII, secrets, privacy leaks | [security-hygiene-check](agents/skills/triggered/security-hygiene-check/SKILL.md) |
| commit, push, merge, branches | [git-discipline](agents/skills/passive/git-discipline/SKILL.md) |
| test cadence, nightly, release gates | [testing-doctrine](agents/skills/passive/testing-doctrine/SKILL.md) |
| wording, terminology, examples | [documentation-style](agents/skills/passive/documentation-style/SKILL.md) |
| checkpoint, resume, history | [scratch-space](agents/skills/passive/scratch-space/SKILL.md) |
| context paging, page out, page in, offload context | [context-paging](agents/skills/activated/context-paging/SKILL.md) |
| compaction, compact, handoff summary | [context-compaction-procedure](agents/skills/triggered/context-compaction-procedure/SKILL.md) |
| periodic workflow, timed skill, shared timers | [design-time-triggered-skill](agents/skills/activated/design-time-triggered-skill/SKILL.md) |
| fresh session, weekly compaction | [maintain-scratch](agents/skills/triggered/maintain-scratch/SKILL.md) |
| create skill, author workflow | [design-skill](agents/skills/activated/design-skill/SKILL.md) |
| correction, workflow gap, refine, self-improvement | [refine-skill](agents/skills/triggered/refine-skill/SKILL.md) |
| README, onboarding, quickstart | [polish-docs](agents/skills/activated/polish-docs/SKILL.md) |
| debug, crash, regression | [diagnose-and-repair](agents/skills/activated/diagnose-and-repair/SKILL.md) |
| test plan, acceptance, coverage gaps | [design-validation](agents/skills/activated/design-validation/SKILL.md) |
| benchmark, compare, feasibility | [run-experiment](agents/skills/activated/run-experiment/SKILL.md) |
| continuous optimization, metrics | [indefinite-loop](agents/skills/activated/indefinite-loop/SKILL.md) |
| delegate, parallelize, handoff | [coordinate-work](agents/skills/activated/coordinate-work/SKILL.md) |
| review, audit, PR findings | [audit-and-resolve](agents/skills/activated/audit-and-resolve/SKILL.md) |
| deploy, migrate, resume job | [operate-workflow](agents/skills/activated/operate-workflow/SKILL.md) |

## Authoring

Use [design-skill](agents/skills/activated/design-skill/SKILL.md) for creation and [refine-skill](agents/skills/triggered/refine-skill/SKILL.md) for evidence-backed maintenance.

- `README.md` is for humans and is marketing-centric: communicate concrete value, credible proof, and a clear path to adoption. `AGENTS.md` is for computers and is utility-centric: provide precise routing, constraints, commands, and decision rules. Keep agent operating instructions out of the README and promotional prose out of AGENTS. Marketing remains evidence-driven, without exaggeration.
- Specify outcomes and consequential decision criteria; delegate execution mechanics.
- Prefer precise verbs and established terms over explanatory padding; preserve scope and qualifiers.
- Remove tutorials, micromanagement, repeated policy, obvious advice, and speculative edge cases. Every sentence costs attention.
- Prefer consolidation over rule accumulation. Do not hide verbosity in references.
- Keep skills portable and self-contained. Add supporting files only for necessary task-specific material.
- Check format and links; use behavioral evaluation when a consequential uncertainty warrants it.

## Scratch space

**Fresh-session startup:** on the first project-context load after the initial user prompt, read triggered [maintain-scratch](agents/skills/triggered/maintain-scratch/SKILL.md) and check its entry in `agents/scratch/timers.json`. Run it if due (seven-day default). Check once per project per fresh session, not per task or context-window compaction. Preserve checked state across context handoffs. Shared timer completion advances only after verified maintenance; this is independent of self-improvement enablement.

Use [scratch-space](agents/skills/passive/scratch-space/SKILL.md) for durable, Git-versioned task notes in `./agents/scratch/`. Never ignore this directory; include relevant note updates when committing authorized work. Retain only resumption state, costly evidence, and ongoing operational policy not recoverable from canonical files or Git. Scratch is not a changelog: no routine edit summaries, completion receipts, or duplicate skill lessons. All skills' scratch instructions follow this retention rule; completed tasks usually need no note. Delete obsolete records rather than archiving them by default. Read-only task scope still applies.

Use `./agents/tmp/` for disposable files. Always keep `/agents/tmp/` in the root `.gitignore`; never force-add its contents. Retain reusable evidence in durable storage.

## Context paging harness opt-in

[Context-paging](agents/skills/activated/context-paging/SKILL.md) stores exact context in `agents/context-paging/context.db` (gitignored) so compaction and session boundaries do not lose it. Harness capture is per-project opt-in and only runs for subscribed projects. Once per session, before substantive work, check in order and stop at the first that holds:

1. `python3 agents/skills/activated/context-paging/scripts/cp_subscribed.py` exits 0 — this project is subscribed and the harness plugin is active. Skip silently.
2. `agents/tmp/context-paging.json` records `{"harness_install": "declined"}`. Skip silently.
3. Otherwise ask: "Install context paging in your harness for this project? It captures user messages automatically and keeps paged context recoverable." On yes, follow the skill's harness wiring ([references/kimi-hooks.md](agents/skills/activated/context-paging/references/kimi-hooks.md)) this session, subscribing last. On no, write `{"harness_install": "declined"}` to `agents/tmp/context-paging.json`. Any other answer defers to the next session; ask at most once per session.

## Context compaction

**Fresh-session startup:** on the first project-context load, read triggered [context-compaction-procedure](agents/skills/triggered/context-compaction-procedure/SKILL.md) once before substantive work, so its procedure is resident when compaction occurs; preserve this across context handoffs. When compaction occurs and context-paging is enabled for this project, that skill's statement replaces harness compaction instructions.

## Pre-commit security gate

Before every project commit, including amendments and merges, run [security-hygiene-check](agents/skills/triggered/security-hygiene-check/SKILL.md) on the final candidate after all edits. Apply the natural-language disclosure policy in `agents/scratch/security-policy.md`; findings outside its approved scope require an explicit user disposition before committing, even when commit/push permission already exists. Recheck changed candidates. This gate is independent of self-improvement enablement.

## Self-improvement

Self-improvement: enabled.

**Always read and consider [refine-skill](agents/skills/triggered/refine-skill/SKILL.md).** It is a cross-cutting metaskill, not an optional route selected by task keywords.

**When skill use ends, before the final response**, evaluate user corrections, recurring friction, workflow gaps, and verified reusable lessons. When self-improvement is enabled, coalesce skills used for the same activity into one evidence-backed refinement pass within the task's write scope, validate any edits, and include them in the authorized task commit. Include blocked or interrupted skill use; rereading a skill does not retrigger the check. No evidence means no edit; refinement does not recursively trigger itself. `Self-improvement: enabled.` enables automatic edits; `Self-improvement: disabled.` turns them off — either state retains the requirement to read and consider the metaskill. Explicit refinement requests still apply.

## Reference skill libraries

Use relevant examples as inspiration, not requirements. Favor this collection's minimalism over a reference library's complexity; check licenses before copying material.

| Library | Useful ideas to examine |
| --- | --- |
| [Anthropic skills](https://github.com/anthropics/skills) | Self-contained packaging, concise entrypoints, and supporting resources for substantial workflows. |
| [Obra Superpowers](https://github.com/obra/superpowers) | Composable development processes, explicit workflow transitions, and skill validation practices. Adapt individual ideas without importing the entire methodology. |
| [Vercel agent-skills](https://github.com/vercel-labs/agent-skills) | Clear use conditions, impact-based prioritization, and separation of collections into focused skills. Generalize relevant process ideas from stack-specific examples. |
| [Hermes Agent bundled skills](https://github.com/NousResearch/hermes-agent/tree/main/skills) | Default skill architecture, capability-focused discovery, progressive disclosure, and evidence-driven refinement. Inspect its [skill authoring procedure](https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md) and distinguish portable principles from Hermes-specific runtime policies. |

Use the [Agent Skills specification](https://agentskills.io/specification) for portable packaging. It is a format reference, not a skill library. Verify current content when relying on external conventions; avoid preserving star counts or treating popularity as evidence of effectiveness.
