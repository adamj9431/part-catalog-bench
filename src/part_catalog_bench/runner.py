from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assets import resolve_context_assets
from .dataset import (
    build_dataset_snapshot,
    git_provenance,
    load_dataset_snapshot,
    write_dataset_snapshot,
)
from .models import (
    AnswerSpec,
    AnswerType,
    Exercise,
    ExerciseStatus,
    Prediction,
    Question,
    load_exercises,
)
from .providers import (
    REASONING_EFFORTS,
    IncompleteResponseError,
    Provider,
    create_provider,
    image_content,
)
from .rubric import grade_rubric_answer, rubric_semantic_grade_required
from .source import load_source_definition, repository_root, source_guide_path
from .util import append_jsonl, read_jsonl, sha256_text, write_json

REUSE_CONFIG_FIELDS = (
    "evaluation_mode",
    "input_modality",
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "reasoning_effort",
    "timeout",
    "retries",
    "dpi",
)


def _answer_fingerprint(answer: AnswerSpec) -> str:
    canonical = json.dumps(
        answer.model_dump(mode="json", exclude_none=False),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256_text(canonical)


def _question_answers(exercises: list[Exercise]) -> dict[tuple[str, str], str]:
    return {
        (exercise.id, question.id): _answer_fingerprint(question.answer)
        for exercise in exercises
        for question in exercise.questions
    }


def _reuse_config_mismatches(
    source_config: dict[str, Any], current_config: dict[str, Any]
) -> list[str]:
    return [
        field
        for field in REUSE_CONFIG_FIELDS
        if source_config.get(field) != current_config.get(field)
    ]


def _load_reuse_sources(
    source_dirs: list[Path],
    *,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for source_dir in source_dirs:
        config_path = source_dir / "run.json"
        predictions_path = source_dir / "predictions.jsonl"
        if not config_path.is_file() or not predictions_path.is_file():
            raise ValueError(
                f"reuse source {source_dir} must contain run.json and predictions.jsonl"
            )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        mismatches = _reuse_config_mismatches(config, current_config)
        if mismatches:
            raise ValueError(
                f"reuse source {source_dir} has incompatible run settings: " + ", ".join(mismatches)
            )
        dataset = config.get("dataset") or {}
        snapshot_file = dataset.get("snapshot_file")
        dataset_sha256 = dataset.get("sha256")
        if not snapshot_file or not dataset_sha256:
            raise ValueError(
                f"reuse source {source_dir} predates dataset snapshots and cannot be reused safely"
            )
        source_exercises = load_dataset_snapshot(
            source_dir / snapshot_file,
            dataset_sha256,
        )
        predictions: dict[tuple[str, str], dict[str, Any]] = {}
        for row in read_jsonl(predictions_path):
            key = (row.get("exercise_id"), row.get("question_id"))
            if key[0] and key[1]:
                predictions[key] = row
        sources.append(
            {
                "run_id": config.get("run_id") or source_dir.name,
                "dataset_sha256": dataset_sha256,
                "grader": config.get("grader") or {},
                "answer_sha256": _question_answers(source_exercises),
                "predictions": predictions,
            }
        )
    return sources


def _find_reusable_prediction(
    sources: list[dict[str, Any]],
    *,
    key: tuple[str, str],
    prompt_sha256: str,
    asset_sha256: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for source in sources:
        row = source["predictions"].get(key)
        if row is None:
            continue
        error = row.get("error")
        if error and not str(error).startswith("IncompleteResponseError:"):
            continue
        if row.get("prompt_sha256") != prompt_sha256:
            continue
        if (row.get("asset_sha256") or {}) != asset_sha256:
            continue
        return row, source
    return None


def _answer_shape(answer: AnswerSpec) -> str:
    if answer.type == AnswerType.COMPOUND:
        fields = ", ".join(f'"{name}": {field.type.value}' for name, field in answer.fields.items())
        return f"Return a JSON object with exactly these fields and value types: {{{fields}}}."
    return {
        "ordered_list": "Return the answer as a JSON array in the requested order.",
        "ordered_part_path": (
            "Return a JSON array in traversal order. Each element must be exactly "
            '{"part_number": string, "instance": positive integer, "pass": positive integer}. '
            "Use a different instance number for each separate physical copy of the same part. "
            "If the path passes through the same physical instance again, reuse its instance "
            "number and increment pass. Number instances and passes from 1 without gaps."
        ),
        "unordered_set": "Return the answer as a JSON array; order is not important.",
        "part_number": (
            "Return only the part number, without a part name, explanatory text, or sentence "
            "punctuation. Return it as a JSON string."
        ),
        "integer": "Return the answer as a JSON integer.",
        "boolean": "Return the answer as a JSON boolean.",
    }.get(answer.type.value, "Return the answer as a JSON string.")


def build_messages(
    *,
    system_prompt: str,
    source_guide: str,
    exercise_title: str,
    question_prompt: str,
    answer_spec: AnswerSpec,
    assets: list[dict[str, Any]],
    grounding: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    question_text = (
        f"CATALOG GUIDE\n{source_guide}\n\n"
        f"EXERCISE\n{exercise_title}\n\n"
        f"QUESTION\n{question_prompt}\n\n"
        "GROUNDING COORDINATES\n"
        "Coordinates use a top-left origin and are normalized to the full uncropped page. "
        f"Crops and annotations: {json.dumps(grounding, sort_keys=True)}\n\n"
        f'OUTPUT\n{_answer_shape(answer_spec)} Return only {{"answer": ...}}.'
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": question_text}]
    for index, asset in enumerate(assets, start=1):
        content.append(
            {
                "type": "text",
                "text": f"Context image {index}: {asset['label']}",
            }
        )
        content.append(image_content(Path(asset["path"]), asset["mime_type"]))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]
    prompt_record = json.dumps(
        {
            "system": system_prompt,
            "question_text": question_text,
            "assets": [{"label": asset["label"], "sha256": asset["sha256"]} for asset in assets],
        },
        sort_keys=True,
    )
    return messages, prompt_record


def prepare_question_messages(
    *,
    exercise: Exercise,
    question: Question,
    exercise_path: Path,
    manifest_path: Path | None,
    dpi: int = 300,
    system_prompt: str | None = None,
    source_guide: str | None = None,
) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    """Resolve assets and build the messages used for one isolated question."""
    if system_prompt is None:
        system_prompt = (repository_root() / "prompts" / "system.md").read_text(encoding="utf-8")
    if source_guide is None:
        definition = load_source_definition(exercise.source_id)
        source_guide = source_guide_path(definition).read_text(encoding="utf-8")
    annotations = [*exercise.context.annotations, *question.annotations]
    assets = resolve_context_assets(
        manifest_path,
        exercise.context.catalog_refs,
        exercise.context.pages,
        exercise.context.assets,
        annotations,
        exercise_path=exercise_path,
        dpi=dpi,
    )
    grounding = {
        "coordinate_system": "normalized_full_page_top_left",
        "pages": [
            page.model_dump(mode="json", exclude_none=True) for page in exercise.context.pages
        ],
        "annotations": [
            annotation.model_dump(mode="json", exclude_none=True) for annotation in annotations
        ],
    }
    messages, prompt_record = build_messages(
        system_prompt=system_prompt,
        source_guide=source_guide,
        exercise_title=exercise.title,
        question_prompt=question.prompt,
        answer_spec=question.answer,
        assets=assets,
        grounding=grounding,
    )
    return messages, prompt_record, assets


def parse_answer(text: str) -> Any:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()
    candidates = [stripped]
    object_match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if object_match and object_match.group() != stripped:
        candidates.append(object_match.group())
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed["answer"]
        return parsed
    return stripped


def run_benchmark(
    *,
    provider_name: str,
    model: str,
    exercises_path: Path,
    manifest_path: Path | None,
    output_root: Path,
    include_drafts: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    reasoning_effort: str | None = None,
    timeout: float = 180.0,
    retries: int = 2,
    dpi: int = 300,
    run_id: str | None = None,
    provider: Provider | None = None,
    grader_provider_name: str | None = None,
    grader_model: str | None = None,
    grader_max_tokens: int = 1024,
    grader_reasoning_effort: str | None = None,
    grader_provider: Provider | None = None,
    reuse_from: list[Path] | None = None,
) -> Path:
    if reasoning_effort is not None:
        reasoning_effort = reasoning_effort.strip().lower()
        if reasoning_effort not in REASONING_EFFORTS:
            choices = ", ".join(sorted(REASONING_EFFORTS))
            raise ValueError(f"reasoning_effort must be one of: {choices}")
    if grader_reasoning_effort is not None:
        grader_reasoning_effort = grader_reasoning_effort.strip().lower()
        if grader_reasoning_effort not in REASONING_EFFORTS:
            choices = ", ".join(sorted(REASONING_EFFORTS))
            raise ValueError(f"grader_reasoning_effort must be one of: {choices}")
    if grader_max_tokens < 128:
        raise ValueError("grader_max_tokens must be at least 128")
    loaded = load_exercises(exercises_path)
    selected = [
        (path, exercise)
        for path, exercise in loaded
        if include_drafts or exercise.status == ExerciseStatus.READY
    ]
    if not selected:
        raise ValueError("no exercises selected; mark one ready or use --include-drafts")

    grader_provider_name = grader_provider_name or provider_name
    grader_model = grader_model or model
    run_id = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{provider_name}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = run_dir / "predictions.jsonl"
    completed = {
        (row.get("exercise_id"), row.get("question_id")) for row in read_jsonl(predictions_path)
    }

    repo_root = repository_root()
    system_prompt = (repo_root / "prompts" / "system.md").read_text(encoding="utf-8")
    source_guides: dict[str, str] = {}
    _, current_dataset = build_dataset_snapshot(selected, exercises_path)
    current_reuse_config = {
        "evaluation_mode": "isolated-question",
        "input_modality": "image-native",
        "provider": provider_name,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "timeout": timeout,
        "retries": retries,
        "dpi": dpi,
    }
    reuse_sources = _load_reuse_sources(
        [Path(item) for item in (reuse_from or [])],
        current_config=current_reuse_config,
    )
    provider = provider or create_provider(provider_name)
    existing_config_path = run_dir / "run.json"
    if existing_config_path.exists():
        existing_config = json.loads(existing_config_path.read_text(encoding="utf-8"))
        existing_dataset = existing_config.get("dataset") or {}
        expected_fingerprint = existing_dataset.get("sha256")
        snapshot_file = existing_dataset.get("snapshot_file")
        if not expected_fingerprint or not snapshot_file:
            raise ValueError(
                f"run {run_id!r} predates dataset snapshots and cannot be resumed safely; "
                "use a new run ID"
            )
        load_dataset_snapshot(run_dir / snapshot_file, expected_fingerprint)
        if current_dataset["sha256"] != expected_fingerprint:
            raise ValueError(
                f"run {run_id!r} was created with dataset {expected_fingerprint}, but the "
                f"selected exercises now fingerprint as {current_dataset['sha256']}; use a "
                "new run ID or restore the original exercises"
            )
        config = existing_config
    else:
        dataset = write_dataset_snapshot(run_dir, selected, exercises_path)
        provenance = git_provenance(repo_root)
        if provenance:
            dataset["repository"] = provenance
        config = {
            "schema_version": 2,
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "evaluation_mode": "isolated-question",
            "input_modality": "image-native",
            "provider": provider_name,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "timeout": timeout,
            "retries": retries,
            "dpi": dpi,
            "exercises_path": str(exercises_path.resolve()),
            "manifest_path": str(manifest_path.resolve()) if manifest_path else None,
            "exercise_ids": [exercise.id for _, exercise in selected],
            "dataset": dataset,
            "grader": {
                "provider": grader_provider_name,
                "model": grader_model,
                "temperature": 0.0,
                "max_tokens": grader_max_tokens,
                "reasoning_effort": grader_reasoning_effort,
            },
            "reuse": {
                "sources": [
                    {
                        "run_id": source["run_id"],
                        "dataset_sha256": source["dataset_sha256"],
                    }
                    for source in reuse_sources
                ]
            },
        }
        write_json(existing_config_path, config)

    for exercise_path, exercise in selected:
        if exercise.source_id not in source_guides:
            definition = load_source_definition(exercise.source_id)
            source_guides[exercise.source_id] = source_guide_path(definition).read_text(
                encoding="utf-8"
            )
        for question in exercise.questions:
            key = (exercise.id, question.id)
            if key in completed:
                continue
            messages, prompt_record, assets = prepare_question_messages(
                exercise=exercise,
                question=question,
                exercise_path=exercise_path,
                manifest_path=manifest_path,
                dpi=dpi,
                system_prompt=system_prompt,
                source_guide=source_guides[exercise.source_id],
            )
            prompt_sha256 = sha256_text(prompt_record)
            asset_sha256 = {asset["label"]: asset["sha256"] for asset in assets}
            reusable = _find_reusable_prediction(
                reuse_sources,
                key=key,
                prompt_sha256=prompt_sha256,
                asset_sha256=asset_sha256,
            )
            if reusable is not None:
                row, source = reusable
                prediction = Prediction.model_validate(row)
                prediction.reused_from = {
                    "run_id": source["run_id"],
                    "dataset_sha256": source["dataset_sha256"],
                }
                current_answer_sha256 = _answer_fingerprint(question.answer)
                source_answer_sha256 = source["answer_sha256"].get(key)
                grader_config = config["grader"]
                grading_matches = (
                    source_answer_sha256 == current_answer_sha256
                    and source["grader"] == grader_config
                )
                if prediction.error is None and rubric_semantic_grade_required(
                    prediction.answer, question.answer
                ):
                    if not grading_matches:
                        if grader_provider is None:
                            grader_provider = (
                                provider
                                if grader_provider_name == provider_name
                                else create_provider(grader_provider_name)
                            )
                        prediction.grading = grade_rubric_answer(
                            question_prompt=question.prompt,
                            predicted=prediction.answer,
                            spec=question.answer,
                            provider=grader_provider,
                            provider_name=grader_provider_name,
                            model=grader_model,
                            max_tokens=grader_max_tokens,
                            reasoning_effort=grader_reasoning_effort,
                            timeout=timeout,
                            retries=retries,
                        )
                elif not grading_matches:
                    prediction.grading = None
                append_jsonl(predictions_path, [prediction.model_dump(mode="json")])
                completed.add(key)
                continue
            prediction = Prediction(
                exercise_id=exercise.id,
                question_id=question.id,
                provider=provider_name,
                requested_model=model,
                prompt_sha256=prompt_sha256,
                asset_sha256=asset_sha256,
            )
            last_error: Exception | None = None
            for attempt in range(retries + 1):
                start = time.monotonic()
                try:
                    response = provider.complete(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        reasoning_effort=reasoning_effort,
                        timeout=timeout,
                    )
                    prediction.latency_seconds = time.monotonic() - start
                    prediction.answer = parse_answer(response.text)
                    prediction.raw_response = response.text
                    prediction.response_model = response.response_model
                    prediction.usage = response.usage
                    prediction.provider_response = response.raw
                    last_error = None
                    break
                except Exception as exc:
                    prediction.latency_seconds = time.monotonic() - start
                    last_error = exc
                    if isinstance(exc, IncompleteResponseError):
                        prediction.response_model = exc.response_model
                        prediction.usage = exc.usage
                        prediction.provider_response = exc.raw
                        break
                    if attempt < retries:
                        time.sleep(min(2**attempt, 8))
            if last_error is not None:
                prediction.error = f"{type(last_error).__name__}: {last_error}"
            elif rubric_semantic_grade_required(prediction.answer, question.answer):
                if grader_provider is None:
                    grader_provider = (
                        provider
                        if grader_provider_name == provider_name
                        else create_provider(grader_provider_name)
                    )
                prediction.grading = grade_rubric_answer(
                    question_prompt=question.prompt,
                    predicted=prediction.answer,
                    spec=question.answer,
                    provider=grader_provider,
                    provider_name=grader_provider_name,
                    model=grader_model,
                    max_tokens=grader_max_tokens,
                    reasoning_effort=grader_reasoning_effort,
                    timeout=timeout,
                    retries=retries,
                )
            append_jsonl(predictions_path, [prediction.model_dump(mode="json")])
            completed.add(key)
    return run_dir
