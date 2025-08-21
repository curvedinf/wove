# Save as example.py and run `python example.py`
# or copy-paste into a Python console.
import time
from wove import weave

# The `weave` block can be used without `async with`.
# Wove will manage the event loop behind the scenes.
with weave() as w:
    # This task takes 1 second to run.
    @w.do
    def magic_number():
        time.sleep(1.0)
        return 42

    # This task also takes 1 second. Wove runs it
    # in parallel with `magic_number` in a background thread.
    @w.do
    def important_text():
        time.sleep(1.0)
        return "The meaning of life"

    # This task depends on the first two. It runs only
    # after both are complete.
    @w.do
    def put_together(important_text, magic_number):
        return f"{important_text} is {magic_number}!"

# The block finishes here, taking ~1 second total.
# Access the result of the final task via `w.result.final`.
print(w.result.final)

# Access other task results by name.
print(f"The magic number was {w.result.magic_number}")
