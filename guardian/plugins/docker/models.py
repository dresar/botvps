"""Models untuk plugin docker."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContainerInfo:
    """Informasi kontainer Docker."""

    container_id: str
    name: str
    image: str
    status: str
    state: str
    created_at: datetime | None
    ports: str
    cpu_percent: float | None
    memory_bytes: int | None
    memory_limit_bytes: int | None


@dataclass
class ImageInfo:
    """Informasi Docker image."""

    image_id: str
    repo_tags: list[str]
    size_bytes: int
    created_at: datetime | None


@dataclass
class ContainerStats:
    """Statistik runtime kontainer."""

    container_id: str
    name: str
    cpu_percent: float
    memory_usage_bytes: int
    memory_limit_bytes: int
    memory_percent: float
    net_input_bytes: int
    net_output_bytes: int
