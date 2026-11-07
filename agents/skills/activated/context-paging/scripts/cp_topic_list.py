#!/usr/bin/env python3
"""List topics of the current session with page counts."""
import cpcommon as cp


def main():
    con = cp.connect()
    sid, key, _ = cp.ensure_session(con)
    rows = con.execute(
        "SELECT t.id, t.name, (SELECT COUNT(*) FROM pages p WHERE p.topic_id = t.id) AS pages"
        " FROM topics t WHERE t.session_id = ? ORDER BY t.name",
        (sid,),
    ).fetchall()
    print("session %d key=%s" % (sid, key))
    for r in rows:
        print("%d %s pages=%d" % (r["id"], r["name"], r["pages"]))


if __name__ == "__main__":
    main()
