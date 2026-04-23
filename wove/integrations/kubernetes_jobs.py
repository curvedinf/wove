from typing import Any, Dict

from ..remote import payload_to_b64
from .base import RemoteTaskAdapter, maybe_await


class KubernetesJobsAdapter(RemoteTaskAdapter):
    required_modules = ("kubernetes",)
    install_hint = "kubernetes"

    async def start(self) -> None:
        load_config = self.config.get("load_config", True)
        if load_config:
            from kubernetes import config as kube_config

            loader = kube_config.load_incluster_config if self.config.get("in_cluster") else kube_config.load_kube_config
            try:
                loader(**dict(self.config.get("load_config_options") or {}))
            except TypeError:
                loader()

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        job_factory = self.config.get("job_factory")
        if job_factory is not None:
            job = await maybe_await(job_factory(payload, frame, self.config))
        else:
            job = self._default_job(payload, frame)

        namespace = self.config.get("namespace", "default")
        api = self.config.get("batch_api")
        if api is None:
            from kubernetes import client

            api = client.BatchV1Api()
        return await maybe_await(api.create_namespaced_job(namespace=namespace, body=job))

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del submission, frame
        namespace = self.config.get("namespace", "default")
        api = self.config.get("batch_api")
        if api is None:
            from kubernetes import client

            api = client.BatchV1Api()
        await maybe_await(api.delete_namespaced_job(name=self._job_name(run_id), namespace=namespace))

    def _job_name(self, run_id: str) -> str:
        safe_id = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in run_id.lower())
        return f"{self.config.get('job_name_prefix', 'wove')}-{safe_id}"[:63].rstrip("-")

    def _default_job(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        image = self.config.get("image")
        if not image:
            raise TypeError("kubernetes_jobs executor_config requires `image` or `job_factory`.")

        from kubernetes import client

        name = self._job_name(frame["run_id"])
        env = [client.V1EnvVar(name="WOVE_REMOTE_PAYLOAD", value=payload_to_b64(payload))]
        container = client.V1Container(
            name="wove",
            image=image,
            command=self.config.get("command") or ["python", "-m", "wove.remote_worker"],
            env=env,
        )
        spec = client.V1PodSpec(restart_policy="Never", containers=[container])
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": "wove", "wove-run-id": frame["run_id"]}),
            spec=spec,
        )
        job_spec = client.V1JobSpec(template=template, backoff_limit=self.config.get("backoff_limit", 0))
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=name, labels={"app": "wove"}),
            spec=job_spec,
        )
