# Kimi Code CLI harness wiring

Worked example for coding the capture plugin at install time. Verify event names, payload fields, and config syntax against the [hooks documentation](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html) before writing anything; this page matches the documented API as of 2026-11-07.

Facts this wiring relies on:

- Hook rules are `[[hooks]]` entries in `~/.kimi-code/config.toml` (user-level only; there is no project hook file) with fields `event`, `matcher`, `command`, `timeout` (1–600s, default 30).
- Commands run with the session's local project directory as working directory; event details arrive as JSON on stdin, including `hook_event_name`, `session_id`, and `cwd`.
- `UserPromptSubmit`'s `prompt` field is a list of content blocks (`[{"type": "text", "text": "..."}]`), not a string; the dispatcher normalizes it to text before capture.
- `SessionStart` (matcher `startup|resume`), `UserPromptSubmit`, and `SessionEnd` (matcher `exit|archive`) cover the three lifecycle processes. Exit 0 allows and stdout may be appended to context; exit 2 blocks (never used here); failures fail open.

## Steps

1. Write the dispatcher to `~/.kimi-code/hooks/context-paging/hook.py` from the template below.
2. Append the three hook rules to `~/.kimi-code/config.toml`.
3. From the project root, run `cp_subscribe.py` — last, after the rules exist, because subscription means "installed and activated".
4. Verify (below) in a fresh session.

## Dispatcher template

```python
#!/usr/bin/env python3
"""kimi code context-paging hook: per-project gate, then lifecycle capture."""
import json
import os
import subprocess
import sys

REGISTRY = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "context-paging", "projects.json",
)


def run(scripts, name, *args, cwd, sid="", stdin_text=None):
    try:
        subprocess.run(
            [sys.executable or "python3", os.path.join(scripts, name), *args],
            cwd=cwd, input=stdin_text, text=True,
            env=dict(os.environ, CP_SESSION=sid),
            stdout=subprocess.DEVNULL, stderr=None, timeout=25,
        )
    except Exception as exc:  # fail-open: capture must never block
        print("context-paging: %s failed: %s" % (name, exc), file=sys.stderr)


def prompt_text(payload):
    p = payload.get("prompt", "")
    if isinstance(p, list):  # content blocks: [{"type": "text", "text": "..."}]
        return "\n".join(b.get("text", "") for b in p if isinstance(b, dict))
    return p if isinstance(p, str) else ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    root = payload.get("cwd") or os.getcwd()
    try:
        with open(REGISTRY, encoding="utf-8") as f:
            entry = json.load(f).get(root)
    except Exception:
        entry = None
    if not entry:
        return  # not subscribed: this project never runs capture
    scripts, db = entry.get("scripts", ""), entry.get("db", "")
    sid, event = payload.get("session_id", ""), payload.get("hook_event_name", "")
    if event == "SessionStart":
        run(scripts, "cp_session_start.py", sid, cwd=root, sid=sid)
        run(scripts, "cp_cleanup.py", cwd=root, sid=sid)
        print(
            "Context paging active for this project. Nothing is summarized; older "
            "context may already be paged out to %s. Recover it: "
            "`python3 %s/cp_search.py <query>` or cp_page_in.py; store exact "
            "durable detail with cp_page_out.py." % (db, scripts)
        )
    elif event == "UserPromptSubmit":
        run(scripts, "cp_message_add.py", "user", "-", cwd=root, sid=sid,
            stdin_text=prompt_text(payload))
    elif event == "SessionEnd":
        run(scripts, "cp_session_end.py", sid, cwd=root, sid=sid)


if __name__ == "__main__":
    main()
    sys.exit(0)
```

## Hook rules

```toml
[[hooks]]
event = "SessionStart"
matcher = "startup|resume"
command = "python3 ~/.kimi-code/hooks/context-paging/hook.py"
timeout = 15

[[hooks]]
event = "UserPromptSubmit"
command = "python3 ~/.kimi-code/hooks/context-paging/hook.py"
timeout = 15

[[hooks]]
event = "SessionEnd"
matcher = "exit|archive"
command = "python3 ~/.kimi-code/hooks/context-paging/hook.py"
timeout = 15
```

## Practices

- **Gate first.** The registry read happens before any database access; an unsubscribed project costs one JSON read and exits 0. This is what keeps user-level hooks per-project.
- **Fail open.** Every error path logs to stderr and exits 0; never exit 2 — capture must not block a prompt.
- **Stay fast.** One stdin read, one registry read, at most two short script calls; `timeout = 15` leaves margin under the 30s default.
- **Keep semantics idempotent.** `cp_session_start.py` get-or-creates by session key, so `startup` and `resume` are both safe; `cp_cleanup.py` is due-checked, so running it at every session start is the periodic cleanup check at the first message of a new session.
- **Capture verbatim, curate deliberately.** Hooks record user prompts in `messages`; do not try to capture assistant replies from payloads that do not carry them. Record assistant-side summaries and decisions yourself as pages (`cp_page_out.py`) or `cp_message_add.py assistant -`.
- **PreCompact/PostCompact** exist but PreCompact return values are ignored; do not rely on them to inject anything. The SessionStart notice plus the working discipline cover recovery.
- **Moved skill directory?** Rerun `cp_subscribe.py` from the project; the registry stores script paths.

## Verify

1. Start a fresh session in the subscribed project: `cp_session_list.py` shows a new active session, and the paging notice appears (SessionStart stdout may be appended to context).
2. Send one prompt: `cp_message_list.py 1` shows the captured user message.
3. Run a session in a different, unsubscribed project: no rows appear anywhere and the hook still exits 0.
4. Manual harness check without starting a session:
   `echo '{"hook_event_name":"UserPromptSubmit","session_id":"t1","cwd":"<project root>","prompt":[{"type":"text","text":"hello"}]}' | python3 ~/.kimi-code/hooks/context-paging/hook.py`, then confirm the row with `CP_SESSION=t1 cp_message_list.py --since any` (message lookups scope to `CP_SESSION`, defaulting to `manual`) and remove the test session with `cp_session_delete.py t1`.

## Remove

Run `cp_unsubscribe.py` in each subscribed project, delete the three `[[hooks]]` rules and `~/.kimi-code/hooks/context-paging/`. Databases under `agents/context-paging/` stay until deleted.
