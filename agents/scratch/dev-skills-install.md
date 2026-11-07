# Dev-skills installation record

- **Scope:** project-wide (user selected option 1, 2026-11-07).
- **Source:** https://github.com/curvedinf/dev-skills @ `a740ada51ce258f9907535776e8749b16fa14681` (upstream main, "cp chrono filter").
- **Destination mapping:** `skills/<category>/<name>/` → `agents/skills/<category>/<name>/`, 22 skills (12 activated, 6 passive, 4 triggered) with adapters (`agents/openai.yaml`), references, and scripts; upstream `LICENSE` (MIT) → `agents/skills/LICENSE`.
- **Excluded:** upstream `.git`, upstream `agents/scratch/` (history and completion state), upstream `README.md`, upstream `docs/skill-research.md` (linked only from upstream README).
- **Initialized:** `agents/scratch/{index.md, timers.json, security-policy.md}`; `maintain-scratch` timer at declared default `interval_days: 7`, `last_completed_at: null` — no upstream completion history imported.
- **Adaptations:** project `AGENTS.md` created from source `AGENTS.md`; all skill links re-rooted to `agents/skills/`; skills store path updated to `agents/skills/<category>/<name>/`; harness opt-in, pre-commit security gate, fresh-session `maintain-scratch` + `context-compaction-procedure` triggers, and `refine-skill` metaskill check wired; self-improvement enablement left pending — upstream's `enabled` not inherited. `agents/scratch/security-policy.md` starts as a template — no upstream disclosure permissions imported.
- **`.gitignore`:** appended `/agents/tmp/` and `/agents/context-paging/`; unrelated rules untouched.
- **Conflicts:** none — no prior installation or existing `AGENTS.md`/`agents/` layout.
- **Pending:** none. Resolved 2026-11-07: user opted in to both. Context paging — existing `~/.kimi-code/hooks/context-paging/hook.py` and the three config rules matched the current template exactly (no changes needed); `cp_subscribe.py` run from the project root, `cp_subscribed.py` exits 0, manual payload capture verified and test session removed. Self-improvement — `Self-improvement: enabled.` set in project `AGENTS.md`.
- **Local customization:** `agents/skills/activated/context-paging/references/kimi-hooks.md` Verify step 4 amended to scope the post-check message lookup with `CP_SESSION` and delete the test session (evidence-backed refinement, 2026-11-07); reconcile on reinstall.
