import sys
import types

import pytest

from wove.integrations import (
    get_backend_adapter_class,
    get_backend_adapter_dependencies,
    get_backend_adapter_install_hints,
)
from wove.integrations.arq import ARQAdapter
from wove.integrations.aws_batch import AWSBatchAdapter
from wove.integrations.base import BackendAdapter
from wove.integrations.celery import CeleryAdapter
from wove.integrations.dask import DaskAdapter
from wove.integrations.kubernetes_jobs import KubernetesJobsAdapter
from wove.integrations.ray import RayAdapter
from wove.integrations.rq import RQAdapter
from wove.integrations.slurm import SlurmAdapter
from wove.integrations.taskiq import TaskiqAdapter
from wove.integrations.temporal import TemporalAdapter


def make_adapter(adapter_class, name, config):
    return adapter_class(name=name, config=config, callback_url="http://callback", run_config={})


def make_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


@pytest.mark.asyncio
async def test_adapter_registry_and_base_contract():
    assert get_backend_adapter_class("celery") is CeleryAdapter
    assert get_backend_adapter_dependencies()["celery"] == ("celery",)
    assert get_backend_adapter_install_hints()["dask"] == "dask[distributed]"

    with pytest.raises(ValueError, match="Unknown executor"):
        get_backend_adapter_class("missing")

    adapter = make_adapter(BackendAdapter, "base", {})
    assert adapter.missing_dependencies() == ()
    await adapter.start()
    await adapter.cancel("run", None, {})
    await adapter.close()

    with pytest.raises(NotImplementedError):
        await adapter.submit({}, {})


@pytest.mark.asyncio
async def test_celery_adapter_submits_payload_to_named_task():
    class App:
        def __init__(self):
            self.calls = []

        def send_task(self, name, args, **kwargs):
            self.calls.append((name, args, kwargs))
            return "submission"

    app = App()
    adapter = make_adapter(CeleryAdapter, "celery", {"app": app, "queue": "wove"})
    await adapter.start()
    result = await adapter.submit({"payload": True}, {"run_id": "r1"})

    assert result == "submission"
    assert app.calls == [("wove.run_backend_payload", [{"payload": True}], {"queue": "wove"})]


@pytest.mark.asyncio
async def test_celery_adapter_can_create_app(monkeypatch):
    class CreatedApp:
        def __init__(self, name, broker=None, backend=None):
            self.name = name
            self.broker = broker
            self.backend = backend
            self.calls = []

        def send_task(self, name, args, **kwargs):
            self.calls.append((name, args, kwargs))
            return "created-submission"

    celery_module = make_module("celery", Celery=CreatedApp)
    monkeypatch.setitem(sys.modules, "celery", celery_module)

    adapter = make_adapter(
        CeleryAdapter,
        "celery",
        {"app_name": "created", "broker_url": "redis://broker", "backend_url": "redis://backend"},
    )
    await adapter.start()
    result = await adapter.submit({"payload": True}, {"run_id": "r1"})

    assert result == "created-submission"
    assert adapter._app.name == "created"
    assert adapter._app.broker == "redis://broker"
    assert adapter._app.backend == "redis://backend"


@pytest.mark.asyncio
async def test_celery_adapter_requires_app_or_broker_url():
    adapter = make_adapter(CeleryAdapter, "celery", {})
    with pytest.raises(TypeError, match="requires `app` or `broker_url`"):
        await adapter.start()


@pytest.mark.asyncio
async def test_rq_adapter_enqueues_worker_function():
    class Queue:
        def __init__(self):
            self.calls = []

        def enqueue(self, func, payload, **kwargs):
            self.calls.append((func.__name__, payload, kwargs))
            return "job"

    queue = Queue()
    adapter = make_adapter(RQAdapter, "rq", {"queue": queue})
    await adapter.start()
    result = await adapter.submit({"payload": True}, {"run_id": "r2"})

    assert result == "job"
    assert queue.calls == [("run", {"payload": True}, {"job_id": "r2"})]


