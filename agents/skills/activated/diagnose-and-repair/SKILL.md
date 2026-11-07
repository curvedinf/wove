---
name: diagnose-and-repair
description: Debug, reproduce, regression, crash, failing test, repair. Establish a reported failure mechanism and verify a correction; investigation-only requests stop at findings.
metadata:
  category: activated
---

# Diagnose and repair

Establish the mechanism before choosing the repair. An investigation-only request ends with findings.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: reproductions, rejected explanations, repair attempts, and unresolved evidence.

1. Establish expected behavior and reproduce the reported symptom in its relevant context. Retain the failing result and candidate identity; distinguish a product defect from a broken fixture, environment, or expectation.
2. Form a falsifiable hypothesis and seek discriminating evidence. Trace the affected boundaries and compare working cases. Minimize order-dependent reproductions without erasing the causal sequence.
3. Derive a scoped correction from the demonstrated mechanism. Change one causal concern at a time; avoid bundling speculative fixes or unrelated cleanup.
4. Re-run the original reproduction and relevant adjacent checks. Preserve its meaningful inputs and acceptance strength. If an expectation itself was wrong, justify that correction separately.
5. Report the mechanism, correction, retained evidence, and remaining uncertainty. A failed repair reopens diagnosis; do not stack speculative fixes.

Prefer deterministic regression coverage. For intermittent defects, retain the failing observations and compare under equivalent conditions; one quiet run does not prove absence. If reproduction or testing is unavailable, distinguish static evidence and unverified repairs from demonstrated fixes. Stop speculative repair and name the missing evidence.

Illustrative hypothesis: “Resuming after acknowledgment loss submits the completed item again; querying its stored request ID before retry should expose the duplicate.”
