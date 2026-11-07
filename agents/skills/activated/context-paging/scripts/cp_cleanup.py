#!/usr/bin/env python3
"""Prune old sessions; runs only when due (24h since the last run).

usage: cp_cleanup.py [--days N] [--stale-days N] [--force]

--days     retention for ended sessions (default 30)
--stale-days  auto-end sessions inactive this long (default 7)
--force    run even when not due

Checks itself at session start: due-checked calls are near-free, so the
session-start hook can simply run this with no arguments.
"""
import sqlite3
import sys

import cpcommon as cp


def parse(argv):
    opts = {"days": 30, "stale": 7, "force": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--force":
            opts["force"] = True
        elif a in ("--days", "--stale-days"):
            i += 1
            opts["stale" if a == "--stale-days" else "days"] = int(argv[i])
        else:
            sys.exit(__doc__.strip())
        i += 1
    return opts


def main():
    opts = parse(sys.argv[1:])
    con = cp.connect()
    row = con.execute("SELECT value FROM meta WHERE key = 'cleanup_last_run'").fetchone()
    if row and not opts["force"]:
        due = con.execute(
            "SELECT julianday('now') - julianday(?) > 1", (row["value"],)
        ).fetchone()[0]
        if not due:
            print("cleanup: not due (last run %s)" % row["value"])
            return
    stale = con.execute(
        "UPDATE sessions SET ended_at = %s WHERE ended_at IS NULL"
        " AND julianday('now') - julianday(last_active_at) > ?" % cp.NOW,
        (opts["stale"],),
    ).rowcount
    doomed = con.execute(
        "SELECT id FROM sessions WHERE ended_at IS NOT NULL"
        " AND julianday('now') - julianday(ended_at) > ?",
        (opts["days"],),
    ).fetchall()
    msgs = pages = 0
    for r in doomed:
        msgs += con.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (r["id"],)
        ).fetchone()[0]
        pages += con.execute(
            "SELECT COUNT(*) FROM pages WHERE session_id = ?", (r["id"],)
        ).fetchone()[0]
    for r in doomed:
        con.execute("DELETE FROM sessions WHERE id = ?", (r["id"],))
    con.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('cleanup_last_run', %s)" % cp.NOW
    )
    con.commit()
    print(
        "cleanup: ended %d stale session(s), pruned %d ended session(s) older than %dd"
        " (%d messages, %d pages)" % (stale, len(doomed), opts["days"], msgs, pages)
    )


if __name__ == "__main__":
    try:
        main()
    except sqlite3.Error as e:
        sys.exit("cleanup failed: %s" % e)
