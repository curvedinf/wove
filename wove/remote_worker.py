import os
import sys

from .remote import payload_from_b64, run_remote_payload


def main() -> int:
    if len(sys.argv) > 1:
        payload_b64 = sys.argv[1]
    else:
        payload_b64 = os.environ.get("WOVE_REMOTE_PAYLOAD")

    if not payload_b64:
        raise SystemExit("Missing remote payload. Pass it as argv[1] or WOVE_REMOTE_PAYLOAD.")

    run_remote_payload(payload_from_b64(payload_b64))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
