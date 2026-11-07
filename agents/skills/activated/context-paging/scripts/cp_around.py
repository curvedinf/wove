#!/usr/bin/env python3
"""Browse messages around one message id, in order.

usage: cp_around.py MESSAGE_ID [COUNT] [--full]

Shows COUNT messages before and after MESSAGE_ID (default 5, max 50) from
its session, in order, as excerpts; --full prints whole contents. COUNT 0
shows only the message itself. Use after cp_search.py to read a hit with
its surrounding conversation.
"""
import sys

import cpcommon as cp


def main():
    full = "--full" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--full"]
    if not 1 <= len(args) <= 2:
        sys.exit(__doc__.strip())
    mid = int(args[0])
    count = min(int(args[1]) if len(args) == 2 else 5, 50)
    con = cp.connect()
    row = con.execute(
        "SELECT id, session_id FROM messages WHERE id = ?", (mid,)
    ).fetchone()
    if not row:
        sys.exit("no message %d" % mid)
    sid = row["session_id"]
    before = con.execute(
        "SELECT id, role, content, created_at FROM messages"
        " WHERE session_id = ? AND id < ? ORDER BY id DESC LIMIT ?",
        (sid, mid, count),
    ).fetchall()[::-1]
    after = con.execute(
        "SELECT id, role, content, created_at FROM messages"
        " WHERE session_id = ? AND id >= ? ORDER BY id ASC LIMIT ?",
        (sid, mid, count + 1),
    ).fetchall()
    print(cp.filters_line(id=mid, count=count, full="yes" if full else None))
    for r in before + after:
        marker = "->" if r["id"] == mid else "  "
        print(
            "%s #%d %s %s: %s"
            % (marker, r["id"], r["role"], r["created_at"],
               r["content"] if full else cp.excerpt(r["content"], "", 200))
        )


if __name__ == "__main__":
    main()
