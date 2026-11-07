---
name: indefinite-loop
description: Optimize continuously, indefinite loop, keep improving metrics. Run successive research-driven experiment batches until interrupted; use run-experiment for a bounded comparison.
metadata:
  category: activated
---

# Indefinite loop

Remain committed to improving the project's metrics through successive batches of experiments. A completed batch, reached target, or plateau is a reason to reassess and continue, not declare the loop finished.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: baseline, accepted candidate, batch results, rejected directions, and next experiments.

## Preamble: define success

Use the user's metrics. If none are supplied, inspect the project's goals, representative usage, and current bottlenecks; select and justify outcome-aligned metrics. Proceed with that rationale unless an unresolved user tradeoff prevents choosing responsibly.

Define the primary objective, improvement direction, correctness and quality constraints, representative evaluation, and a material gain exceeding measurement noise. For competing metrics, establish priorities or acceptable tradeoffs before experimenting. Record a reproducible baseline and recoverable incumbent. Keep evaluation stable; changing the objective or workload requires an explicit rationale and new baseline.

## Repeat

1. **Research and design a batch.** Inspect measurements, relevant literature or implementations, and previous results. Propose about five distinct hypotheses, each with a mechanism, expected metric impact, evaluation, and bounded experiment cost. Rank by expected impact and information gain per unit cost.
2. **Favor structural opportunities.** Target the measured bottleneck: eliminate work, change algorithms or representations, rewrite a kernel, fuse stages, or remove transfers and synchronization. Size alone does not justify a rewrite. Group neighboring parameter variants into one bounded sweep; do not fill batches with block-size changes or repeatedly sweep an exhausted neighborhood. Tuning needs evidence of remaining headroom. A plateau calls for renewed measurement and a different mechanism.
3. **Execute sequentially.** Run each experiment against the latest accepted incumbent, isolating its contribution. Check correctness and compare under equivalent conditions; repeat enough to resolve plausible noise. After an accepted change, revise invalidated hypotheses.
4. **Keep only demonstrated wins.** Accept a candidate only when it meets the predefined improvement criterion and preserves constraints. Reject or mark inconclusive everything else, restoring only that experiment's changes. Retain a compact record of hypothesis, source/configuration, measurements, and verdict. Check cumulative gains against the original baseline and representative held-out cases to detect workload overfitting.
5. **Renew the search.** Update the incumbent and research priorities from the results, then start the next batch without requesting routine continuation. Keep a resumable checkpoint with accepted state, results, rejected directions, and next experiments; provide concise progress updates.

Continue until the user stops or redirects the loop, an applicable resource or runtime limit is reached, or further progress requires unavailable input or authorization. At an interruption, preserve the checkpoint and identify the continuation point. This skill does not create background execution; never imply work continues after execution ends.

**Illustrative batch:** for a pipeline with measured compute and transfer costs, test eliminating duplicate computation, fusing adjacent stages, changing the intermediate representation, rewriting the dominant kernel, and overlapping transfers with independent work. Each hypothesis must explain its expected end-to-end benefit.
