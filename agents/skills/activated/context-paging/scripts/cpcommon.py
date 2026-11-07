"""Shared helpers for context-paging scripts. Python 3.8+ stdlib only."""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

NOW = "CURRENT_TIMESTAMP"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    harness TEXT NOT NULL DEFAULT 'generic',
    project TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT {now},
    last_active_at TEXT NOT NULL DEFAULT {now},
    ended_at TEXT
);
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE (session_id, name)
);
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE (session_id, name)
);
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    kind TEXT NOT NULL DEFAULT 'note',
    content TEXT NOT NULL,
    token_est INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT {now},
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS page_tags (
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (page_id, tag_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT {now}
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pages_session ON pages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
""".replace("{now}", NOW)


def project_root():
    root = os.environ.get("CP_PROJECT")
    if root:
        return os.path.abspath(root)
    cur = os.getcwd()
    git_root = agents_root = None
    d = cur
    while True:
        if git_root is None and os.path.isdir(os.path.join(d, ".git")):
            git_root = d
        if agents_root is None and os.path.isdir(os.path.join(d, "agents")):
            agents_root = d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return git_root or agents_root or cur


def db_path():
    return os.environ.get("CP_DB") or os.path.join(
        project_root(), "agents", "context-paging", "context.db"
    )


def connect():
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error:
        pass
    con.executescript(SCHEMA)
    con.commit()
    return con


def session_key(explicit=None):
    return explicit or os.environ.get("CP_SESSION") or "manual"


def ensure_session(con, key=None):
    key = session_key(key)
    row = con.execute("SELECT id FROM sessions WHERE key = ?", (key,)).fetchone()
    if row:
        con.execute(
            "UPDATE sessions SET last_active_at = %s, ended_at = NULL WHERE id = ?" % NOW,
            (row["id"],),
        )
        con.commit()
        return row["id"], key, False
    cur = con.execute(
        "INSERT INTO sessions (key, harness, project) VALUES (?, ?, ?)",
        (key, os.environ.get("CP_HARNESS") or "generic", project_root()),
    )
    con.commit()
    return cur.lastrowid, key, True


def ensure_topic(con, session_id, name):
    row = con.execute(
        "SELECT id FROM topics WHERE session_id = ? AND name = ?", (session_id, name)
    ).fetchone()
    if row:
        return row["id"]
    cur = con.execute(
        "INSERT INTO topics (session_id, name) VALUES (?, ?)", (session_id, name)
    )
    con.commit()
    return cur.lastrowid


def ensure_tag(con, session_id, name):
    row = con.execute(
        "SELECT id FROM tags WHERE session_id = ? AND name = ?", (session_id, name)
    ).fetchone()
    if row:
        return row["id"]
    cur = con.execute("INSERT INTO tags (session_id, name) VALUES (?, ?)", (session_id, name))
    con.commit()
    return cur.lastrowid


def attach_tag(con, page_id, session_id, name):
    tag_id = ensure_tag(con, session_id, name)
    con.execute(
        "INSERT OR IGNORE INTO page_tags (page_id, tag_id) VALUES (?, ?)", (page_id, tag_id)
    )
    con.commit()


def page_tags(con, page_ids):
    if not page_ids:
        return {}
    marks = ",".join("?" * len(page_ids))
    rows = con.execute(
        "SELECT pt.page_id, t.name FROM page_tags pt JOIN tags t ON t.id = pt.tag_id "
        "WHERE pt.page_id IN (%s) ORDER BY t.name" % marks,
        page_ids,
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["page_id"], []).append(r["name"])
    return out


def env_tags():
    return [t.strip() for t in os.environ.get("CP_TAGS", "").split(",") if t.strip()]


def read_text(arg):
    if arg == "-":
        return sys.stdin.read()
    return arg or ""


def est_tokens(text):
    return max(1, len(text) // 4)


def parse_since(argv):
    """Split --since DUR out of argv; return (rest, sqlite_modifier, label).

    DUR is Nm, Nh, Nd, or any; the default lookup window is the past hour.
    A None modifier means unbounded.
    """
    if "--since" not in argv:
        return list(argv), "-1 hour", "1h"
    i = argv.index("--since")
    if i + 1 >= len(argv):
        sys.exit("--since needs a duration: 30m, 1h, 7d, or any")
    val = argv[i + 1]
    rest = argv[:i] + argv[i + 2:]
    if val == "any":
        return rest, None, "any"
    n, unit = val[:-1], val[-1:]
    if not (n.isdigit() and unit in ("m", "h", "d")):
        sys.exit("--since needs a duration: 30m, 1h, 7d, or any")
    unit_name = {"m": "minutes", "h": "hours", "d": "days"}[unit]
    return rest, "-%d %s" % (int(n), unit_name), val


def filters_line(**kw):
    """Render applied lookup filters as one compact header line."""
    parts = []
    for k, v in kw.items():
        if v is None or v is False:
            continue
        if v is True:
            parts.append(k)
            continue
        if isinstance(v, str) and (not v or " " in v):
            v = '"%s"' % v
        parts.append("%s=%s" % (k, v))
    return "[filters: %s]" % " ".join(parts)


def excerpt(text, needle="", width=240):
    flat = " ".join(text.split())
    i = flat.lower().find(needle.lower()) if needle else 0
    if i < 0:
        i = 0
    start = max(0, i - width // 3)
    prefix = "..." if start > 0 else ""
    suffix = "..." if start + width < len(flat) else ""
    return prefix + flat[start:start + width] + suffix


def registry_path():
    base = os.environ.get("CP_CONFIG_HOME") or os.environ.get("XDG_CONFIG_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "context-paging", "projects.json")


def load_registry():
    try:
        with open(registry_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_registry(reg):
    path = registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, sort_keys=True)
        f.write("\n")


def root_for(arg):
    return os.path.abspath(arg) if arg else project_root()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
