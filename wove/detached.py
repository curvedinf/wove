import os
import sys


def check_and_detach():
    """
    Performs a double-fork to detach the process and run in the background.
    Returns True for the original process and False for the grandchild.
    The intermediate child process exits.
    On non-Unix systems, it does nothing and returns False.
    """
    if not hasattr(os, "fork"):
        return False

    # First fork
    pid = os.fork()
    if pid > 0:
        # Parent process: return True to signal detachment
        return True

    # Child process (intermediate)
    os.setsid()

    # Second fork
    pid = os.fork()
    if pid > 0:
        # Intermediate process: exit
        os._exit(0)

    # Grandchild process: continue execution
    # When running under pytest, do not redirect stdio or change directory,
    # as it interferes with test execution and output capturing.
    if 'pytest' not in sys.modules:
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        os.umask(0)
        os.chdir("/")

    return False
