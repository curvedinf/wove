#!/usr/bin/env python3
"""List the current session's messages chronologically, newest last.

usage: cp_message_list.py [QUERY] [LIMIT] [--since DUR]

Defaults to the past hour; --since 30m, 24h, 7d, or any widens the window.
"""
import sys

import cpcommon as cp


def main():
    argv, modifier, label = cp.parse_since(sys.argv[1:])
    if len(argv) > 2:
        sys.exit(__doc__.strip())
    query = argv[0] if argv else None
    limit = 20
    if len(argv) > 1:
        try:
            limit = int(argv[1])
        except ValueError:
            sys.exit(__doc__.strip())
    con = cp.connect()
    sid, key, _ = cp.ensure_session(con)
    conds, params = ["session_id = ?"], [sid]
    if query:
        conds.append("content LIKE ?")
        params.append("%" + query + "%")
    tc = " AND created_at >= datetime('now', ?)" if modifier else ""
    rows = con.execute(
        "SELECT id, role, content, created_at FROM messages WHERE "
        + " AND ".join(conds) + tc + " ORDER BY id DESC LIMIT ?",
        params + ([modifier] if modifier else []) + [limit],
    ).fetchall()
    print(cp.filters_line(scope=key, query=query, since=label, limit=limit))
    older_n = 0
    if modifier:
        older_n = con.execute(
            "SELECT COUNT(*) FROM messages WHERE " + " AND ".join(conds), params
        ).fetchone()[0]
    if not rows:
        line = "  no messages in the window"
        if older_n:
            line += "; %d older in this session (--since any)" % older_n
        print(line)
        return
    for r in reversed(rows):
        print("#%d %s %s: %s"
              % (r["id"], r["role"], r["created_at"], cp.excerpt(r["content"], query or "")))
    if older_n:
        print("(%d older beyond the window: --since any)" % older_n)


if __name__ == "__main__":
    main()
