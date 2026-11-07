#!/usr/bin/env python3
"""Reload pages of the current session: recent, matching a query, or by id.

usage: cp_page_in.py [QUERY] [--id N] [--all] [--full] [--limit N] [--since DUR]

--all searches every session in this project; --full prints whole
contents; listings default to the past hour (--since 30m, 24h, 7d, or any
widens) and order oldest-first; default limit is 10 entries. --id is
exact retrieval and is never time-filtered.
"""
import sys

import cpcommon as cp


def parse(argv):
    opts = {"id": None, "all": False, "full": False, "limit": 10}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--id", "--limit"):
            i += 1
            opts[a[2:]] = int(argv[i])
        elif a == "--all":
            opts["all"] = True
        elif a == "--full":
            opts["full"] = True
        else:
            positional.append(a)
        i += 1
    return (positional[0] if positional else None), opts


def show(con, rows, full):
    tags = cp.page_tags(con, [r["id"] for r in rows])
    for r in rows:
        print(
            "page %d [%s] %s session=%s topic=%s tags=%s"
            % (
                r["id"],
                r["kind"],
                r["created_at"],
                r["session_key"],
                r["topic"] or "-",
                ",".join(tags.get(r["id"], [])) or "-",
            )
        )
        print("  " + (r["content"] if full else cp.excerpt(r["content"], "", 400)))


def main():
    argv, modifier, label = cp.parse_since(sys.argv[1:])
    query, opts = parse(argv)
    con = cp.connect()
    if opts["id"] is not None:
        rows = con.execute(
            "SELECT p.*, s.key AS session_key, t.name AS topic FROM pages p"
            " JOIN sessions s ON s.id = p.session_id"
            " LEFT JOIN topics t ON t.id = p.topic_id WHERE p.id = ?",
            (opts["id"],),
        ).fetchall()
        if not rows:
            sys.exit("no page %d" % opts["id"])
        print(cp.filters_line(id=opts["id"]))
        show(con, rows, True)
        return
    sid, key, _ = cp.ensure_session(con)
    conds, params = [], []
    if not opts["all"]:
        conds.append("p.session_id = ?")
        params.append(sid)
    if query:
        conds.append("p.content LIKE ?")
        params.append("%" + query + "%")
    tc = " AND p.created_at >= datetime('now', ?)" if modifier else ""
    sql = (
        "SELECT p.*, s.key AS session_key, t.name AS topic FROM pages p"
        " JOIN sessions s ON s.id = p.session_id"
        " LEFT JOIN topics t ON t.id = p.topic_id"
    )
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += tc + " ORDER BY p.id ASC LIMIT ?"
    rows = con.execute(sql, params + ([modifier] if modifier else []) + [opts["limit"]]).fetchall()
    print(cp.filters_line(scope=("all" if opts["all"] else key), query=query,
                          since=label, limit=opts["limit"]))
    older_n = 0
    if modifier and conds:
        older_n = con.execute(
            "SELECT COUNT(*) FROM pages p WHERE " + " AND ".join(conds), params
        ).fetchone()[0]
    if not rows:
        line = "no pages"
        if older_n:
            line += "; %d page(s) beyond the window (--since any)" % older_n
        print(line)
        return
    print("%d page(s):" % len(rows))
    show(con, rows, opts["full"])
    if older_n:
        print("(%d page(s) older beyond the window: --since any)" % older_n)


if __name__ == "__main__":
    main()
