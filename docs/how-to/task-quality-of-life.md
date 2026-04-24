# Task Quality of Life

Task quality-of-life options reduce the boilerplate that usually grows around async workflows after the first version works. A weave can start with plain `@w.do` tasks, then absorb the operational details that would normally become retry loops, timeout wrappers, semaphores, rate-limit sleeps, thread-pool handoffs, and routing branches.

The important idea is that these options describe how a task should run. The task body should still describe the data it produces.

## Keep The Function Body Clean

A task often starts as a simple call to a database, API, model, parser, or renderer. As soon as that call runs in production, the surrounding code tends to grow: retry the transient failure, stop waiting after a deadline, do not launch too many copies, and send the expensive step somewhere else.

With Wove, those concerns stay on the task declaration. The example uses task mapping from the previous topic, then adds the task options this page introduces.

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

## Stop Writing Sync/Async Glue

Wove accepts `def` and `async def` tasks in the same weave. Synchronous tasks can sit beside async API calls without making the call site choose one style for the entire workflow.

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

That removes the wrapper code that usually appears around mixed workflows: no `asyncio.to_thread(...)` at every synchronous call site, no separate sync and async workflow versions, and no manual result passing between the two styles.

## Put Failure Policy On The Task

Retries and timeouts are part of how a task is operated. Keeping them on `@w.do(...)` makes the workflow easier to scan than hiding retry loops inside the function body.

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

## Shape Fanout Without A Semaphore

Mapped tasks are where workflow code usually accumulates the most scaffolding. Wove already collects mapped results into a list. `workers` and `limit_per_minute` handle the common controls around that fanout.

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

## Route The Outlier, Not The Whole Workflow

Most workflows have one or two tasks that are operationally different from the rest. A report render might belong in Celery, an embedding step might belong on a GPU worker, and a local fetch might still be best in the current process.

Use `environment=...` on the task that needs different execution. The rest of the weave stays local and readable.

An environment is a named execution profile. In the example below, `local` runs tasks in the current process and `reports` sends selected work to Celery.

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

## Give Remote Tasks Delivery Rules

Remote work has one more layer of boilerplate: delivery. A local timeout only describes how long Wove waits for the task function. Delivery options describe how Wove handles the executor boundary when work has crossed into another process, worker service, queue, scheduler, or backend.

Delivery policy only matters when a task leaves the local process. It appears here because these are task options: the task declares the delivery contract it needs from the executor boundary.

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

## Move Repeated Policy Into Configuration

Task options are clearest when they explain why one task is special. If every task in a project has the same retry, timeout, fanout, or delivery policy, make that the default once.

Project configuration is the process-wide place to define defaults before a weave runs. The example below only shows task quality-of-life defaults.

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

Task-level declarations still win when a task needs a different value. That keeps project policy out of the weave while preserving the ability to make important task behavior visible.
