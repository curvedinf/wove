#!/usr/bin/env python3
"""Get-or-create the current session and mark it active.

usage: cp_session_start.py [SESSION_KEY]   (default: $CP_SESSION, else "manual")
"""
import sys

import cpcommon as cp


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else None
    con = cp.connect()
    sid, key, created = cp.ensure_session(con, key)
    state = "started" if created else "resumed"
    print("session %d key=%s %s" % (sid, key, state))


if __name__ == "__main__":
    main()
