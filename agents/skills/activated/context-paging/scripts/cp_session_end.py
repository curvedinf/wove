#!/usr/bin/env python3
"""Mark the current session ended.

usage: cp_session_end.py [SESSION_KEY]   (default: $CP_SESSION, else "manual")
"""
import sys

import cpcommon as cp


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else None
    con = cp.connect()
    sid, key, _ = cp.ensure_session(con, key)
    con.execute(
        "UPDATE sessions SET ended_at = %s, last_active_at = %s WHERE id = ?" % (cp.NOW, cp.NOW),
        (sid,),
    )
    con.commit()
    print("session %d key=%s ended" % (sid, key))


if __name__ == "__main__":
    main()
