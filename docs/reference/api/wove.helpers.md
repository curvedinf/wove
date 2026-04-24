# `wove.helpers`

`wove.helpers` contains small data-shaping utilities that make task dependencies easier to express. They are exported from `wove` for normal use.

Use helpers when a small list, dictionary, batch, or optional-value transformation belongs inside the weave but does not deserve a throwaway task function.

## Common Helpers

- `flatten`: flatten nested iterables.
- `fold`: split an iterable into fixed-size groups.
- `batch`: split an iterable into a fixed number of groups.
- `undict`: turn a dictionary into key/value pairs.
- `redict`: rebuild a dictionary from key/value pairs.
- `denone`: remove `None` values.
- `sync_to_async`: wrap sync functions for async contexts.

## API Details

```{eval-rst}
.. automodule:: wove.helpers
   :members:
```
