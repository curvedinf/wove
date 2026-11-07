#!/usr/bin/env python3
"""Create the context-paging database and schema without other effects."""
import cpcommon as cp


def main():
    con = cp.connect()
    con.close()
    print(cp.db_path())


if __name__ == "__main__":
    main()
