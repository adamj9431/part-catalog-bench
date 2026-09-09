from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .assets import render_catalog_ref
from .catalog import load_manifest
from .models import AnswerSpec, Exercise, load_exercises
from .providers import build_completion_payload, create_provider, incomplete_response_message
from .rubric import grade_rubric_answer, rubric_semantic_grade_required
from .runner import prepare_question_messages, run_benchmark
from .scoring import score_answer
from .source import repository_root
from .util import read_jsonl, write_json


class SaveRequest(BaseModel):
    exercise: dict[str, Any]
    original_id: str | None = None


class TestRequest(BaseModel):
    exercise: dict[str, Any]
    question_id: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = Field(default=8192, ge=1, le=128000)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = None
    grader_provider: str | None = None
    grader_model: str | None = None
    grader_max_tokens: int = Field(default=1024, ge=128, le=128000)
    grader_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = None


class RubricTestRequest(BaseModel):
    question_prompt: str = Field(min_length=3)
    answer: dict[str, Any]
    response: str
    provider: str
    model: str
    max_tokens: int = Field(default=1024, ge=128, le=128000)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = None


def _exercise_refs(exercise: Exercise) -> list[str]:
    return [*exercise.context.catalog_refs, *[page.ref for page in exercise.context.pages]]


def _exercise_index(exercises_dir: Path) -> list[dict[str, Any]]:
    if not exercises_dir.exists():
        return []
    rows = []
    for path, exercise in load_exercises(exercises_dir):
        if ".trash" in path.parts:
            continue
        rows.append(
            {
                "id": exercise.id,
                "title": exercise.title,
                "status": exercise.status.value,
                "questions": len(exercise.questions),
                "refs": _exercise_refs(exercise),
                "path": str(path),
            }
        )
    return sorted(rows, key=lambda row: row["id"])


def _find_exercise(exercises_dir: Path, exercise_id: str) -> tuple[Path, Exercise]:
    for path, exercise in load_exercises(exercises_dir):
        if ".trash" not in path.parts and exercise.id == exercise_id:
            return path, exercise
    raise FileNotFoundError(exercise_id)


