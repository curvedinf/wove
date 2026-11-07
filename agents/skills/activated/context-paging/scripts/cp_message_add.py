#!/usr/bin/env python3
"""Capture a message row in the current session (verbatim, never paraphrased).

usage: cp_message_add.py ROLE CONTENT   (CONTENT "-" reads stdin)

ROLE is typically user, assistant, or system.
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: cp_message_add.py ROLE CONTENT")
    role, content = sys.argv[1], cp.read_text(sys.argv[2])
    if not content.strip():
        sys.exit("refusing to store an empty message")
    con = cp.connect()
    sid, key, _ = cp.ensure_session(con)
    cur = con.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (sid, role, content),
    )
    con.commit()
    print("message %d %s session=%d tokens~%d" % (cur.lastrowid, role, sid, cp.est_tokens(content)))


if __name__ == "__main__":
    main()