@pytest.mark.asyncio
async def test_rq_adapter_can_create_queue_and_cancel(monkeypatch):
    class Redis:
        @classmethod
        def from_url(cls, url):
            return ("redis", url)

    class Queue:
        def __init__(self, name, connection=None):
            self.name = name
            self.connection = connection

    class Job:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    monkeypatch.setitem(sys.modules, "redis", make_module("redis", Redis=Redis))
    monkeypatch.setitem(sys.modules, "rq", make_module("rq", Queue=Queue))

    adapter = make_adapter(RQAdapter, "rq", {"redis_url": "redis://redis", "queue_name": "jobs"})
    await adapter.start()
    job = Job()
    await adapter.cancel("r2", job, {})

    assert adapter._queue.name == "jobs"
    assert adapter._queue.connection == ("redis", "redis://redis")
    assert job.cancelled is True


@pytest.mark.asyncio
async def test_rq_adapter_requires_queue_or_redis_url():
    adapter = make_adapter(RQAdapter, "rq", {})
    with pytest.raises(TypeError, match="requires `queue` or `redis_url`"):
        await adapter.start()


@pytest.mark.asyncio
async def test_ray_adapter_submits_remote_function(monkeypatch):
    class RemoteFunction:
        def __init__(self, func):
            self.func = func

        def remote(self, payload):
            return ("ref", self.func.__name__, payload)

    class Ray:
        def __init__(self):
            self.init_kwargs = None
            self.cancelled = None

        def is_initialized(self):
            return False

        def init(self, **kwargs):
            self.init_kwargs = kwargs

        def remote(self, *args, **kwargs):
            if args:
                return RemoteFunction(args[0])

            def wrap(func):
                return RemoteFunction(func)

            return wrap

        def cancel(self, submission, force=False):
            self.cancelled = (submission, force)

    ray = Ray()
    monkeypatch.setitem(sys.modules, "ray", ray)
    adapter = make_adapter(RayAdapter, "ray", {"address": "ray://cluster", "force_cancel": True})
    await adapter.start()
    submission = await adapter.submit({"payload": True}, {"run_id": "r3"})
    await adapter.cancel("r3", submission, {})

    assert ray.init_kwargs["address"] == "ray://cluster"
    assert submission == ("ref", "run", {"payload": True})
    assert ray.cancelled == (submission, True)


@pytest.mark.asyncio
async def test_dask_adapter_submits_to_client_and_closes():
    class Client:
        def __init__(self):
            self.submitted = None
            self.cancelled = None
            self.closed = False

        def submit(self, func, payload, **kwargs):
            self.submitted = (func.__name__, payload, kwargs)
            return "future"

        def cancel(self, future):
            self.cancelled = future

        def close(self):
            self.closed = True

    client = Client()
    adapter = make_adapter(DaskAdapter, "dask", {"client": client})
    await adapter.start()
    future = await adapter.submit({"payload": True}, {"run_id": "r4"})
    await adapter.cancel("r4", future, {})
    await adapter.close()

    assert client.submitted == ("run", {"payload": True}, {"key": "r4"})
    assert client.cancelled == "future"
    assert client.closed is False


@pytest.mark.asyncio
async def test_dask_adapter_can_create_and_close_client(monkeypatch):
    class Client:
        def __init__(self, address, **kwargs):
            self.address = address
            self.kwargs = kwargs
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setitem(sys.modules, "distributed", make_module("distributed", Client=Client))
    adapter = make_adapter(DaskAdapter, "dask", {"address": "tcp://scheduler", "client_options": {"timeout": 3}})
    await adapter.start()
    await adapter.close()

    assert adapter._client.address == "tcp://scheduler"
    assert adapter._client.kwargs == {"timeout": 3}
    assert adapter._client.closed is True


