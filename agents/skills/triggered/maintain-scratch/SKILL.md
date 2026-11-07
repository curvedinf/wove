---
name: maintain-scratch
description: Fresh project session, weekly scratch compaction, remove obsolete notes. Triggers on the first project-context load after a fresh session's initial user prompt, once per project per session before substantive work, only when the shared seven-day timer in agents/scratch/timers.json is due; follow-up tasks, rereading instructions, and context-window compaction do not retrigger it.
metadata:
  category: triggered
---

# Maintain scratch space

**Event:** first project-context load after the initial user prompt of a fresh agent session. Check once per project per session, before substantive work; follow-up tasks, rereading instructions, and context-window compaction do not retrigger it.

**Timer:** `maintain-scratch` in `agents/scratch/timers.json`, default `interval_days: 7`. Use the [shared timer contract](../../activated/design-time-triggered-skill/references/timer-contract.md). This trigger is independent of skill self-improvement enablement.

When due:

1. Read the index and records. Delete routine change logs, completion receipts, and duplicates of Git history or canonical guidance. Consolidate useful state into current summaries: unresolved work, operational policy, and evidence needed to avoid regression or redundant experiments.
2. Archive only evidence with a concrete future use; do not move clutter into an archive by default. Keep active records resumable and repair links. Promote lasting contracts to canonical documentation where appropriate; never discard sole copies of needed evidence or sweep unrelated temporary files.
3. Verify the index, links, and retained context, then stamp only this timer's completion. A completed review finding nothing to compact still counts. Include maintenance in the next authorized commit.

Coordinate with active writers. Read-only, interrupted, or unsafe concurrent work leaves the timer unchanged; report the deferral. [scratch-space](../../passive/scratch-space/SKILL.md) governs ordinary note upkeep between passes, which does not reset this timer.

The host must load the startup instruction. No fresh session means no periodic check; this skill does not install a scheduler.
