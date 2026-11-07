#!/usr/bin/env python3
"""Delete a session; pages, messages, topics, and tags cascade.

usage: cp_session_delete.py SESSION_KEY
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: cp_session_delete.py SESSION_KEY")
    con = cp.connect()
    cur = con.execute("DELETE FROM sessions WHERE key = ?", (sys.argv[1],))
    con.commit()
    if cur.rowcount:
        print("session %s deleted" % sys.argv[1])
    else:
        sys.exit("no session %s" % sys.argv[1])


if __name__ == "__main__":
    main()
