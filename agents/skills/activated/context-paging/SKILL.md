---
name: context-paging
description: Context paging, page out, page in, offload context, rolling context window, recover compacted history. Keep exact context recoverable in a per-project SQLite database instead of losing it to compaction or session end; per-project harness hooks capture messages. Nothing is summarized.
metadata:
  category: activated
---

# Context paging

Opt-in rolling context, modeled on the Pi context-paging extension: the full record lives on disk, the working window stays small, and recovery returns exact text. Page exact content out to the project database before compaction or session end removes it; page it back in by search when a detail from earlier work is needed. Never store paraphrases — recovery must return exact content.

## Store

SQLite at `<project>/agents/context-paging/context.db` (`CP_DB` overrides); keep `/agents/context-paging/` gitignored next to `/agents/tmp/`. Any script auto-creates the schema. Tables: `sessions`; `messages` (captured conversation, foreign key to session); `topics` and `tags` (session-scoped); `pages` (curated context units, foreign keys to session and topic); `page_tags`. The subscription registry `${XDG_CONFIG_HOME:-~/.config}/context-paging/projects.json` maps project roots to database and script paths; it is the only thing harness hooks check.

## Scripts (`scripts/`, one operation each; env supplies defaults)

| Script | Operation | Arguments |
| --- | --- | --- |
| `cp_session_start.py` | get-or-create session, mark active | `[session_key]` |
| `cp_session_end.py` | mark session ended | `[session_key]` |
| `cp_session_list.py` | sessions with counts | — |
| `cp_session_delete.py` | delete session; rows cascade | `SESSION_KEY` |
| `cp_topic.py` | get-or-create topic | `[name]` (`CP_TOPIC`) |
| `cp_topic_list.py` | topics with page counts | — |
| `cp_page_out.py` | store a page of exact context | `content\|- [topic] [tag ...]`, `--kind note\|decision\|summary\|reference\|error` |
| `cp_page_in.py` | reload pages: recent, matching, or by id (`--id` never time-filtered) | `[query] --id N --all --full --limit N --since DUR` |
| `cp_page_update.py` | replace page content, id stable | `id content\|-` |
| `cp_page_delete.py` | delete page | `id` |
| `cp_tag.py` | attach tag to page | `page_id tag` |
| `cp_message_add.py` | capture a message row | `role content\|-` |
| `cp_message_list.py` | list or filter messages chronologically | `[query] [limit] --since DUR` |
| `cp_search.py` | chronological project-wide recovery search; compact references | `query --since DUR --offset N` |
| `cp_around.py` | browse messages around an id, in order | `message_id [count] --full` |
| `cp_cleanup.py` | prune ended/stale sessions when due (>24h) | `--days N --stale-days N --force` |
| `cp_init.py` | create the schema only | — |
| `cp_subscribe.py` | subscribe a project to harness capture | `[project_dir]` |
| `cp_unsubscribe.py` | unsubscribe; database kept | `[project_dir]` |
| `cp_subscribed.py` | gate: exit 0 iff subscribed | `[project_dir]` |

`CP_SESSION` names the current session (else `manual`); `CP_TOPIC` and `CP_TAGS` (comma-separated) supply defaults, so `cp_page_out.py "<exact content>"` is a complete call. A `-` content argument reads stdin. Read lookups (`cp_search.py`, `cp_message_list.py`, `cp_page_in.py` listings) default to the past hour, order oldest-first, and open with a compact `[filters: …]` line stating what was applied; widen with `--since 30m|24h|7d|any`. Empty windowed results name how many matches lie beyond the window; exact loads (`--id N`, `cp_around.py`) are never time-filtered.

## Working discipline

1. Page out exact, durable material as it is produced: decisions with rationale, file paths from long investigations, error text, large tool outputs worth keeping. One page per unit; the topic and tags name it for later retrieval.
2. Search returns compact references — ids and excerpts, never full contents — windowed to the past hour by default, with `--since` widening and `--offset` paging through further matches. Follow a hit with `cp_around.py <message_id>` to read it with its neighbors in order (`--full` for whole contents) or `cp_page_in.py --id N` for a full page, so minimal data enters the context until detail is needed. Page in when resuming (`cp_page_in.py --all`) or when a previously known detail is missing after compaction. When you author a compaction statement, follow [context-compaction-procedure](../../triggered/context-compaction-procedure/SKILL.md) instead of the harness template.
3. Messages are capture, pages are curation: hooks record verbatim user messages; record your own summaries and decisions as pages.

## Install into a project

1. The skill folder installs with the library ([install-dev-skills](../install-dev-skills/SKILL.md)); `scripts/` stays inside it.
2. Add `/agents/context-paging/` to the project `.gitignore`.
3. Insert the harness opt-in section below into the project `AGENTS.md`.
4. Execute that section now rather than deferring: skip on an existing subscription or recorded decline; otherwise ask whether to install the harness plugin, and on yes complete [references/kimi-hooks.md](references/kimi-hooks.md) — code the hook dispatcher, register the hook rules, then run `cp_subscribe.py` last, so subscribed means installed and verified. A no writes the decline variable; any other answer defers to the section's next-session check.
5. Manual use needs no harness wiring; the scripts run directly.

## Harness opt-in section (insert verbatim)

> ### Context paging harness opt-in
>
> The context-paging skill keeps this project's exact context recoverable in `agents/context-paging/context.db` (gitignored). Harness capture is per-project opt-in and only runs for subscribed projects. Once per session, before substantive work, check in order and stop at the first that holds:
>
> 1. Already installed and activated: `scripts/cp_subscribed.py` from the context-paging skill exits 0 for this project. Skip silently.
> 2. Declined: `agents/tmp/context-paging.json` contains `{"harness_install": "declined"}`. Skip silently.
> 3. Otherwise ask the user: "Install context paging in your harness for this project? It captures user messages automatically and keeps paged context recoverable." On yes, install per the skill's harness wiring this session. On no, write `{"harness_install": "declined"}` to `agents/tmp/context-paging.json`. Any other answer defers to the next session; ask at most once per session.

## Harness wiring

The capture plugin is not shipped; code it at install time so it matches the host's current hook API — [references/kimi-hooks.md](references/kimi-hooks.md) is the worked kimi code CLI example. Requirements for any host:

- Gate every invocation on the subscription registry entry for the event's project directory and exit immediately when absent; hooks are user-level in most harnesses, and this gate is what makes them per-project.
- Session start registers the session and runs the due-checked cleanup (this is the periodic cleanup check at the first message of a new session); each user message inserts a `messages` row; session end marks the session ended.
- Capture is fail-open: hook errors log and allow, never block the harness.
- The session-start hook prints a short paging notice (database path, `cp_search.py`, `cp_page_out.py`) so fresh sessions know older context is recoverable.
