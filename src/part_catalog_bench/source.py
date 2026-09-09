from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ExpectedSource(BaseModel):
    pages: int | None = None
    title_contains: str | None = None


class CatalogRootRule(BaseModel):
    title_contains: str


class LogicalPageRule(BaseModel):
    catalog: str
    bookmark_regex: str
    format: str

    def match(self, title: str) -> re.Match[str] | None:
        return re.search(self.bookmark_regex, title, flags=re.IGNORECASE)


class SourceDefinition(BaseModel):
    id: str
    title: str
    publisher: str | None = None
    product_id: str | None = None
    acquisition_url: str | None = None
    expected: ExpectedSource = Field(default_factory=ExpectedSource)
    catalog_roots: dict[str, CatalogRootRule]
    logical_page_rules: list[LogicalPageRule] = Field(default_factory=list)
    guide: str


def repository_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def load_source_definition(source_id: str, sources_dir: Path | None = None) -> SourceDefinition:
    directory = sources_dir or repository_root() / "sources"
    path = directory / f"{source_id}.yaml"
    if not path.exists():
        available = ", ".join(item.stem for item in sorted(directory.glob("*.yaml")))
        raise FileNotFoundError(f"unknown source {source_id!r}; available: {available or 'none'}")
    return SourceDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def source_guide_path(definition: SourceDefinition) -> Path:
    path = Path(definition.guide)
    return path if path.is_absolute() else repository_root() / path
