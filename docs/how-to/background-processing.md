# Background Processing

Wove can run an entire weave in the background when the current request, command, or script should continue without waiting for every task result. Background work can stay attached to the current Python process in a thread or move into a detached forked process.

To enable background processing, set `background=True` in the `weave()` call. Wove's background processing supports two modes:

- **Embedded mode (default)**: `weave(background=True)` will run the weave in a new background thread using the `threading` module attached to the current Python process.
- **Forked mode**: `weave(background=True, fork=True)` will run the weave in a new detached Python process. Choose forked mode when the background work should continue after the current process or server worker returns. In an HTTP server worker, for example, the request can finish quickly while the forked Wove process continues processing outside the worker pool.

Embedded mode stays inside the current Python process, so the base install is enough. Forked mode has to carry the weave context into a separate Python process, which requires Wove's optional dispatch serializer:

```bash
pip install "wove[dispatch]"
```

For both modes, `weave()` accepts an optional `on_done` callback that runs when the background weave completes. The callback receives the weave's result object, the same object available as `w.result` in foreground weaves.

```python
import time
from wove import weave


def my_callback(result):
    print(f"Background weave complete! Final result: {result.final}")


# Run in a background thread
with weave(background=True, on_done=my_callback) as w:
    @w.do
    def long_running_task():
        time.sleep(2)
        return "Done!"

print("Main program continues to run...")
# After 2 seconds, the callback will be executed.
```

Before you fork a weave, decide how the child process should report completion. Embedded callbacks can access the current Python process, but forked callbacks run in the child process; use a database, file, queue, or other signaling system when the original process needs the result. Forked mode also serializes the local Python context around the `with` block so the child can preserve task behavior, so keep large local variables out of that scope when you do not want them copied into the fork.

## Persist Forked Results For Later Requests

Forked background work has one important consequence: completion happens outside the request process that started it. This section shows how to hand the result through shared storage instead of parent-process memory. The request creates a durable job record, the forked `on_done` callback writes the final result or error, and a later request reads the stored job state.

```python
import json
import sqlite3
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request
from wove import weave


app = Flask(__name__)
DB_PATH = Path("background-results.sqlite3")


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS report_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                data_json TEXT,
                error TEXT,
                updated_at REAL NOT NULL
            )
            """
        )


def write_job(job_id, status, data=None, error=None):
    data_json = None if data is None else json.dumps(data)
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO report_jobs (job_id, status, data_json, error, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                data_json = excluded.data_json,
                error = excluded.error,
                updated_at = excluded.updated_at
            """,
            (job_id, status, data_json, error, time.time()),
        )


def read_job(job_id):
    with connect_db() as db:
        return db.execute(
            "SELECT job_id, status, data_json, error FROM report_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()


init_db()


@app.post("/reports")
def create_report():
    report_spec = request.get_json(force=True)
    job_id = uuid.uuid4().hex
    write_job(job_id, "running")

    def record_result(result):
        if result.exception is not None:
            write_job(job_id, "failed", error=str(result.exception))
            return

        write_job(job_id, "complete", data=result.final)

    with weave(
        background=True,
        fork=True,
        on_done=record_result,
        report_spec=report_spec,
    ) as w:
        @w.do
        def fetch_report_rows(report_spec):
            time.sleep(2)
            return [
                {"sku": "A-100", "units": report_spec.get("units", 1)},
                {"sku": "B-200", "units": 4},
            ]

        @w.do
        def summarize_report(fetch_report_rows):
            return {
                "row_count": len(fetch_report_rows),
                "total_units": sum(row["units"] for row in fetch_report_rows),
            }

    return jsonify({"job_id": job_id, "status_url": f"/reports/{job_id}"}), 202


@app.get("/reports/<job_id>")
def get_report(job_id):
    row = read_job(job_id)
    if row is None:
        abort(404)

    response = {"job_id": row["job_id"], "status": row["status"]}
    if row["data_json"] is not None:
        response["report"] = json.loads(row["data_json"])
    if row["error"] is not None:
        response["error"] = row["error"]
    return jsonify(response)
```

The important boundary is process memory. The callback opens its own database connection because it runs in the forked process. The later `GET /reports/<job_id>` route runs in the Flask server process and reads the stored row instead of trying to communicate with the detached child directly.
