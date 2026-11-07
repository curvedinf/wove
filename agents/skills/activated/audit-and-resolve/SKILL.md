---
name: audit-and-resolve
description: Review, audit, PR feedback, findings, remediation. Assess requested work and resolve authorized findings; use diagnose-and-repair for a reported runtime failure.
metadata:
  category: activated
---

# Audit and resolve

Use the requested mode: review, remediation, or both. Audit assumptions and implementation.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: prior findings, stable IDs, dispositions, and correction evidence.

1. Identify the intended outcome, exact candidate, relevant delta, and acceptance evidence. Read the affected mechanisms and their callers or consumers, not only the author's summary.
2. Seek concrete triggers or counterexamples and check counterevidence. Separate demonstrated defects, supported risks, missing evidence, and preferences; prioritize practical impact.
3. Return actionable findings with stable IDs, locations, consequences, and correction criteria. Give a scoped verdict: acceptable, changes required, or insufficient evidence.
4. When remediation is authorized, assign each finding a disposition: accepted, disputed with evidence, blocked, or explicitly deferred. Correct the established mechanism without bundling unrelated changes or weakening acceptance.
5. Recheck the original counterexample and adjacent behavior against the revised candidate. Preserve unresolved findings and distinguish an author's self-check from independent verification.

A clean review leaves unexamined behavior uncertified. If a review cycle repeats without new evidence, identify the disputed requirement or missing observation rather than repeating assertions. Integration and publication remain separate actions.

Illustrative finding: “F1 — Retrying after a lost acknowledgment creates a second item. The retry path assigns a new request ID. Verify by dropping the acknowledgment after creation and resuming the same request.”
