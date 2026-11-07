---
name: operate-workflow
description: Deploy, publish artifacts, migrate, resume a job, retry partial operations. Reconcile and advance operational state; git-discipline owns Git publication conventions.
metadata:
  category: activated
---

# Operate a workflow

Reconcile state before advancing it. Use the project's established operational entrypoints.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: operation IDs, verified transitions, ambiguous outcomes, and continuation points.

1. Establish the intended outcome, target environment, authorized effects, and authoritative state. Inspect current progress and active ownership before starting or resuming.
2. Identify the phase: pending, in progress, partially complete, complete, failed, or unknown. Separate retryable failures from terminal failures and ambiguous external outcomes.
3. Select the next valid transition. Confirm its prerequisites, resource ownership, and retry deduplication. When an outcome is unknown, reconcile with the authoritative system before replaying the action.
4. Execute within scope, verify the resulting effect, and checkpoint resumable state. Retry only unresolved work under the workflow's retry policy; stop when retries add no evidence or safe progress is blocked.
5. Report the verified state, pending external steps, and recovery checkpoint. Release only resources owned by this run.

A successful command, local status file, or expired lock does not alone establish the external outcome or absence of an active worker. For releases, keep source, version, package, and destination identity aligned; preparation, upload, activation, and user-visible availability are distinct states. Scheduling future execution requires its own authorization.

Illustrative continuation: “Items A and B are confirmed complete. C timed out after submission; query its operation ID before retrying. Resume D after C's outcome is known.”
