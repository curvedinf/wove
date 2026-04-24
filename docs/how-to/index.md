# Topics

The topics are ordered as a learning path. The path begins with the shape of a weave, then adds fanout, task-level controls, reusable workflow structure, helper utilities, failure handling, and production execution choices.

- [The Basics](the-basics.md): the core `weave()` and `@w.do` workflow.
- [Task Mapping](task-mapping.md): running one task or helper callable across many inputs and collecting the results.
- [Task Quality of Life](task-quality-of-life.md): task options that replace retry, timeout, fanout, and routing boilerplate.
- [Inheritable Weaves](inheritable-weaves.md): reusable workflow templates with inline overrides.
- [Helper Functions](helper-functions.md): small data-shaping tools that keep task glue readable.
- [Error Handling](error-handling.md): how task, background, and remote delivery failures surface.
- [Debugging & Introspection](debugging-introspection.md): graph, timing, mapping, and failure inspection.
- [Background Processing](background-processing.md): running a whole weave after the caller continues.
- [Remote Task Environments](remote-task-environments.md): sending selected tasks to other processes, services, queues, clusters, or schedulers.
- [Patterns For Production](patterns-for-production.md): common production workflow shapes built from Wove's core task, mapping, policy, background, and remote-execution building blocks.

```{toctree}
:maxdepth: 1
:hidden:

the-basics
task-mapping
task-quality-of-life
inheritable-weaves
helper-functions
error-handling
debugging-introspection
background-processing
remote-task-environments
patterns-for-production
```
