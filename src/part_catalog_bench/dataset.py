from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .models import Exercise
from .util import sha256_file, sha256_text, write_json

SNAPSHOT_FILENAME = "dataset_snapshot.json"


def _exercise_payload(exercises: list[Exercise]) -> list[dict[str, Any]]:
    """Return the stable, complete exercise representation used for scoring."""
    return [
        exercise.model_dump(mode="json", exclude_none=False)
        for exercise in sorted(exercises, key=lambda item: item.id)
    ]


def exercise_fingerprint(exercises: list[Exercise]) -> str:
    canonical = json.dumps(
        _exercise_payload(exercises),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256_text(canonical)


def _source_file_label(path: Path, exercises_path: Path) -> str:
    if exercises_path.is_file():
        return path.name
    try:
        return path.resolve().relative_to(exercises_path.resolve()).as_posix()
    except ValueError:
        return path.name


def build_dataset_snapshot(
    selected: list[tuple[Path, Exercise]], exercises_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    exercises = [exercise for _, exercise in selected]
    source_files = []
    for path, exercise in sorted(selected, key=lambda item: item[1].id):
        source_files.append(
            {
                "exercise_id": exercise.id,
                "path": _source_file_label(path, exercises_path),
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )
    snapshot = {
        "schema_version": 1,
        "exercises": _exercise_payload(exercises),
        "source_files": source_files,
    }
    fingerprint = exercise_fingerprint(exercises)
    metadata = {
        "snapshot_file": SNAPSHOT_FILENAME,
        "sha256": fingerprint,
        "exercise_count": len(exercises),
        "question_count": sum(len(exercise.questions) for exercise in exercises),
        "source_files": source_files,
    }
    return snapshot, metadata


def write_dataset_snapshot(
    run_dir: Path, selected: list[tuple[Path, Exercise]], exercises_path: Path
) -> dict[str, Any]:
    snapshot, metadata = build_dataset_snapshot(selected, exercises_path)
    write_json(run_dir / SNAPSHOT_FILENAME, snapshot)
    return metadata


def load_dataset_snapshot(path: Path, expected_sha256: str | None = None) -> list[Exercise]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("exercises"), list):
        raise ValueError(f"invalid dataset snapshot: {path}")
    exercises = [Exercise.model_validate(item) for item in raw["exercises"]]
    actual = exercise_fingerprint(exercises)
    if expected_sha256 and actual != expected_sha256:
        raise ValueError(
            "dataset snapshot fingerprint does not match run.json: "
            f"expected {expected_sha256}, found {actual}"
        )
    return exercises


def git_provenance(root: Path) -> dict[str, Any] | None:
    """Return supplementary code provenance without making Git a runtime requirement."""
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return {"git_commit": commit, "git_dirty": bool(status.strip())}
