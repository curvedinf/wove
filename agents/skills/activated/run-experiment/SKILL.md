---
name: run-experiment
description: Benchmark, compare alternatives, feasibility spike, hypothesis test. Run a bounded controlled experiment; indefinite-loop owns continuous optimization.
metadata:
  category: activated
---

# Run an experiment

Answer a specific question with observations. A negative or inconclusive result is a valid outcome.

For ongoing work, read and update [scratch records](../../passive/scratch-space/SKILL.md) in `agents/scratch/`: hypotheses, reproduction details, results including failures, and verdicts.

1. Define the question, alternatives, relevant metric or observable outcome, and decision criterion before collecting results. Set a bounded scope; reject post-hoc success thresholds.
2. Establish the baseline and record consequential inputs, configuration, source/artifact identity, and environment. Separate exploratory tuning from held-out evaluation to control selection bias.
3. Run comparable trials. Control unrelated changes, warmup, execution order, and competing load as relevant. Preserve raw outcomes, including failures; repeat enough to characterize measurement variance.
4. Compare the target outcome alongside correctness and resource tradeoffs. Distinguish a component measurement from end-to-end behavior, and correlation from causal attribution.
5. Deliver the result, reproduction details, uncertainty, and resulting decision. Keep an experiment separate from production adoption unless adoption was requested.

If conditions cannot be made comparable, report the comparison as uncontrolled. Do not cherry-pick runs or substitute a proxy metric without explaining its limits.

Illustrative verdict: “The candidate used less memory on the same workload, but latency varied more than the observed difference. Memory reduction is supported; a speed improvement is not established.”
