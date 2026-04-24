# Patterns For Production

Production code usually needs more than one kind of work to happen at the same time: database reads, service calls, file parsing, model requests, report rendering, and work that belongs outside the request process. Wove is useful when those steps belong in one readable workflow, but should not run one after another.

This page is organized by the Wove pattern, not by the application domain. An API endpoint, a report builder, and an inference pipeline can all be the same pattern if Wove is doing the same thing: running independent tasks, waiting for their results, and merging them into one value.

The examples use real libraries to show where each pattern appears in production code. The imports show the concrete libraries involved. Keep the orchestration shape, then replace placeholder functions, models, and service names with objects from your project. Worker-service examples use project-owned handler names such as `handle_wove_command(...)`; the executor reference defines the frame contract those handlers must satisfy.

## Fan Out Independent Work, Then Merge

This pattern is for a workflow that needs several unrelated inputs before it can produce one result. Wove runs the independent tasks as soon as the context exits, then runs the merge task when its named parameters are available.

The important shape is the dependency graph: `profile`, `billing`, and `support` do not depend on each other, so Wove can run them together. `summary(profile, billing, support)` names all three results, so Wove waits until every branch is complete before building the response.

Example application: aggregate several service calls for one API response.

```python
from pydantic import BaseModel
from wove import weave
import httpx


class AccountSummary(BaseModel):
    account_id: str
    plan: str
    balance: int
    open_ticket_count: int


async def account_summary(account_id: str) -> AccountSummary:
    async with httpx.AsyncClient(timeout=10.0) as client:
        async with weave() as w:
            @w.do
            async def profile():
                response = await client.get(f"https://accounts.internal/accounts/{account_id}")
                response.raise_for_status()
                return response.json()

            @w.do
            async def billing():
                response = await client.get(f"https://billing.internal/accounts/{account_id}")
                response.raise_for_status()
                return response.json()

            @w.do
            async def support():
                response = await client.get(f"https://support.internal/accounts/{account_id}/tickets")
                response.raise_for_status()
                return response.json()

            @w.do
            def summary(profile, billing, support):
                return AccountSummary(
                    account_id=account_id,
                    plan=profile["plan"],
                    balance=billing["balance"],
                    open_ticket_count=len(support["open"]),
                )

    return w.result.final
```

The same pattern fits any case where the branches are different facts about the same final answer. A FastAPI handler can load database rows and remote service state in parallel. A report builder can fetch account data, usage rows, and billing data before rendering. An inference pipeline can run retrieval, classification, and drafting before choosing the final response. Those are different applications, but Wove is still doing the same fan-out/fan-in work.

## Template a Workflow, Then Override the Variable Parts

This pattern is for a workflow shape that repeats across a project, but has one or two steps that vary by caller, tenant, test, or deployment. Wove lets you define the common task graph as a `Weave` class, then override selected tasks inline without copying the whole workflow.

The important shape is the stable graph. `AccountHealthCheck` defines the shared branches and the final merge. A caller can run it as-is, or replace `account(...)` while keeping the inherited `billing(...)` and `health_check(...)` tasks.

Example application: standardize account health checks while letting tenant-specific callers change how account data is loaded.

```python
# workflows.py
from wove import Weave
import httpx


class AccountHealthCheck(Weave):
    @Weave.do(timeout=10.0)
    async def account(self, account_id: int):
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"https://accounts.internal/accounts/{account_id}")
            response.raise_for_status()
            return response.json()

    @Weave.do(timeout=10.0)
    async def billing(self, account_id: int):
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"https://billing.internal/accounts/{account_id}")
            response.raise_for_status()
            return response.json()

    @Weave.do
    def health_check(self, account, billing):
        return {
            "account_id": account["id"],
            "plan": account["plan"],
            "past_due": billing["past_due"],
        }
```

```python
# normal caller
from wove import weave
from .workflows import AccountHealthCheck


async def account_health(account_id: int):
    async with weave(AccountHealthCheck, account_id=account_id) as w:
        pass

    return w.result.health_check
```

```python
# tenant-specific caller
from wove import weave
from .workflows import AccountHealthCheck


async def tenant_account_health(account_id: int, tenant_slug: str):
    async with weave(AccountHealthCheck, account_id=account_id, tenant_slug=tenant_slug) as w:
        @w.do(timeout=15.0)
        async def account(account_id: int, tenant_slug: str):
            return await load_tenant_account(tenant_slug, account_id)

    return w.result.health_check
```

Use this when the repeated workflow is valuable in its own right. If every caller overrides most of the tasks, keep the workflow inline instead; the class should preserve the shape, not hide it.

## Map a Work Set, Then Reduce

This pattern is for repeated work where one task produces or receives a list of inputs, another task runs once per item, and a final task combines the mapped results. Wove treats the mapped task's result as a list, so downstream tasks consume it through the same parameter-name dependency model as any other task.

The important shape is `@w.do("object_keys", workers=16)`: the string points to the upstream iterable, and `workers` caps how many mapped instances can run at once.

Example application: parse many objects from S3, then roll them up.

