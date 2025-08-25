import asyncio
import os
import time
import unittest

from wove import weave


class TestDetached(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "fork"), "os.fork not available")
    def test_detached_execution(self):
        # Use a local file to signal that the detached process has run.
        # This is more container-friendly than using /tmp.
        output_file = "detached_test_output.txt"

        try:
            # Use a synchronous `with` block for detached execution.
            with weave(detach=True) as w:

                @w.do
                def write_to_file():
                    # This code runs in the detached grandchild process
                    with open(output_file, "w") as f:
                        f.write("detached task executed")
                    return "done"

            # Give the detached process a moment to run and write the file.
            time.sleep(3)

            # Check if the file was written by the detached process
            with open(output_file, "r") as f:
                content = f.read()

            self.assertEqual(content, "detached task executed")

        except FileNotFoundError:
            self.fail("Detached process did not write the output file.")
        finally:
            # Clean up the temporary file
            if os.path.exists(output_file):
                os.unlink(output_file)
