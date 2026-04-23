from typing import Any, Dict

from ..remote import payload_to_b64
from .base import RemoteTaskAdapter, maybe_await


class AWSBatchAdapter(RemoteTaskAdapter):
    required_modules = ("boto3",)
    install_hint = "boto3"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client: Any = None

    async def start(self) -> None:
        self._client = self.config.get("client")
        if self._client is not None:
            return

        import boto3

        self._client = boto3.client("batch", **dict(self.config.get("client_options") or {}))

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        job_queue = self.config.get("job_queue")
        job_definition = self.config.get("job_definition")
        if not job_queue or not job_definition:
            raise TypeError("aws_batch executor_config requires `job_queue` and `job_definition`.")

        overrides = dict(self.config.get("container_overrides") or {})
        env = list(overrides.get("environment") or [])
        env.append({"name": "WOVE_REMOTE_PAYLOAD", "value": payload_to_b64(payload)})
        overrides["environment"] = env
        if "command" not in overrides and self.config.get("command"):
            overrides["command"] = self.config["command"]

        params = dict(self.config.get("submit_job_options") or {})
        params.update(
            {
                "jobName": self.config.get("job_name_prefix", "wove") + "-" + frame["run_id"],
                "jobQueue": job_queue,
                "jobDefinition": job_definition,
                "containerOverrides": overrides,
            }
        )
        return await maybe_await(self._client.submit_job(**params))

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        job_id = submission.get("jobId") if isinstance(submission, dict) else None
        if job_id:
            await maybe_await(self._client.cancel_job(jobId=job_id, reason="Cancelled by Wove."))
