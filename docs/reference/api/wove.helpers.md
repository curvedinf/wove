# `wove.helpers`

`wove.helpers` contains small data-shaping utilities that make task dependencies easier to express. They are exported from `wove` for normal use.

These helpers keep common data-shaping work inside the weave without forcing extra task functions for every list, dictionary, batch, or optional-value transformation.

## Common Helpers

- `flatten`: flatten nested iterables.
- `fold`: combine values with a reducer.
- `batch`: split an iterable into fixed-size batches.
- `undict`: unpack dictionary values.
- `redict`: rebuild dictionaries from key/value pairs.
- `denone`: remove `None` values.
- `sync_to_async`: wrap sync functions for async contexts.

## API Details

```{eval-rst}
.. automodule:: wove.helpers
   :members:
```