```python
from io import BytesIO
from wove import merge, weave
import boto3
import duckdb
import polars as pl

s3 = boto3.client("s3")


def normalize_frame(frame):
    return frame.with_columns(pl.col("customer_id").cast(pl.Utf8))


def daily_rollup(bucket: str, prefix: str):
    with weave(bucket=bucket, prefix=prefix) as w:
        @w.do
        def object_keys(bucket, prefix):
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [item["Key"] for item in response.get("Contents", [])]

        @w.do("object_keys", workers=16)
        def parsed_file(item, bucket):
            raw = s3.get_object(Bucket=bucket, Key=item)["Body"].read()
            return pl.read_parquet(BytesIO(raw))

        @w.do
        async def combined(parsed_file):
            normalized = await merge(normalize_frame, parsed_file)
            return pl.concat(normalized)

        @w.do
        def rollup(combined):
            connection = duckdb.connect()
            connection.register("events", combined)
            return connection.sql("""
                select customer_id, count(*) as event_count
                from events
                group by customer_id
            """).pl()

    return w.result.rollup
```

When the mapped work calls a dependency that has its own limits, keep those limits visible in the mapped task. Wove controls task fanout with `workers`; the client, pool, or limiter still owns connection and rate behavior.

Example application: enrich customer records without overwhelming the profile service.

```python
from aiolimiter import AsyncLimiter
from wove import weave
import httpx

limiter = AsyncLimiter(120, 60)


async def enrich_customers(customer_ids: list[int]):
    async with httpx.AsyncClient(timeout=10.0) as client:
        async with weave(customer_ids=customer_ids) as w:
            @w.do("customer_ids", workers=20)
            async def enrichment(item):
                async with limiter:
                    response = await client.get(f"https://profiles.internal/customers/{item}")
                    response.raise_for_status()
                    return response.json()

            @w.do
            def by_customer_id(enrichment):
                return {row["customer_id"]: row for row in enrichment}

    return w.result.by_customer_id
```

## Detach a Workflow from the Caller

This pattern is for work that belongs to the request, command, or event that triggered it, but should not make that caller wait. Wove keeps the workflow written inline and starts it in the background when the context exits.

This is not a durability pattern. In-process background work is appropriate for follow-up work that can tolerate process loss. If the work must survive restarts or needs queue semantics, use a remote task environment instead.

Example application: return `202 Accepted` from an HTTP endpoint while follow-up work continues.

```python
from fastapi import FastAPI, status
from wove import weave
import httpx

app = FastAPI()


@app.post("/orders", status_code=status.HTTP_202_ACCEPTED)
def create_order(payload: dict):
    order = save_order(payload)

    def record_background_result(result):
        mark_order_followup_complete(order.id, error=result.exception)

    with weave(background=True, order_id=order.id, on_done=record_background_result) as w:
        @w.do
        def audit_log(order_id):
            write_audit_event("order.created", order_id=order_id)

        @w.do
        async def enrichment(order_id):
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post("https://enrichment.internal/orders", json={"order_id": order_id})
                response.raise_for_status()
                return response.json()

        @w.do
        def confirmation_email(order_id):
            send_confirmation_email(order_id)

    return {"order_id": order.id, "status": "accepted"}
```

## Send a Task to a Direct Worker Service

This pattern is for a project that already has a service boundary and wants selected Wove tasks to run on the other side of it. Wove still builds the local dependency graph, but the selected task frame is sent through a network executor instead of being run in the weave process.

Use this when the worker service is yours and the operational behavior is simple request/response or stream delivery. If queueing, scheduling, retries, or cluster placement should be owned by Celery, Temporal, Ray, or another system, use the backend-owned execution pattern instead.

Example application: keep lightweight orchestration in the caller and run report generation in an internal worker service.

```python
# wove_config.py
WOVE_CONFIG = {
    "default_environment": "default",
    "environments": {
        "default": {"executor": "local"},
        "workers": {
            "executor": "https",
            "executor_config": {
                "url": "https://workers.internal/wove/tasks",
                "security": "env:WOVE_WORKER_SECRET",
                "timeout": 30.0,
            },
        },
    },
}
```

```python
# submitting process
import wove
from wove import weave

wove.config()

with weave() as w:
    @w.do
    def account():
        return load_account()

    @w.do(environment="workers")
    def report(account):
        return build_report(account)
```

```python
# worker service sketch
from fastapi import FastAPI, Request
from wove.security import NetworkExecutorSecurity

app = FastAPI()
security = NetworkExecutorSecurity.from_config("env:WOVE_WORKER_SECRET")


@app.post("/wove/tasks")
async def wove_tasks(request: Request):
    body = await request.body()
    security.verify_headers(
        headers=request.headers,
        transport="http",
        target=request.url.path,
        body=body,
    )
    return await handle_wove_command(body)
```

The transport can change without changing the weave shape. Use HTTP/HTTPS for simple request/response services, gRPC when that is already the service boundary, and WebSocket when the worker needs to stream heartbeats or progress events while the task runs.

