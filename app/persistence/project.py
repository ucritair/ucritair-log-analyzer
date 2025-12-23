from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import orjson

from app.core.config import ProcessingConfig, FilterConfig
from app.data.dataset import Dataset


@dataclass
class Project:
    dataset_paths: list[str]
    processing_config: ProcessingConfig
    filter_config: FilterConfig
    active_standard_pack: str
    active_dataset_index: int = 0


def save_project(project: Project, path: Path) -> None:
    payload = {
        "datasets": project.dataset_paths,
        "processing_config": asdict(project.processing_config),
        "filter_config": asdict(project.filter_config),
        "active_standard_pack": project.active_standard_pack,
        "active_dataset_index": project.active_dataset_index,
    }
    path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))


def load_project(path: Path) -> Project:
    data = orjson.loads(path.read_bytes())
    return Project(
        dataset_paths=data.get("datasets", []),
        processing_config=ProcessingConfig(**data.get("processing_config", {})),
        filter_config=FilterConfig(**data.get("filter_config", {})),
        active_standard_pack=data.get("active_standard_pack", "us_epa_legacy"),
        active_dataset_index=int(data.get("active_dataset_index", 0)),
    )
