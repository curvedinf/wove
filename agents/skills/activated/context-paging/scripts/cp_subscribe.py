#!/usr/bin/env python3
"""Register a project for harness capture (per-project subscription).

usage: cp_subscribe.py [PROJECT_DIR]   (default: current project root)

Adds the project to ${XDG_CONFIG_HOME:-~/.config}/context-paging/projects.json,
which is the only thing harness hooks check before running. Run after the
harness plugin is installed and verified, so subscription means "active".
"""
import os
import sys

import cpcommon as cp


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__.strip())
    root = cp.root_for(sys.argv[1] if len(sys.argv) > 1 else None)
    os.environ["CP_PROJECT"] = root
    con = cp.connect()
    con.close()
    db = cp.db_path()
    reg = cp.load_registry()
    reg[root] = {
        "db": db,
        "scripts": os.path.dirname(os.path.abspath(__file__)),
        "harness": os.environ.get("CP_HARNESS") or "generic",
        "subscribed_at": cp.utc_now(),
    }
    cp.save_registry(reg)
    print("subscribed %s" % root)
    print("db=%s" % db)
    ignore = os.path.join(root, ".gitignore")
    try:
        with open(ignore, encoding="utf-8") as f:
            covered = "agents/context-paging" in f.read()
    except OSError:
        covered = False
    if not covered:
        print("note: add /agents/context-paging/ to %s (the database is local data)" % ignore)


if __name__ == "__main__":
    main()