@pytest.mark.asyncio
async def test_taskiq_and_arq_adapters_enqueue_payloads():
    class Task:
        def __init__(self):
            self.payloads = []

        async def kiq(self, payload):
            self.payloads.append(payload)
            return "message"

    task = Task()
    taskiq = make_adapter(TaskiqAdapter, "taskiq", {"task": task})
    await taskiq.start()
    assert await taskiq.submit({"payload": "taskiq"}, {"run_id": "r5"}) == "message"
    assert task.payloads == [{"payload": "taskiq"}]

    class Pool:
        def __init__(self):
            self.calls = []
            self.closed = False

        async def enqueue_job(self, function_name, payload, **kwargs):
            self.calls.append((function_name, payload, kwargs))
            return "job"

        def close(self):
            self.closed = True

    pool = Pool()
    arq = make_adapter(ARQAdapter, "arq", {"pool": pool, "queue_name": "wove"})
    await arq.start()
    assert await arq.submit({"payload": "arq"}, {"run_id": "r6"}) == "job"
    await arq.close()
    assert pool.calls == [("wove_run_backend_payload", {"payload": "arq"}, {"_job_id": "r6", "_queue_name": "wove"})]
    assert pool.closed is False


@pytest.mark.asyncio
async def test_taskiq_finds_task_from_broker_and_rejects_missing_task():
    class Broker:
        def __init__(self):
            self.names = []

        def find_task(self, name):
            self.names.append(name)
            return lambda payload: ("called", payload)

    broker = Broker()
    adapter = make_adapter(TaskiqAdapter, "taskiq", {"broker": broker, "task_name": "task.name"})
    await adapter.start()
    assert await adapter.submit({"payload": True}, {"run_id": "r"}) == ("called", {"payload": True})
    assert broker.names == ["task.name"]

    with pytest.raises(TypeError, match="requires `task` or a `broker`"):
        await make_adapter(TaskiqAdapter, "taskiq", {}).start()


@pytest.mark.asyncio
async def test_arq_adapter_can_create_pool_and_rejects_missing_pool(monkeypatch):
    class Pool:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    created = {}

    async def create_pool(settings):
        created["settings"] = settings
        return Pool()

    monkeypatch.setitem(sys.modules, "arq", make_module("arq"))
    monkeypatch.setitem(sys.modules, "arq.connections", make_module("arq.connections", create_pool=create_pool))

    adapter = make_adapter(ARQAdapter, "arq", {"redis_settings": "settings"})
    await adapter.start()
    await adapter.close()
    assert created["settings"] == "settings"
    assert adapter._pool.closed is True

    with pytest.raises(TypeError, match="requires `pool` or `redis_settings`"):
        await make_adapter(ARQAdapter, "arq", {}).start()


@pytest.mark.asyncio
async def test_temporal_adapter_starts_workflow_and_cancels_handle():
    class Handle:
        def __init__(self):
            self.cancelled = False

        async def cancel(self):
            self.cancelled = True

    class Client:
        def __init__(self):
            self.calls = []
            self.handle = Handle()

        async def start_workflow(self, workflow, payload, **kwargs):
            self.calls.append((workflow, payload, kwargs))
            return self.handle

    client = Client()
    adapter = make_adapter(
        TemporalAdapter,
        "temporal",
        {"client": client, "workflow": "WoveWorkflow", "task_queue": "wove"},
    )
    await adapter.start()
    handle = await adapter.submit({"payload": True}, {"run_id": "r7"})
    await adapter.cancel("r7", handle, {})

    assert client.calls == [
        (
            "WoveWorkflow",
            {"payload": True},
            {"id": "wove-r7", "task_queue": "wove"},
        )
    ]
    assert client.handle.cancelled is True


