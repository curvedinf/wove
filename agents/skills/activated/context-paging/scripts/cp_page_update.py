#!/usr/bin/env python3
"""Replace a page's content, keeping its id, topic, and tags.

usage: cp_page_update.py ID CONTENT   (CONTENT "-" reads stdin)
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: cp_page_update.py ID CONTENT")
    content = cp.read_text(sys.argv[2])
    if not content.strip():
        sys.exit("refusing to store an empty page")
    con = cp.connect()
    cur = con.execute(
        "UPDATE pages SET content = ?, token_est = ?, updated_at = %s WHERE id = ?" % cp.NOW,
        (content, cp.est_tokens(content), int(sys.argv[1])),
    )
    con.commit()
    if cur.rowcount:
        print("page %s updated tokens~%d" % (sys.argv[1], cp.est_tokens(content)))
    else:
        sys.exit("no page %s" % sys.argv[1])


if __name__ == "__main__":
    main()
