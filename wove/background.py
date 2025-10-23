import asyncio
import sys
import cloudpickle
import os
import pickle


def main():
    """
    The entry point for a forked weave process.
    This function deserializes a WoveContextManager instance from a file,
    executes it, and then calls the on_done callback.
    """
    if len(sys.argv) != 2:
        print("Usage: python -m wove.background <context_file>", file=sys.stderr)
        sys.exit(1)

    context_file = sys.argv[1]

    try:
        with open(context_file, "rb") as f:
            wcm = cloudpickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        print(f"Error deserializing context: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up the temporary file
        if os.path.exists(context_file):
            os.remove(context_file)

    async def run_weave():
        # Temporarily disable background mode to allow execution in __aexit__
        wcm._background = False
        try:
            async with wcm:
                pass  # The work is done in __aexit__
        finally:
            # Restore the flag
            wcm._background = True

        if wcm._on_done_callback:
            # Check if the callback is async
            if asyncio.iscoroutinefunction(wcm._on_done_callback):
                await wcm._on_done_callback(wcm.result)
            else:
                wcm._on_done_callback(wcm.result)

    asyncio.run(run_weave())


if __name__ == "__main__":
    main()
