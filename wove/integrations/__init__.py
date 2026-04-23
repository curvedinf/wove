from typing import Dict, Type

from .arq import ARQAdapter
from .aws_batch import AWSBatchAdapter
from .base import RemoteTaskAdapter
from .celery import CeleryAdapter
from .dask import DaskAdapter
from .kubernetes_jobs import KubernetesJobsAdapter
from .ray import RayAdapter
from .rq import RQAdapter
from .slurm import SlurmAdapter
from .taskiq import TaskiqAdapter
from .temporal import TemporalAdapter


ADAPTERS: Dict[str, Type[RemoteTaskAdapter]] = {
    "celery": CeleryAdapter,
    "temporal": TemporalAdapter,
    "ray": RayAdapter,
    "rq": RQAdapter,
    "taskiq": TaskiqAdapter,
    "arq": ARQAdapter,
    "dask": DaskAdapter,
    "kubernetes_jobs": KubernetesJobsAdapter,
    "aws_batch": AWSBatchAdapter,
    "slurm": SlurmAdapter,
}


def get_adapter_class(name: str) -> Type[RemoteTaskAdapter]:
    try:
        return ADAPTERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown executor '{name}'.") from exc


def get_adapter_dependencies() -> Dict[str, tuple]:
    return {name: adapter.required_modules for name, adapter in ADAPTERS.items()}


def get_adapter_install_hints() -> Dict[str, str]:
    return {name: adapter.install_hint or " ".join(adapter.required_modules) for name, adapter in ADAPTERS.items()}
