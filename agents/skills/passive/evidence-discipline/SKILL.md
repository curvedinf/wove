---
name: evidence-discipline
description: Claims, citations, sources, uncertainty, completion reports. Keep statements proportional to supporting evidence when enabled.
metadata:
  category: passive
---

# Evidence discipline

While assessing or reporting work, distinguish observations, attributed reports, and inferences. This convention shapes the current task; it does not initiate a separate audit.

For ongoing work, read and update [scratch records](../scratch-space/SKILL.md) in `agents/scratch/`: reusable evidence, candidate identity, and limits on conclusions.

- Attach consequential claims to inspectable sources or results. Cite the material that supports the claim, not merely a related page or a search snippet.
- Identify the candidate, inputs, and conditions when they affect a conclusion. Evidence from a different configuration is supporting context, not verification of this one.
- Bound conclusions by evidence: a successful build establishes compilation, a simulation establishes modeled behavior, and an observed user journey establishes that journey.
- Retain counterevidence and coverage gaps. Distinguish “not observed,” “not tested,” and “shown not to occur.” Recheck evidence when relevant inputs change.
- Report completed, failed, and blocked parts separately. An attempted action, delegated report, or empty test selection is not a verified result.

Illustrative report: “The import preserved all rows in the supplied fixture. Resuming an interrupted import was not exercised.”