```python
# wove_config.py
WOVE_CONFIG = {
    "default_environment": "grpc_workers",
    "environments": {
        "grpc_workers": {
            "executor": "grpc",
            "executor_config": {
                "target": "workers.internal:9000",
                "method": "/wove.network_executor.WorkerService/Send",
                "secure": True,
                "security": "env:WOVE_WORKER_SECRET",
            },
        },
        "socket_workers": {
            "executor": "websocket",
            "executor_config": {
                "url": "wss://workers.internal/wove",
                "security": "env:WOVE_WORKER_SECRET",
                "open_timeout": 10.0,
            },
            "delivery_heartbeat_seconds": 15.0,
        },
    },
}
```

## Send a Task to Backend-Owned Execution

This pattern is for work that should enter infrastructure your project already runs: a queue, workflow engine, cluster, batch system, or scheduler. Wove owns the inline dependency graph and result delivery back to the weave. The backend owns worker placement, queueing, scheduling, and its own operational controls.

The selected task still looks like a normal Wove task. The difference is the environment: `@w.do(environment="reports")` routes that task through the configured backend adapter.

Example application: submit report rendering to Celery while keeping the rest of the weave local. The same task-routing pattern applies to Temporal, Ray, RQ, Taskiq, ARQ, Dask, Kubernetes Jobs, AWS Batch, and Slurm.

```python
# wove_config.py
WOVE_CONFIG = {
    "default_environment": "default",
    "environments": {
        "default": {"executor": "local"},
        "reports": {
            "executor": "celery",
            "executor_config": {
                "broker_url": "redis://redis:6379/0",
                "task_name": "myapp.wove_task",
                "callback_url": "https://web.internal/wove/events/shared-secret",
                "callback_token": "shared-secret",
            },
            "delivery_timeout": 60.0,
            "delivery_cancel_mode": "best_effort",
        },
    },
}
```

```python
# submitting process
import wove
from wove import weave

wove.config()

with weave() as w:
    @w.do
    def account():
        return load_account()

    @w.do(environment="reports")
    def report(account):
        return render_report(account)
```

Backend workers must be able to reach the callback URL in the environment config. The adapter pages in the reference section show the worker entrypoint for each backend.

## Instrument a Workflow Run

This pattern is for a workflow that is important enough to alert on. In production, the useful question is not just whether the request failed; it is which task made the workflow slow, which task failed first, and whether any parallel work was cancelled as a consequence.

Wove records task timings, cancelled task names, the execution plan, and the first exception on the result object. Use that data at the boundary of the workflow, where the request ID, user ID, job ID, or tenant ID is still available.

Example application: build one dashboard response and emit enough telemetry to debug the production run later.

```python
from opentelemetry import trace
from prometheus_client import Histogram
from wove import weave
import sentry_sdk
import structlog

log = structlog.get_logger()
tracer = trace.get_tracer(__name__)
TASK_SECONDS = Histogram(
    "dashboard_weave_task_seconds",
    "Task duration inside the dashboard Wove workflow.",
    ["task"],
)


def record_dashboard_run(w, *, request_id: str, user_id: int):
    slowest_task, slowest_seconds = max(
        w.result.timings.items(),
        key=lambda item: item[1],
        default=("none", 0.0),
    )

    for task_name, seconds in w.result.timings.items():
        TASK_SECONDS.labels(task=task_name).observe(seconds)

    if w.result.exception is not None:
        sentry_sdk.capture_exception(w.result.exception)
        log.error(
            "dashboard_weave_failed",
            request_id=request_id,
            user_id=user_id,
            error_type=type(w.result.exception).__name__,
            error=str(w.result.exception),
            cancelled=sorted(w.result.cancelled),
            slowest_task=slowest_task,
            slowest_seconds=slowest_seconds,
        )
        return

    log.info(
        "dashboard_weave_completed",
        request_id=request_id,
        user_id=user_id,
        task_count=len(w.result.timings),
        tier_count=len(w.execution_plan["tiers"]) if w.execution_plan else 0,
        slowest_task=slowest_task,
        slowest_seconds=slowest_seconds,
    )


def build_dashboard(user_id: int, request_id: str):
    with tracer.start_as_current_span("dashboard.weave") as span:
        span.set_attribute("request.id", request_id)
        span.set_attribute("user.id", user_id)

        with weave(user_id=user_id, request_id=request_id, error_mode="return") as w:
            @w.do
            def profile(user_id, request_id):
                log.info("loading_profile", user_id=user_id, request_id=request_id)
                return load_profile(user_id)

            @w.do
            def permissions(user_id, request_id):
                log.info("loading_permissions", user_id=user_id, request_id=request_id)
                return load_permissions(user_id)

            @w.do
            def dashboard(profile, permissions, request_id):
                log.info("building_dashboard", request_id=request_id)
                return {"profile": profile, "permissions": permissions}

    record_dashboard_run(w, request_id=request_id, user_id=user_id)

    if w.result.exception is not None:
        raise w.result.exception

    return w.result.dashboard
```
