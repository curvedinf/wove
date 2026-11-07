---
name: coordinate-work
description: Delegate, parallelize, split work, coordinate contributors, integrate handoffs. Organize requested assignments; does not authorize delegation by itself.
metadata:
  category: activated
---

# Coordinate work

Partition by ownership and interfaces. Keep tightly coupled work together; parallelism is a choice, not the goal.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: assignment ownership, dependencies, separate contributor records, and integration status.

1. Establish the shared outcome, acceptance criteria, source baseline, and dependency order. Assign integration ownership.
2. Give each assignment a bounded objective, owned files or artifacts, interface expectations, available inputs, and required return evidence. Make each handoff self-contained.
3. Prepare authorized execution environments before dispatch. Separate writable outputs, preserve required uncommitted inputs, and allocate shared resources. Parallelize only noninterfering assignments.
4. Reconcile returned deltas against their source baseline. Check interface changes, evidence, and unresolved decisions; reassign or clarify the affected work when assumptions break.
5. Combine authorized changes at meaningful dependency milestones and validate end-to-end interfaces. Report what is reviewed, integrated, verified, and still pending.

Planning does not authorize delegation or integration. When contributors or isolation are unavailable, execute the same assignments sequentially and state the limitation. Passing isolated checks does not establish combined behavior.

Illustrative handoff: “Own the CSV parser. Return records matching the agreed schema, malformed-input behavior, and verification results. The importer owns persistence; integration must exercise parser output against the real importer.”
