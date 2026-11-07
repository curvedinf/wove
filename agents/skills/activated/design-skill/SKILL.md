---
name: design-skill
description: Create a skill, design a workflow, author process instructions. Build minimal reusable skills; refine-skill owns evidence-triggered maintenance.
metadata:
  category: activated
---

# Design a skill

Skills normalize different agents' default approaches; they do not improve the agent or teach expertise. Specify outcome-defining conventions; trust execution to the agent.

Use [scratch records](../../passive/scratch-space/SKILL.md) for unresolved design decisions or costly evidence needed to resume work; completed skill creation needs no separate record.

1. Identify the desired outcome and which defaults need standardization. Check existing ownership before creating a skill; route corrections to [refine-skill](../../triggered/refine-skill/SKILL.md).
2. Inspect relevant peer skills or exemplary outputs. Extract specific conventions worth adopting, not their entire methodology. [Architecture references](references/architecture.md) provide starting points.
3. Choose passive guidance (always applicable within scope), an activated process (deliberately initiated), or a triggered workflow (non-user event). For activated skills, write a short sequence from initial assessment through delivery and verification; continuous workflows instead define the repeat cycle and resumable interruption conditions. A list of principles alone is not a process. For passive skills, state the ongoing convention and its scope. For triggered skills, define event, conditions, procedure, and host wiring, and state the trigger conditions in the `description` — fully when they fit, otherwise encompassing initial conditions plus “ and extra conditions.” with the full condition list inside the skill; use [design-time-triggered-skill](../design-time-triggered-skill/SKILL.md) for timers.
4. Front-load the description with likely request terms, the outcome, and the distinction from adjacent skills. Keywords select candidates; user intent determines activation. Keep computer-facing, utility-centric routing and instructions in `AGENTS.md` and skills; reserve `README.md` for human-facing, marketing-centric value, evidence, and adoption. Assign each shared convention one canonical owner; link selectively. Specify the important choices and add compact finished examples where they clarify the intended result. Leave execution mechanics to the agent.
5. Prune nonessential instructions. Preserve the process and distinguishing details, then check packaging, references, and any meaningful behavioral uncertainty.

## Writing conventions

- **Minimal, not vague:** replace “use best practices” or “make it polished” with the few concrete choices that define the requested standard. Conciseness must not erase the process.
- **Specific, not prescriptive:** normalize voice, structure, evidence, or decision criteria as relevant. Avoid tutorials, tool-by-tool instructions, arbitrary quotas, and repeated policy.
- **Examples show the target:** use finished examples, not before/after comparisons by default. Demonstrate the distinguishing qualities together; an example of brevity alone does not demonstrate persuasive, evidence-driven writing. Label fictional examples and assumptions.
- **Required user choices:** specify the question, what counts as an answer, and which work must wait. Asking is not receiving a choice; never turn missing input into a default. Honor an explicit selection already supplied for the task.
- **Semantic density:** prefer precise verbs and established terms that encode the intended distinction. Preserve qualifiers, scope, and process; avoid cryptic shorthand, invented jargon, or stronger claims disguised as compression.
- **Every sentence costs attention:** remove hand-waving, empty superlatives, speculative exceptions, and redundant explanations. Supporting files must earn their place, not conceal verbosity.

Check that representative requests select the intended skill from descriptions alone, especially adjacent skills. Packaging checks do not establish execution behavior; exercise tasks when consequential uncertainty warrants it.

Use `skills/<passive|activated|triggered>/<name>/SKILL.md`, with frontmatter `name`, `description`, and `metadata.category`. Keep host-specific invocation settings in adapters.