@pytest.mark.asyncio
async def test_temporal_adapter_can_connect_client_and_validates_config(monkeypatch):
    class Client:
        @classmethod
        async def connect(cls, target_host, **kwargs):
            instance = cls()
            instance.target_host = target_host
            instance.kwargs = kwargs
            return instance

    monkeypatch.setitem(sys.modules, "temporalio", make_module("temporalio"))
    monkeypatch.setitem(sys.modules, "temporalio.client", make_module("temporalio.client", Client=Client))

    adapter = make_adapter(TemporalAdapter, "temporal", {"target_host": "temporal:7233", "connect_options": {"namespace": "default"}})
    await adapter.start()
    assert adapter._client.target_host == "temporal:7233"
    assert adapter._client.kwargs == {"namespace": "default"}

    with pytest.raises(TypeError, match="requires `client` or `target_host`"):
        await make_adapter(TemporalAdapter, "temporal", {}).start()

    with pytest.raises(TypeError, match="requires `workflow` and `task_queue`"):
        await adapter.submit({}, {"run_id": "r"})


@pytest.mark.asyncio
async def test_kubernetes_and_aws_batch_adapters_submit_payload_env():
    class BatchApi:
        def __init__(self):
            self.created = None
            self.deleted = None

        def create_namespaced_job(self, namespace, body):
            self.created = (namespace, body)
            return "job"

        def delete_namespaced_job(self, name, namespace):
            self.deleted = (name, namespace)

    api = BatchApi()

    async def job_factory(payload, frame, config):
        return {"payload": payload, "run": frame["run_id"], "namespace": config["namespace"]}

    kubernetes = make_adapter(
        KubernetesJobsAdapter,
        "kubernetes_jobs",
        {"load_config": False, "namespace": "jobs", "batch_api": api, "job_factory": job_factory},
    )
    await kubernetes.start()
    assert await kubernetes.submit({"payload": "k8s"}, {"run_id": "r8"}) == "job"
    await kubernetes.cancel("r8", None, {})
    assert api.created == ("jobs", {"payload": {"payload": "k8s"}, "run": "r8", "namespace": "jobs"})
    assert api.deleted == ("wove-r8", "jobs")

    class BatchClient:
        def __init__(self):
            self.submitted = None
            self.cancelled = None

        def submit_job(self, **kwargs):
            self.submitted = kwargs
            return {"jobId": "aws-job"}

        def cancel_job(self, **kwargs):
            self.cancelled = kwargs

    client = BatchClient()
    aws = make_adapter(
        AWSBatchAdapter,
        "aws_batch",
        {"client": client, "job_queue": "queue", "job_definition": "definition"},
    )
    await aws.start()
    submission = await aws.submit({"payload": "aws"}, {"run_id": "r9"})
    await aws.cancel("r9", submission, {})

    assert client.submitted["jobQueue"] == "queue"
    assert client.submitted["jobDefinition"] == "definition"
    environment = client.submitted["containerOverrides"]["environment"]
    assert environment[0]["name"] == "WOVE_BACKEND_PAYLOAD"
    assert client.cancelled == {"jobId": "aws-job", "reason": "Cancelled by Wove."}


@pytest.mark.asyncio
async def test_kubernetes_adapter_default_job_and_config_loading(monkeypatch):
    class KubeConfig:
        def __init__(self):
            self.loaded = None

        def load_kube_config(self, **kwargs):
            self.loaded = ("kube", kwargs)

        def load_incluster_config(self, **kwargs):
            self.loaded = ("cluster", kwargs)

    class Obj:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class BatchApi:
        def __init__(self):
            self.created = None
            self.deleted = None

        def create_namespaced_job(self, namespace, body):
            self.created = (namespace, body)
            return "created"

        def delete_namespaced_job(self, name, namespace):
            self.deleted = (name, namespace)

    api = BatchApi()
    kube_config = KubeConfig()
    client_module = make_module(
        "kubernetes.client",
        BatchV1Api=lambda: api,
        V1EnvVar=Obj,
        V1Container=Obj,
        V1PodSpec=Obj,
        V1PodTemplateSpec=Obj,
        V1ObjectMeta=Obj,
        V1JobSpec=Obj,
        V1Job=Obj,
    )
    monkeypatch.setitem(sys.modules, "kubernetes", make_module("kubernetes", config=kube_config, client=client_module))
    monkeypatch.setitem(sys.modules, "kubernetes.client", client_module)

    adapter = make_adapter(
        KubernetesJobsAdapter,
        "kubernetes_jobs",
        {"namespace": "jobs", "image": "image", "load_config_options": {"context": "dev"}},
    )
    await adapter.start()
    result = await adapter.submit({"payload": "k8s"}, {"run_id": "Run_8"})
    await adapter.cancel("Run_8", None, {})

    assert kube_config.loaded == ("kube", {"context": "dev"})
    assert result == "created"
    assert api.created[0] == "jobs"
    assert api.created[1].kwargs["metadata"].kwargs["name"] == "wove-run-8"
    assert api.deleted == ("wove-run-8", "jobs")

    with pytest.raises(TypeError, match="requires `image` or `job_factory`"):
        make_adapter(KubernetesJobsAdapter, "kubernetes_jobs", {"load_config": False})._default_job({}, {"run_id": "r"})


