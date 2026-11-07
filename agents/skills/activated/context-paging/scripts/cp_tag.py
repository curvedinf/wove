#!/usr/bin/env python3
"""Attach a tag to a page (get-or-create in the page's session).

usage: cp_tag.py PAGE_ID TAG
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: cp_tag.py PAGE_ID TAG")
    con = cp.connect()
    row = con.execute(
        "SELECT id, session_id FROM pages WHERE id = ?", (int(sys.argv[1]),)
    ).fetchone()
    if not row:
        sys.exit("no page %s" % sys.argv[1])
    cp.attach_tag(con, row["id"], row["session_id"], sys.argv[2])
    print("tag %s -> page %s" % (sys.argv[2], sys.argv[1]))


if __name__ == "__main__":
    main()
