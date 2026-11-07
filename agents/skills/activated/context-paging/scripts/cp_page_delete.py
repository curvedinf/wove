#!/usr/bin/env python3
"""Delete a page by id (its tag links cascade).

usage: cp_page_delete.py ID
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: cp_page_delete.py ID")
    con = cp.connect()
    cur = con.execute("DELETE FROM pages WHERE id = ?", (int(sys.argv[1]),))
    con.commit()
    if cur.rowcount:
        print("page %s deleted" % sys.argv[1])
    else:
        sys.exit("no page %s" % sys.argv[1])


if __name__ == "__main__":
    main()
