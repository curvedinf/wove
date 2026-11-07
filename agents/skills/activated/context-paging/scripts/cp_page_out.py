#!/usr/bin/env python3
"""Store a page of exact context (never a paraphrase) in the current session.

usage: cp_page_out.py CONTENT [TOPIC] [TAG ...]
       echo CONTENT | cp_page_out.py - [TOPIC] [TAG ...]

CONTENT "-" reads stdin. TOPIC defaults to $CP_TOPIC; TAGs merge with $CP_TAGS
(comma-separated). --kind selects note|decision|summary|reference|error.
"""
import os
import sys

import cpcommon as cp


def main():
    args = sys.argv[1:]
    kind = "note"
    if "--kind" in args:
        i = args.index("--kind")
        kind = args[i + 1]
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__.strip())
    content = cp.read_text(args[0])
    if not content.strip():
        sys.exit("refusing to store an empty page")
    topic = args[1] if len(args) > 1 else os.environ.get("CP_TOPIC")
    tags = args[2:] + [t for t in cp.env_tags() if t not in args[2:]]

    con = cp.connect()
    sid, _, _ = cp.ensure_session(con)
    topic_id = cp.ensure_topic(con, sid, topic) if topic else None
    cur = con.execute(
        "INSERT INTO pages (session_id, topic_id, kind, content, token_est)"
        " VALUES (?, ?, ?, ?, ?)",
        (sid, topic_id, kind, content, cp.est_tokens(content)),
    )
    pid = cur.lastrowid
    for tag in tags:
        cp.attach_tag(con, pid, sid, tag)
    con.commit()
    print(
        "page %d stored session=%d kind=%s topic=%s tags=%s tokens~%d"
        % (pid, sid, kind, topic or "-", ",".join(tags) or "-", cp.est_tokens(content))
    )


if __name__ == "__main__":
    main()
