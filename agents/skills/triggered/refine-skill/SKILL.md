---
name: refine-skill
description: User corrections, repeated friction, workflow gaps, verified lessons, skill self-improvement. Triggers when any skill-assisted activity ends, including blocked or interrupted endings and passive skills at their governed activity's completion, or on an explicit refinement request, and extra conditions. Always read and consider; apply evidence-backed edits only when project-enabled, before the final response and authorized commit.
metadata:
  category: triggered
---

# Refine a skill

Refine shared procedures from observed evidence, not the agent itself. As a cross-cutting metaskill, always read and consider this guidance regardless of the selected workflow. Observe user corrections, recurring friction, procedural gaps, and verified reusable lessons during skill use.

**Event and full trigger conditions:** the `description` states the initial ones plus “ and extra conditions.”

- A skill-assisted activity ends, including a workflow that ends blocked or interrupted; for passive guidance, the boundary is completion of the activity it governed.
- An explicit refinement request arrives; it applies regardless of enablement.
- One pass per activity: coalesce skills used for the same activity and evaluate before the final response and authorized task commit. Rereading a skill is not a new event; this event-driven trigger has no timer.
- Apply edits only when enabled. No evidence means no edit.

1. **Distill the lesson.** Identify the condition and required behavior; add rationale only where it changes decisions. Capture a reusable convention, not an incident transcript. Skip one-off details and rules already covered.
2. **Patch the owner.** Read the affected skill and replace the passage responsible for the divergence. Preserve prior requirements; avoid recency-driven overcorrection and accumulating exceptions. Consolidate overlapping guidance while preserving resources and callers. Use [design-skill](../../activated/design-skill/SKILL.md) for a genuinely distinct new process; otherwise keep the change local.
3. **Verify and finish.** Keep edits recoverable and within the task's write scope. Check packaging, links, and the affected decision; use behavioral evaluation for consequential uncertainty. For read-only or externally owned skills, report a proposed correction instead. Include edits in the authorized task commit and briefly report the refinement and its evidence; do not add routine no-op reports. This skill may refine itself, but maintenance does not trigger another pass.

Use [scratch records](../../passive/scratch-space/SKILL.md) only for deferred corrections or evidence needed for later work. Once a lesson is encoded in its owning skill, do not also log the refinement in scratch. Keep session history out of runtime instructions.

## Enablement

Applicable `AGENTS.md` instructions control automatic refinement; a host-supported agent-wide setting supplies the default and a more specific project declaration overrides it. `Self-improvement: enabled.` enables it; disabled or absent leaves it off. Explicit refinement requests still apply. Installation must not inherit the library's opt-in or expand write scope to global skills.

Beside an enabled declaration, link this skill and include: “Always read and consider refine-skill. When skill use ends, assess its lessons once; apply an evidence-backed refinement when enabled, before the final response.” The host must load that instruction; a triggered category or discovery adapter alone does not enforce it. This is an agent-followed completion obligation, not a runtime callback or background service.