@pytest.mark.asyncio
async def test_kubernetes_adapter_incluster_loader_fallback(monkeypatch):
    class KubeConfig:
        def __init__(self):
            self.loaded = False

        def load_incluster_config(self, **kwargs):
            if kwargs:
                raise TypeError("no kwargs")
            self.loaded = True

    kube_config = KubeConfig()
    monkeypatch.setitem(sys.modules, "kubernetes", make_module("kubernetes", config=kube_config))

    adapter = make_adapter(
        KubernetesJobsAdapter,
        "kubernetes_jobs",
        {"in_cluster": True, "load_config_options": {"ignored": True}},
    )
    await adapter.start()
    assert kube_config.loaded is True


@pytest.mark.asyncio
async def test_aws_batch_adapter_can_create_client_and_cancel_without_job_id(monkeypatch):
    class Boto3:
        def client(self, name, **kwargs):
            client = types.SimpleNamespace(name=name, kwargs=kwargs)

            def submit_job(**_submit_kwargs):
                return {}

            client.submit_job = submit_job
            client.cancel_job = lambda **_kwargs: None
            return client

    monkeypatch.setitem(sys.modules, "boto3", Boto3())
    adapter = make_adapter(AWSBatchAdapter, "aws_batch", {"client_options": {"region_name": "us-east-1"}})
    await adapter.start()
    assert adapter._client.name == "batch"
    assert adapter._client.kwargs == {"region_name": "us-east-1"}

    with pytest.raises(TypeError, match="requires `job_queue` and `job_definition`"):
        await adapter.submit({}, {"run_id": "r"})

    await adapter.cancel("r", {}, {})


@pytest.mark.asyncio
async def test_slurm_adapter_accepts_custom_submit_callable():
    async def submit(payload, frame, config):
        return (payload, frame["run_id"], config["partition"])

    adapter = make_adapter(SlurmAdapter, "slurm", {"submit": submit, "partition": "short"})
    result = await adapter.submit({"payload": "slurm"}, {"run_id": "r10"})

    assert result == ({"payload": "slurm"}, "r10", "short")


@pytest.mark.asyncio
async def test_slurm_adapter_default_submit_and_cancel(monkeypatch):
    calls = []

    class Completed:
        stdout = "12345\n"

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return Completed()

    monkeypatch.setattr("wove.integrations.slurm.subprocess.run", run)
    adapter = make_adapter(SlurmAdapter, "slurm", {"job_name_prefix": "job", "scancel": ["cancel"]})
    result = await adapter.submit({"payload": "slurm"}, {"run_id": "r11"})
    await adapter.cancel("r11", result, {})
    await adapter.cancel("r11", "", {})

    assert result == "12345"
    assert calls[0][0][0:2] == ["sbatch", "--parsable"]
    assert calls[0][1] == {"check": True, "capture_output": True, "text": True}
    assert calls[1] == (["cancel", "12345"], {"check": False})
