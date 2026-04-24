# `wove.weave`

`wove.weave` defines the reusable workflow class model for workflows that should be packaged as classes, inherited, extended, or reused across call sites.

`Weave` is the reference for class-based workflows: reusable task graphs, inheritable templates, and the places where class definitions differ from inline `with weave() as w:` blocks.

## Core Idea

Inline weaves are best when the workflow belongs exactly where it is written. `Weave` classes are best when the same dependency graph should be reused, inherited, or partially overridden.

## Related Pages

- [Inheritable Weaves](../../how-to/inheritable-weaves.md): practical guide for reusable workflow classes.
- [`wove.context`](wove.context.md): context manager behavior.
- [`wove`](wove.md): public import surface.

## API Details

```{eval-rst}
.. automodule:: wove.weave
   :members:
   :no-index:
```
