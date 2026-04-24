import subprocess
from typing import Any, Dict

from ..backend import payload_to_b64
from .base import BackendAdapter, maybe_await


class SlurmAdapter(BackendAdapter):
    required_modules = ("pyslurm",)
    install_hint = "pyslurm"

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        submit = self.config.get("submit")
        if submit is not None:
            return await maybe_await(submit(payload, frame, self.config))

        command = self.config.get("command") or "python -m wove.backend_worker"
        payload_b64 = payload_to_b64(payload)
        wrap = f"WOVE_BACKEND_PAYLOAD='{payload_b64}' {command}"
        args = list(self.config.get("sbatch") or ["sbatch", "--parsable"])
        args.extend(
            [
                "--job-name",
                self.config.get("job_name_prefix", "wove") + "-" + frame["run_id"],
                "--wrap",
                wrap,
            ]
        )
        completed = subprocess.run(args, check=True, capture_output=True, text=True)
        return completed.stdout.strip()

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        job_id = str(submission).strip()
        if not job_id:
            return
        scancel = list(self.config.get("scancel") or ["scancel"])
        subprocess.run(scancel + [job_id], check=False)
