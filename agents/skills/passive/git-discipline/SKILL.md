---
name: git-discipline
description: Git, commit, push, merge, branches, staging, release candidate. Apply working-state preservation, branch flow, and task-completion publication defaults when enabled.
metadata:
  category: passive
---

# Git discipline

Apply these conventions during repository work. When enabled, the task-completion defaults below authorize routine commits and developer-branch pushes; explicit task restrictions take precedence.

## Task completion

Before creating any commit, run [security-hygiene-check](../../triggered/security-hygiene-check/SKILL.md) on the final candidate; findings not covered by the project disclosure policy pause these commit/push defaults for the user’s decision.

Use the project’s gates and [testing-doctrine](../testing-doctrine/SKILL.md) for validation cadence; publication never substitutes for acceptance.

- **Working directly on `main`:** commit the task's changes locally after each completed work task. Push only when explicitly requested.
- **Working on a persistent developer branch:** commit and push after each completed work task, then verify the remote ref. No repeated permission request is needed.
- Keep automatic task commits scoped to that task and its durable notes, preserving unrelated pending work. Skip empty commits for tasks with no changes. These defaults do not authorize merging a feature branch or promoting staging or a release candidate; follow the requested workflow for those branches.

## Working state

- **Inspect the whole state.** Before integration or publication, inspect the branch, worktree, staged and unstaged changes, untracked files, and intended remote ref. Review the actual diff; do not assume the current task accounts for everything pending.
- **Preserve local work.** Keep unrelated edits and staging intact during scoped tasks. Preserve explicitly protected files byte-for-byte and verify that preservation after integration. Avoid broad stashes or destructive reset/restore to make a merge convenient; isolate work or preserve only the conflicting paths recoverably.
- **Honor publication scope.** A request to “push your changes” means commit and publish the complete pending working tree unless the user scopes a subset or explicitly protects files from inclusion. Do not silently narrow publication to session-local edits. Inspect the intended set before staging; ignored temporary files remain excluded. A scoped commit must not absorb unrelated staged changes.
- **Resolve integration deliberately.** Fetch the relevant remote state and reconcile conflicts against both sides' intended behavior. Do not choose an entire side merely to clear conflicts. A rejected push calls for inspecting divergence, not automatically force-pushing or rewriting shared history. Retain worktrees and branches that still contain needed work.
- **Make commits reviewable.** Make cohesive commits without omitting work from an authorized broad publication. Describe the concrete change in commit messages and PR descriptions, following repository conventions. Do not invent a branch, release, or commit-format policy.
- **Verify the result.** Check the committed contents and remaining working state. After pushing, compare the intended commit with the remote branch ref, for example using `git ls-remote`. Report what was committed, published, and left pending separately from what was tested. Respect explicit test limits; publication is not test certification.

## Branch flow

Use this model unless the project explicitly defines another. Resolve actual branch names and developer ownership from project instructions; the names below describe roles.

```text
owner/feature → developer → staging → release candidate → main
```

- **Feature branches:** branch from the owner's persistent developer branch and merge completed, appropriately checked work back there. Keep unfinished experiments on feature branches; everything published to a developer branch is eligible for staging integration. Delete a feature branch only after its work is retained and it is no longer needed.
- **Developer branches:** retain one persistent branch per developer. Preserve published ancestry; do not rebase or reset branches already consumed by integration. Synchronize released changes from `main` as needed, and avoid pulling all of staging into a developer branch just to obtain one dependency.
- **Staging:** regularly merge eligible developer tips through authorized automation, for example daily. Capture source commit IDs, serialize updates, and validate the combined candidate before advancing shared staging. On conflicts or failed gates, retain the last accepted staging tip, record the failed candidate, and route unresolved work to its owner. Reconcile a concurrently changed remote before retrying. This convention does not itself install a schedule.
- **Release candidate:** cut from an identified staging commit when a release is selected. Freeze feature intake while staging continues ahead. Apply focused fixes and run the project's thorough release checks on the resulting candidate; a new fix invalidates affected prior evidence. Do not repeatedly merge newer staging into an active candidate, silently expanding release scope.
- **Main:** promote the exact accepted release-candidate commit, preferably by fast-forward. If `main` has advanced, reconcile it into the candidate and revalidate before promotion. Tag the accepted release commit under the project's naming rules; do not reset `main` to force a promotion.

Carry release-candidate fixes back to staging and affected developer branches, using merges where their ancestry is appropriate or traceable individual fixes where a merge would import unrelated work. An urgent production fix starts from `main`, receives the required validation, and propagates to any active candidate and development lines. Track fix propagation to prevent regression at reintegration.

Use [scratch records](../scratch-space/SKILL.md) for unresolved integration, protected work, pending publication, or fix propagation. Completed commits and pushes belong in Git history, not a parallel scratch log.

Illustrative report: “Published all pending project changes to the requested branch; its remote ref matches the local commit. The protected local configuration remains uncommitted. Only the requested syntax checks ran.”
