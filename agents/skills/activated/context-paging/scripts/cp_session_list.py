#!/usr/bin/env python3
"""List sessions with their page, message, and topic counts."""
import cpcommon as cp


def main():
    con = cp.connect()
    rows = con.execute(
        "SELECT s.id, s.key, s.harness, s.started_at, s.last_active_at, s.ended_at,"
        " (SELECT COUNT(*) FROM pages p WHERE p.session_id = s.id) AS pages,"
        " (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS messages,"
        " (SELECT COUNT(*) FROM topics t WHERE t.session_id = s.id) AS topics"
        " FROM sessions s ORDER BY s.id DESC"
    ).fetchall()
    for r in rows:
        state = "ended " + r["ended_at"] if r["ended_at"] else "active"
        print(
            "%d %s [%s] %s pages=%d messages=%d topics=%d started=%s last=%s"
            % (
                r["id"],
                r["key"],
                r["harness"],
                state,
                r["pages"],
                r["messages"],
                r["topics"],
                r["started_at"],
                r["last_active_at"],
            )
        )


if __name__ == "__main__":
    main()
