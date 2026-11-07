#!/usr/bin/env python3
"""Remove a project's harness-capture subscription.

usage: cp_unsubscribe.py [PROJECT_DIR]   (default: current project root)

Hooks stop running for the project immediately; its database is left in place.
"""
import sys

import cpcommon as cp


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__.strip())
    root = cp.root_for(sys.argv[1] if len(sys.argv) > 1 else None)
    reg = cp.load_registry()
    if reg.pop(root, None) is not None:
        cp.save_registry(reg)
        print("unsubscribed %s (database kept)" % root)
    else:
        print("%s was not subscribed" % root)


if __name__ == "__main__":
    main()