def _development_record(
    run_dir: Path,
    config: dict[str, Any],
    prediction: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    score_errors = score.get("errors") or []
    error = prediction.get("error") or ("; ".join(score_errors) if score_errors else None)
    passed = not error and score.get("strict") == 1.0
    return {
        "run_id": config.get("run_id", run_dir.name),
        "created_at": config.get("created_at"),
        "exercise_id": prediction.get("exercise_id"),
        "question_id": prediction.get("question_id"),
        "provider": prediction.get("provider") or config.get("provider"),
        "requested_model": prediction.get("requested_model") or config.get("model"),
        "response_model": prediction.get("response_model"),
        "raw_response": prediction.get("raw_response"),
        "answer": prediction.get("answer"),
        "error": error,
        "latency_seconds": prediction.get("latency_seconds"),
        "usage": prediction.get("usage") or {},
        "max_tokens": config.get("max_tokens"),
        "reasoning_effort": config.get("reasoning_effort"),
        "grader": config.get("grader"),
        "grading": prediction.get("grading"),
        "passed": passed,
        "outcome": "error" if error else "pass" if passed else "fail",
        "score": score,
    }


def _development_history(
    development_root: Path,
    exercise_id: str,
    question_id: str,
    answer_spec: AnswerSpec,
) -> list[dict[str, Any]]:
    records = []
    if not development_root.exists():
        return records
    for run_dir in development_root.iterdir():
        if not run_dir.is_dir():
            continue
        config_path = run_dir / "run.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        prediction = next(
            (
                row
                for row in read_jsonl(run_dir / "predictions.jsonl")
                if row.get("exercise_id") == exercise_id and row.get("question_id") == question_id
            ),
            None,
        )
        if prediction is None:
            continue
        incomplete_error = incomplete_response_message(
            prediction.get("provider_response") or {}, config.get("max_tokens")
        )
        if incomplete_error and not prediction.get("error"):
            prediction = {
                **prediction,
                "answer": None,
                "raw_response": None,
                "error": f"IncompleteResponseError: {incomplete_error}",
            }
        saved_record = run_dir / "development.json"
        if saved_record.exists() and not incomplete_error:
            try:
                record = json.loads(saved_record.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                record = None
            rubric_record_current = answer_spec.grading is None or (
                record is not None and record.get("score", {}).get("grading_method") == "rubric"
            )
            if (
                record
                and record.get("exercise_id") == exercise_id
                and record.get("question_id") == question_id
                and rubric_record_current
            ):
                records.append(record)
                continue
        score = (
            {"score": 0.0, "strict": 0.0, "reason": prediction.get("error")}
            if prediction.get("error")
            else score_answer(prediction.get("answer"), answer_spec, prediction.get("grading"))
        )
        records.append(_development_record(run_dir, config, prediction, score))
    return sorted(
        records,
        key=lambda record: (record.get("created_at") or "", record.get("run_id") or ""),
        reverse=True,
    )


def _recent_development_models(
    development_root: Path, provider: str, limit: int = 5
) -> list[dict[str, str]]:
    """Return the most recently used distinct candidate models for one provider."""
    records = []
    if not development_root.exists():
        return records
    for run_dir in development_root.iterdir():
        if not run_dir.is_dir():
            continue
        try:
            config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        model = config.get("model")
        if config.get("provider") != provider or not model:
            continue
        records.append(
            {
                "id": str(model),
                "used_at": str(config.get("created_at") or ""),
                "run_id": str(config.get("run_id") or run_dir.name),
            }
        )
    records.sort(key=lambda row: (row["used_at"], row["run_id"]), reverse=True)
    recent = []
    seen = set()
    for record in records:
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        recent.append({"id": record["id"], "used_at": record["used_at"]})
        if len(recent) == limit:
            break
    return recent


def _catalog_sections(manifest: dict[str, Any], catalog: str) -> list[dict[str, Any]]:
    """Build navigable bookmark ranges, including ranges for parent bookmarks."""
    nodes: dict[tuple[str, ...], dict[str, Any]] = {}
    root_title = manifest.get("catalogs", {}).get(catalog, {}).get("root_title")
    for document in manifest.get("documents", []):
        if document.get("catalog") != catalog:
            continue
        bookmark_path = list(document.get("bookmark_path") or [document["title"]])
        if bookmark_path and bookmark_path[0] == root_title:
            bookmark_path = bookmark_path[1:]
        if not bookmark_path:
            bookmark_path = [document["title"]]
        for depth in range(1, len(bookmark_path) + 1):
            path = tuple(bookmark_path[:depth])
            node = nodes.setdefault(
                path,
                {
                    "title": path[-1],
                    "path": list(path),
                    "depth": depth,
                    "source_start_page": document["source_start_page"],
                    "source_end_page": document["source_end_page"],
                },
            )
            node["source_start_page"] = min(
                node["source_start_page"], document["source_start_page"]
            )
            node["source_end_page"] = max(node["source_end_page"], document["source_end_page"])
    ordered = sorted(
        nodes.values(),
        key=lambda node: (node["source_start_page"], node["depth"], node["path"]),
    )
    for index, node in enumerate(ordered, start=1):
        node["id"] = f"{catalog}-bookmark-{index:04d}"
        node["page_count"] = node["source_end_page"] - node["source_start_page"] + 1
    return ordered


def create_authoring_app(
    manifest_path: Path,
    exercises_dir: Path,
    development_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Part Catalog Bench Authoring Studio")
    html_path = Path(__file__).with_name("authoring.html")
    development_root = development_root or repository_root() / "results" / "development"

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return html_path.read_text(encoding="utf-8")

    @app.get("/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        manifest = load_manifest(manifest_path)
        logical_by_page: dict[tuple[str, int], str] = {}
        for ref, page in manifest.get("logical_pages", {}).items():
            logical_by_page.setdefault((page["catalog"], page["source_page"]), ref)
        ordered_refs: dict[str, list[str]] = {}
        for catalog, bounds in manifest["catalogs"].items():
            ordered_refs[catalog] = [
                logical_by_page.get((catalog, source_page), f"{catalog}@source:{source_page}")
                for source_page in range(bounds["source_start_page"], bounds["source_end_page"] + 1)
            ]
        return {
            "source": manifest["source"],
            "manifest": str(manifest_path),
            "catalog_bounds": manifest["catalogs"],
            "logical_refs": {
                "illustrations": ordered_refs["illustrations"],
                "text": ordered_refs["text"],
            },
            "sections": {
                "illustrations": _catalog_sections(manifest, "illustrations"),
                "text": _catalog_sections(manifest, "text"),
            },
            "exercises": _exercise_index(exercises_dir),
            "coordinate_system": "normalized_full_page_top_left",
        }

    @app.get("/api/page")
    def page(ref: str = Query(..., min_length=3), dpi: int = Query(180, ge=72, le=400)):
        try:
            path = render_catalog_ref(manifest_path, ref, dpi=dpi)
        except (KeyError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.get("/api/section-pdf")
    def section_pdf(ref: str = Query(..., min_length=3)):
        manifest = load_manifest(manifest_path)
        logical = manifest.get("logical_pages", {}).get(ref)
        if logical:
            relative = logical["document_path"]
        else:
            try:
                source_page = int(ref.rsplit(":", 1)[1])
            except (ValueError, IndexError) as exc:
                raise HTTPException(status_code=404, detail="catalog page not found") from exc
            document = next(
                (
                    item
                    for item in manifest["documents"]
                    if item["source_start_page"] <= source_page <= item["source_end_page"]
                ),
                None,
            )
            if document is None:
                raise HTTPException(status_code=404, detail="catalog section not found")
            relative = document["relative_path"]
        path = (manifest_path.parent / relative).resolve()
        if manifest_path.parent.resolve() not in path.parents or not path.exists():
            raise HTTPException(status_code=404, detail="catalog section file not found")
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    @app.get("/api/exercises/{exercise_id}")
    def get_exercise(exercise_id: str) -> dict[str, Any]:
        try:
            _, exercise = _find_exercise(exercises_dir, exercise_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="exercise not found") from exc
        return exercise.model_dump(mode="json")

    @app.post("/api/exercises")
    def save_exercise(request: SaveRequest) -> dict[str, Any]:
        try:
            exercise = Exercise.model_validate(request.exercise)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        exercises_dir.mkdir(parents=True, exist_ok=True)
        try:
            destination, _ = _find_exercise(exercises_dir, request.original_id or exercise.id)
        except FileNotFoundError:
            destination = exercises_dir / f"{exercise.id}.yaml"
        destination.write_text(
            yaml.safe_dump(
                exercise.model_dump(mode="json", exclude_none=True),
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        return {"saved": str(destination), "exercise": exercise.model_dump(mode="json")}

    @app.delete("/api/exercises/{exercise_id}")
    def archive_exercise(exercise_id: str) -> dict[str, str]:
        try:
            path, _ = _find_exercise(exercises_dir, exercise_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="exercise not found") from exc
        trash = exercises_dir / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        destination = trash / f"{path.stem}-{stamp}{path.suffix}"
        shutil.move(path, destination)
        return {"archived": str(destination), "recovery": "Move the file back from .trash."}

    @app.get("/api/development-history/{exercise_id}/{question_id}")
    def development_history(exercise_id: str, question_id: str) -> dict[str, Any]:
        try:
            _, exercise = _find_exercise(exercises_dir, exercise_id)
            question = next(item for item in exercise.questions if item.id == question_id)
        except (FileNotFoundError, StopIteration) as exc:
            raise HTTPException(status_code=404, detail="exercise or question not found") from exc
        return {
            "history": _development_history(
                development_root, exercise_id, question_id, question.answer
            )
        }

    @app.get("/api/models")
    def available_models(
        provider: str = Query(pattern="^(openrouter|databricks)$"),
    ) -> dict[str, Any]:
        try:
            models = create_provider(provider).list_models()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "provider": provider,
            "models": models,
            "recent_models": _recent_development_models(development_root, provider),
        }

    @app.post("/api/test-question")
    def test_question(request: TestRequest) -> dict[str, Any]:
        try:
            exercise = Exercise.model_validate(request.exercise)
            question = next(item for item in exercise.questions if item.id == request.question_id)
        except (Exception, StopIteration) as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid exercise/question: {exc}"
            ) from exc
        single = exercise.model_copy(update={"questions": [question], "status": "ready"})
        with tempfile.TemporaryDirectory(prefix="part-catalog-bench-author-") as temp_name:
            temporary = Path(temp_name)
            exercise_file = temporary / "exercise.yaml"
            exercise_file.write_text(
                yaml.safe_dump(single.model_dump(mode="json", exclude_none=True), sort_keys=False),
                encoding="utf-8",
            )
            try:
                run_dir = run_benchmark(
                    provider_name=request.provider,
                    model=request.model,
                    exercises_path=exercise_file,
                    manifest_path=manifest_path,
                    output_root=development_root,
                    include_drafts=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    reasoning_effort=request.reasoning_effort,
                    run_id=datetime.now(UTC).strftime("author-%Y%m%dT%H%M%S%fZ"),
                    grader_provider_name=request.grader_provider,
                    grader_model=request.grader_model,
                    grader_max_tokens=request.grader_max_tokens,
                    grader_reasoning_effort=request.grader_reasoning_effort,
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        rows = read_jsonl(run_dir / "predictions.jsonl")
        prediction = rows[-1] if rows else None
        if prediction is None:
            raise HTTPException(status_code=502, detail="provider run produced no prediction")
        score = (
            {"score": 0.0, "strict": 0.0, "reason": prediction.get("error")}
            if prediction.get("error")
            else score_answer(prediction.get("answer"), question.answer, prediction.get("grading"))
        )
        config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        record = _development_record(run_dir, config, prediction, score)
        write_json(run_dir / "development.json", record)
        return {"run_dir": str(run_dir), "history_record": record}

    @app.post("/api/preview-question")
    def preview_question(request: TestRequest) -> dict[str, Any]:
        try:
            exercise = Exercise.model_validate(request.exercise)
            question = next(item for item in exercise.questions if item.id == request.question_id)
        except (Exception, StopIteration) as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid exercise/question: {exc}"
            ) from exc
        with tempfile.TemporaryDirectory(prefix="part-catalog-bench-preview-") as temp_name:
            try:
                messages, _, assets = prepare_question_messages(
                    exercise=exercise,
                    question=question,
                    exercise_path=Path(temp_name) / "exercise.yaml",
                    manifest_path=manifest_path,
                )
            except Exception as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload = build_completion_payload(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            reasoning_effort=request.reasoning_effort,
        )
        return {
            "provider": request.provider,
            "request": payload,
            "assets": [
                {
                    "label": asset["label"],
                    "mime_type": asset["mime_type"],
                    "sha256": asset["sha256"],
                }
                for asset in assets
            ],
        }

    @app.post("/api/test-rubric")
    def test_rubric(request: RubricTestRequest) -> dict[str, Any]:
        try:
            answer = AnswerSpec.model_validate(request.answer)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid answer rubric: {exc}") from exc
        if answer.grading is None:
            raise HTTPException(status_code=422, detail="answer does not use rubric grading")
        grading = None
        if rubric_semantic_grade_required(request.response, answer):
            try:
                grading = grade_rubric_answer(
                    question_prompt=request.question_prompt,
                    predicted=request.response,
                    spec=answer,
                    provider=create_provider(request.provider),
                    provider_name=request.provider,
                    model=request.model,
                    max_tokens=request.max_tokens,
                    reasoning_effort=request.reasoning_effort,
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "score": score_answer(request.response, answer, grading),
            "grading": grading,
        }

    return app
