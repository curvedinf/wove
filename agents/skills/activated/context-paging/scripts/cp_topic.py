#!/usr/bin/env python3
"""Get-or-create a topic in the current session.

usage: cp_topic.py [NAME]   (default: $CP_TOPIC)
"""
import os
import sys

import cpcommon as cp


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CP_TOPIC")
    if not name:
        sys.exit("usage: cp_topic.py [NAME] (or set CP_TOPIC)")
    con = cp.connect()
    sid, key, _ = cp.ensure_session(con)
    tid = cp.ensure_topic(con, sid, name)
    print("topic %d %s (session %d)" % (tid, name, sid))


if __name__ == "__main__":
    main()
