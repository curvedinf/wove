#!/usr/bin/env python3
"""Subscription gate: exit 0 iff the project is subscribed.

usage: cp_subscribed.py [PROJECT_DIR]   (default: current project root)

Harness-side check for "already installed and activated for this project".
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__.strip())
    root = cp.root_for(sys.argv[1] if len(sys.argv) > 1 else None)
    entry = cp.load_registry().get(root)
    if entry:
        print("subscribed %s db=%s" % (root, entry.get("db", "?")))
        return 0
    print("not subscribed %s" % root)
    return 1


if __name__ == "__main__":
    sys.exit(main())
