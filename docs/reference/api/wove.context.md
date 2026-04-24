# `wove.context`

`wove.context` contains the context manager implementation behind the public `weave` entrypoint. Most users should import `weave` from `wove`; this module is useful when you need to understand context-manager behavior exactly.

When you need to understand exactly what `with weave(...) as w:` creates, this module shows the lifecycle around setup, task collection, block exit, execution, and teardown.

## Public Surface

`WoveContextManager` is exported as `wove.weave`. Using the class directly is rarely necessary, but its methods define the context lifecycle used by every inline weave.

## Related Pages

- [`wove`](wove.md): public import surface.
- [`wove.weave`](wove.weave.md): task registration and reusable weave class behavior.
- [`wove.runtime`](wove.runtime.md): runtime configuration applied when a weave starts.

## API Details

```{eval-rst}
.. automodule:: wove.context
   :members:
```
