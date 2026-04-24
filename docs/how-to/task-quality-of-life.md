# Task Quality of Life

Task quality-of-life options reduce the boilerplate that usually grows around async workflows after the first version works. A weave can start with plain `@w.do` tasks, then absorb the operational details that would normally become retry loops, timeout wrappers, semaphores, rate-limit sleeps, thread-pool handoffs, and routing branches.

Task quality-of-life options describe how a task should run. The task body should still describe the data it produces.

## Task Options

Task options are the keyword arguments that tell Wove how to operate a task. A task often starts as a simple call to a database, API, model, parser, or renderer. As soon as that call runs in production, the surrounding code tends to grow: retry the transient failure, stop waiting after a deadline, do not launch too many copies, and send the expensive step somewhere else.

With Wove, operational concerns stay on the task declaration. The following example maps over customer IDs and applies the relevant task options directly to `@w.do(...)`.

```python
from wove import weave


with weave(raw_customer_ids=load_customer_ids(), max_pending=10_000) as w:
    @w.do
    def customer_ids(raw_customer_ids):
        return raw_customer_ids

    @w.do("customer_ids", workers=25, limit_per_minute=600, retries=2, timeout=10.0)
    async def profile(item):
        return await profile_service.fetch(item)

    @w.do
    def by_customer_id(profile):
        return {row["id"]: row for row in profile}
```

The `profile(...)` function only says how to fetch one profile. The decorator says how Wove should operate that task: map over the customer IDs, run at most 25 at once, pace launches, retry transient failures, and stop waiting after 10 seconds.

## Sync And Async Tasks

Sync and async tasks can live in the same weave. Wove accepts `def` and `async def` tasks together, so synchronous calls can sit beside async API calls without making the call site choose one style for the entire workflow.

```python
from wove import weave


with weave(account_id="acct_123") as w:
    @w.do
    def account(account_id):
        return load_account_from_database(account_id)

    @w.do
    async def profile(account):
        return await fetch_profile(account["profile_id"])

    @w.do
    def response(account, profile):
        return {"account": account, "profile": profile}
```

Mixed sync/async task support removes the wrapper code that usually appears around mixed workflows: no `asyncio.to_thread(...)` at every synchronous call site, no separate sync and async workflow versions, and no manual result passing between the two styles.

## Retries And Timeouts

Retries and timeouts are task-level failure controls. Declaring retries and timeouts on `@w.do(...)` makes the workflow easier to scan than hiding retry loops inside the function body.

```python
from wove import weave


with weave(order_id="ord_123") as w:
    @w.do(retries=3, timeout=5.0)
    async def order(order_id):
        return await orders_api.fetch(order_id)

    @w.do
    def receipt(order):
        return render_receipt(order)
```

Use `retries` when running the task again is safe. Use `timeout` when the task has a real deadline. If a task performs a side effect, make that side effect idempotent before adding retries.

## Fanout Controls

Fanout controls limit how mapped task instances are launched. Mapped tasks are where workflow code usually accumulates the most scaffolding. Wove already collects mapped results into a list. `workers` and `limit_per_minute` handle the common controls around that fanout.

```python
from wove import weave


with weave(urls=sitemap_urls(), max_pending=5_000) as w:
    @w.do("urls", workers=8, limit_per_minute=120)
    async def page(item):
        return await fetch_page(item)

    @w.do
    def successful_pages(page):
        return [response for response in page if response.status_code == 200]
```

`workers` replaces the local semaphore around the mapped call. `limit_per_minute` replaces launch pacing code. `max_pending` belongs on the weave because it protects the whole run from accidentally expanding into too much queued work.

## Task Environments

Task environments are named execution profiles. Most workflows have one or two tasks that are operationally different from the rest. A report render might belong in Celery, an embedding step might belong on a GPU worker, and a local fetch might still be best in the current process.

Use `environment=...` on the task that needs different execution. The rest of the weave stays local and readable.

In the example below, `local` runs tasks in the current process and `reports` sends selected work to Celery.

```python
import wove
from wove import weave


wove.config(
    default_environment="local",
    environments={
        "local": {"executor": "local"},
        "reports": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "task_name": "myapp.wove_task",
            },
        },
    },
)

with weave(order_id="ord_123") as w:
    @w.do
    def order(order_id):
        return load_order(order_id)

    @w.do(environment="reports", timeout=30.0)
    def report(order):
        return render_pdf_report(order)
```

The task name still describes the data produced by the weave. The environment only changes where that task runs.

## Delivery Policy

Delivery policy describes what Wove expects from the executor boundary. A local timeout only describes how long Wove waits for the task function. Delivery options describe how Wove handles work that has crossed into another process, worker service, queue, scheduler, or backend.

Delivery policy only matters when a task leaves the local process. Delivery policy appears here because it is still task behavior: the task declares the delivery contract it needs from the executor boundary.

```python
from wove import weave


with weave(order_id="ord_123") as w:
    @w.do
    def order(order_id):
        return load_order(order_id)

    @w.do(
        environment="reports",
        delivery_timeout=60.0,
        delivery_idempotency_key="report:{order_id}",
        delivery_cancel_mode="best_effort",
        delivery_heartbeat_seconds=10.0,
        delivery_max_in_flight=100,
        delivery_orphan_policy="requeue",
    )
    def report(order, order_id):
        return render_pdf_report(order)
```

Use delivery options when the way work is handed off matters to the task's contract: how long Wove waits for the remote result, how the remote job is deduped, whether cancellation needs acknowledgement, how stale workers are detected, how many remote jobs can be in flight, and what happens to pending work when the local weave is stopping.

## Configuration Defaults

Configuration defaults are the process-wide values Wove applies before task-level options. Task options are clearest when they explain why one task is special. If every task in a project has the same retry, timeout, fanout, or delivery policy, make that the default once.

Project configuration stores those defaults before a weave runs. The example below sets task quality-of-life defaults directly in startup code.

```python
import wove


wove.config(
    default_environment="default",
    environments={
        "default": {
            "executor": "local",
            "retries": 2,
            "timeout": 10.0,
            "workers": 20,
            "limit_per_minute": 600,
            "max_pending": 10_000,
        },
    },
)
```

The same defaults can live in `wove_config.py` when a project benefits from one configuration file. Calling `wove.config()` with no arguments attempts to autoload `wove_config.py` from the current working directory or one of its parents.

```python
# wove_config.py
WOVE_CONFIG = {
    "default_environment": "default",
    "environments": {
        "default": {"executor": "local"},
        "reports": {
            "executor": "stdio",
            "executor_config": {"command": ["python", "-m", "my_worker"]},
            "retries": 3,
        },
    },
    "max_workers": 64,
    "delivery_timeout": 15.0,
}
```

```python
import wove

wove.config()  # autoload
# or:
# wove.config(config_file="/abs/path/to/custom_config.py")
```

Task-level declarations still win when a task needs a different value. Configuration defaults keep project-wide policy out of the inline weave while preserving the ability to make important task behavior visible where needed.
