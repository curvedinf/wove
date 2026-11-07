---
name: design-validation
description: Test plan, acceptance criteria, coverage gaps, test-suite design. Design checks for specific claims; testing-doctrine owns execution cadence and evidence reuse.
metadata:
  category: activated
---

# Design validation

Select checks by evidentiary scope, not by test count or coverage percentage.

Assign designed checks to the project’s intervals using [testing-doctrine](../../passive/testing-doctrine/SKILL.md) when available.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: claim-to-check mappings, candidate-specific results, and uncovered obligations.

1. Identify the acceptance claims, consequential failure modes, and existing evidence. Account for the requested test budget and project gates.
2. Map each claim to the smallest adequate check. Reuse existing tests and fixtures where suitable; include actual entrypoints, adverse conditions, and lifecycle boundaries when those are part of the claim.
3. Separate component proof from real integration and user-experience proof. Simulators can isolate a mechanism; they cannot establish unmodeled network, hardware, rendering, or external-service behavior.
4. Execute when authorized, retaining results and relevant candidate/configuration identity. A plan-only request produces the proposed checks and unresolved obligations instead.
5. Report which claims passed, failed, remain untested, or rely on substitute evidence. Rerun invalidated checks; deduplicate equivalent runner coverage.

When reducing a suite, map retired coverage to verified replacements or retained checks. Preserve defect detection and fresh-state coverage; fewer test names alone are not savings. Skipped or empty selections are not passes.

Illustrative mapping: “Duplicate prevention: replay the same request in a component fixture. Interrupted delivery: exercise the production entrypoint with acknowledgment loss. Neither check establishes visual status accuracy.”
