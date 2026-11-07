---
name: design-time-triggered-skill
description: Create timed skills, periodic maintenance, interval triggers, shared timers. Design a triggered workflow with an explicit observation event and shared scratch timer state.
metadata:
  category: activated
---

# Design a time-triggered skill

Define periodic work that runs when an agent observes a due timer, without requiring another user request. Use [design-skill](../design-skill/SKILL.md) for general authoring conventions.

1. Define the outcome, interval, scope, and non-user observation event. Distinguish the clock condition from when it is checked: weekly work checked at fresh-session startup runs at the next eligible startup, not autonomously on a wall-clock deadline.
2. Assign a stable timer key, normally the skill name, in project-local `agents/scratch/timers.json`. Follow the [shared timer contract](references/timer-contract.md). Preserve existing entries and completion history; never import another project's timestamps.
3. Write the triggered skill with `metadata.category: triggered`: event, due condition, bounded procedure, completion evidence, and failure/deferral behavior; its `description` states the observation event and due condition so agents can trigger it from the description alone. State whether missed intervals collapse into one run; default to one maintenance pass, not replaying every missed period.
4. Wire the event into instructions the host actually loads, such as AGENTS startup guidance. Name the skill and timer key, define once-per-event behavior, and preserve event state across context compaction. A description or discovery adapter is not a scheduler. Use `allow_implicit_invocation: true` for a Codex triggered adapter; event conditions still govern execution.
5. Verify first use, not due, due, interrupted, read-only, and concurrent-update cases. Confirm one skill's completion preserves other timers. Check packaging and links; distinguish reviewed behavior from executed validation.

Record the event, interval, timer key, and verification limits in [scratch records](../../passive/scratch-space/SKILL.md). Creating this workflow does not run or schedule its payload.
