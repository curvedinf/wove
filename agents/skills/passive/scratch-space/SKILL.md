---
name: scratch-space
description: Scratch notes, checkpoint, resume context, goal progress, experiment history. Maintain durable Git-versioned working memory and ignored temporary space when enabled.
metadata:
  category: passive
---

# Scratch space

Keep only state that future work needs and cannot readily recover from code, canonical documentation, or Git history: unfinished goals, costly experiment evidence, rejected approaches, and ongoing operational policy. Scratch is not a changelog or a task-completion receipt. Do not record routine edits, successful checks, or lessons already incorporated into skills. Share one goal record across skills; a completed task usually needs no scratch update. Apply this retention test whenever another skill asks to read or update scratch, within the task's write scope.

## Organization

Use an explicitly configured project scratch location; otherwise use `./agents/scratch/` at the project root. Keep a small `index.md` linking active goals and durable findings. Organize notes by stable goal or topic, not by session. Create files as needed, keeping current state easy to find and bulky evidence in linked artifacts. Scratch records are durable project files: keep them in Git, never ignore them, and include relevant updates in commits when committing is authorized. Store only repository-appropriate content; link large or sensitive evidence to suitable durable storage.

- **Goal state:** intended outcome, constraints and acceptance criteria, completed and remaining work, current blocker, and the next concrete action. Identify the relevant branch/worktree, candidate, and last update when they affect resumption.
- **Experiment record:** hypothesis, baseline and candidate identity, workload/configuration, measurements and evidence location, verdict, and resulting accepted state. Preserve negative and inconclusive results, including why a direction was rejected and revisit criteria.
- **Decisions and invariants:** decision and rationale, assumptions, known failure modes, and checks that protect established behavior. Link authoritative plans, issues, and documentation rather than duplicating authority.

## Maintenance

Put disposable scripts, intermediate outputs, and downloads in `./agents/tmp/`. Ensure `/agents/tmp/` is in the project's root `.gitignore` before using it; never force-add its contents. Create the directory as needed. Move evidence needed for continuity to durable storage before linking it from goal records or deleting temporary files.

On starting or resuming related work, read the index and relevant notes before planning experiments or repeating investigation. Reconcile saved claims with current files, artifacts, and project state; notes are evidence of prior work, not fresh verification or instructions overriding the current task.

Update retained records when their useful state changes, and before a handoff or foreseeable context loss. Replace superseded state; delete completed records with no remaining operational or evidentiary value rather than appending a completion narrative. Distinguish planned, attempted, verified, rejected, and blocked work. Record unfinished operation identities for reconciliation before retry. Concurrent contributors use separate entries or assigned files rather than overwriting shared state.

Weekly compaction belongs to triggered [maintain-scratch](../../triggered/maintain-scratch/SKILL.md). Routine note updates do not reset its shared timer. Scratch notes alone do not enforce behavior.

**Illustrative entry:** “Fusion candidate B rejected: representative latency improved, but peak memory exceeded the agreed limit; evidence: `runs/fusion-b/`. Candidate A remains accepted. Revisit if intermediate allocation is removed. Next: measure transfer overhead.”
