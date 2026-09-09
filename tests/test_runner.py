import json
from pathlib import Path
from typing import Any

import pytest

from part_catalog_bench import runner
from part_catalog_bench.models import AnswerSpec, AnswerType, Exercise
from part_catalog_bench.providers import IncompleteResponseError, ProviderResponse
from part_catalog_bench.runner import build_messages
from part_catalog_bench.util import read_jsonl


def test_prompt_contains_coordinate_grounding_and_compound_shape() -> None:
    messages, record = build_messages(
        system_prompt="system",
        source_guide="guide",
        exercise_title="Highlighted assembly",
        question_prompt="What do A and B do?",
        answer_spec=AnswerSpec(
            type="compound",
            fields={
                "A": AnswerSpec(type="short_text", value="supports tank"),
                "B": AnswerSpec(type="integer", value=2),
            },
        ),
        assets=[],
        grounding={
            "coordinate_system": "normalized_full_page_top_left",
            "annotations": [
                {
                    "label": "A",
                    "rect": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
                }
            ],
        },
    )
    text = messages[1]["content"][0]["text"]
    assert "normalized_full_page_top_left" in text
    assert '"A": short_text' in text
    assert '"B": integer' in text
    assert "supports tank" not in text
    assert "coordinates" in record.lower()
    assert "Vehicle metadata" not in text


def test_prompt_explains_ordered_part_path_instances_and_passes() -> None:
    messages, _ = build_messages(
        system_prompt="system",
        source_guide="guide",
        exercise_title="Pedal shaft",
        question_prompt="Trace the shaft.",
        answer_spec=AnswerSpec(
            type=AnswerType.ORDERED_PART_PATH,
            value=[{"part_number": "2471", "instance": 1, "pass": 1}],
        ),
        assets=[],
        grounding={},
    )
    text = messages[1]["content"][0]["text"]
    assert '"part_number": string' in text
    assert "same physical instance again" in text
    assert "Number instances and passes from 1 without gaps" in text


def test_part_number_prompt_requires_bare_number_without_leaking_answer() -> None:
    messages, _ = build_messages(
        system_prompt="system",
        source_guide="guide",
        exercise_title="Pedal bolt",
        question_prompt="What does this bolt thread into?",
        answer_spec=AnswerSpec(
            type=AnswerType.PART_NUMBER,
            value="34370-S",
            family="standard",
        ),
        assets=[],
        grounding={},
    )

    text = messages[1]["content"][0]["text"]
    assert (
        "Return only the part number, without a part name, explanatory text, or sentence "
        "punctuation."
    ) in text
    assert "Return it as a JSON string." in text
    assert "34370-S" not in text


def test_truncated_response_is_recorded_as_non_retryable_error(tmp_path: Path, monkeypatch) -> None:
    exercise = Exercise.model_validate(
        {
            "id": "truncated-example",
            "status": "ready",
            "title": "Truncated example",
            "source_id": "test-source",
            "context": {"assets": ["dummy.png"]},
            "questions": [
                {
                    "id": "q01",
                    "prompt": "Trace the shaft.",
                    "category": "spatial_relationship",
                    "difficulty": "hard",
                    "answer": {"type": "short_text", "value": "answer"},
                }
            ],
        }
    )
    exercise_path = tmp_path / "exercise.yaml"
    guide_path = tmp_path / "guide.md"
    guide_path.write_text("guide", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "system.md").write_text("system", encoding="utf-8")
    monkeypatch.setattr(runner, "load_exercises", lambda path: [(exercise_path, exercise)])
    monkeypatch.setattr(runner, "load_source_definition", lambda source_id: object())
    monkeypatch.setattr(runner, "source_guide_path", lambda definition: guide_path)
    monkeypatch.setattr(runner, "repository_root", lambda: tmp_path)
    monkeypatch.setattr(runner, "resolve_context_assets", lambda *args, **kwargs: [])

    raw: dict[str, Any] = {
        "model": "openai/gpt-5.6-sol",
        "choices": [
            {
                "finish_reason": "length",
                "native_finish_reason": "max_output_tokens",
                "message": {"content": None},
            }
        ],
        "usage": {"completion_tokens": 8192, "cost": 0.2},
    }

    class TruncatedProvider:
        name = "fake"
        calls = 0

        def complete(self, **kwargs: Any) -> None:
            self.calls += 1
            raise IncompleteResponseError("Output limit reached before final answer.", raw)

    provider = TruncatedProvider()
    run_dir = runner.run_benchmark(
        provider_name="fake",
        model="openai/gpt-5.6-sol",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        reasoning_effort="low",
        provider=provider,
        retries=2,
        run_id="truncated-run",
    )

    prediction = json.loads((run_dir / "predictions.jsonl").read_text(encoding="utf-8"))
    config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert provider.calls == 1
    assert prediction["raw_response"] is None
    assert prediction["answer"] is None
    assert prediction["error"].startswith("IncompleteResponseError:")
    assert prediction["provider_response"] == raw
    assert prediction["usage"]["cost"] == 0.2
    assert config["schema_version"] == 2
    assert config["dataset"]["exercise_count"] == 1
    assert config["dataset"]["question_count"] == 1
    assert len(config["dataset"]["sha256"]) == 64
    assert (run_dir / "dataset_snapshot.json").exists()
    assert config["max_tokens"] == 8192
    assert config["reasoning_effort"] == "low"


def test_run_saves_semantic_rubric_grades_with_prediction(tmp_path: Path, monkeypatch) -> None:
    exercise = Exercise.model_validate(
        {
            "id": "rubric-example",
            "status": "ready",
            "title": "Rubric example",
            "source_id": "test-source",
            "context": {"assets": ["dummy.png"]},
            "questions": [
                {
                    "id": "q01",
                    "prompt": "What does the square mean?",
                    "category": "catalog_notation",
                    "difficulty": "medium",
                    "answer": {
                        "type": "short_text",
                        "value": "Only in kit 3A187",
                        "grading": {
                            "method": "rubric",
                            "criteria": [
                                {
                                    "id": "meaning",
                                    "description": (
                                        "States that the part is supplied only in a kit."
                                    ),
                                    "points": 1,
                                }
                            ],
                        },
                    },
                }
            ],
        }
    )
    exercise_path = tmp_path / "exercise.yaml"
    guide_path = tmp_path / "guide.md"
    guide_path.write_text("guide", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "system.md").write_text("system", encoding="utf-8")
    monkeypatch.setattr(runner, "load_exercises", lambda path: [(exercise_path, exercise)])
    monkeypatch.setattr(runner, "load_source_definition", lambda source_id: object())
    monkeypatch.setattr(runner, "source_guide_path", lambda definition: guide_path)
    monkeypatch.setattr(runner, "repository_root", lambda: tmp_path)
    monkeypatch.setattr(runner, "resolve_context_assets", lambda *args, **kwargs: [])

    class CandidateProvider:
        name = "fake"

        def complete(self, **kwargs: Any) -> ProviderResponse:
            return ProviderResponse(
                text='{"answer":"It is available only as part of a kit."}',
                raw={"model": "candidate"},
                response_model="candidate",
                usage={},
            )

    class GraderProvider:
        name = "fake-grader"

        def complete(self, **kwargs: Any) -> ProviderResponse:
            return ProviderResponse(
                text=(
                    '{"criteria_met":true,'
                    '"explanation":"The response states that availability is kit-only."}'
                ),
                raw={"model": "fixed-grader"},
                response_model="fixed-grader",
                usage={"total_tokens": 12},
            )

    run_dir = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=CandidateProvider(),
        grader_provider_name="fake-grader",
        grader_model="fixed-grader",
        grader_provider=GraderProvider(),
        run_id="rubric-run",
    )

    prediction = json.loads((run_dir / "predictions.jsonl").read_text(encoding="utf-8"))
    config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert prediction["grading"]["criteria"][0]["criteria_met"] is True
    assert config["grader"]["model"] == "fixed-grader"


def _reuse_test_exercise(
    *, prompt: str = "Identify the part.", include_q02: bool = False
) -> Exercise:
    questions: list[dict[str, Any]] = [
        {
            "id": "q01",
            "prompt": prompt,
            "category": "component_identification",
            "difficulty": "easy",
            "answer": {"type": "part_number", "value": "1001"},
        }
    ]
    if include_q02:
        questions.append(
            {
                "id": "q02",
                "prompt": "Identify the second part.",
                "category": "component_identification",
                "difficulty": "medium",
                "answer": {"type": "part_number", "value": "1002"},
            }
        )
    return Exercise.model_validate(
        {
            "id": "reuse-example",
            "status": "ready",
            "title": "Reuse example",
            "source_id": "test-source",
            "context": {"assets": ["dummy.png"]},
            "questions": questions,
        }
    )


def _configure_reuse_test(
    tmp_path: Path,
    monkeypatch,
    selected: list[tuple[Path, Exercise]],
) -> Path:
    exercise_path = tmp_path / "exercise.yaml"
    guide_path = tmp_path / "guide.md"
    guide_path.write_text("guide", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "system.md").write_text("system", encoding="utf-8")
    monkeypatch.setattr(runner, "load_exercises", lambda path: selected)
    monkeypatch.setattr(runner, "load_source_definition", lambda source_id: object())
    monkeypatch.setattr(runner, "source_guide_path", lambda definition: guide_path)
    monkeypatch.setattr(runner, "repository_root", lambda: tmp_path)
    monkeypatch.setattr(runner, "resolve_context_assets", lambda *args, **kwargs: [])
    return exercise_path


class _CountingProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, **kwargs: Any) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            text='{"answer":"1001"}',
            raw={"model": "candidate"},
            response_model="candidate",
            usage={"total_tokens": 10},
        )


def test_expanded_dataset_reuses_unchanged_questions_only(tmp_path: Path, monkeypatch) -> None:
    selected = [(tmp_path / "exercise.yaml", _reuse_test_exercise())]
    exercise_path = _configure_reuse_test(tmp_path, monkeypatch, selected)
    first_provider = _CountingProvider()
    first_run = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=first_provider,
        run_id="original",
    )
    assert first_provider.calls == 1

    selected[:] = [(tmp_path / "exercise.yaml", _reuse_test_exercise(include_q02=True))]
    expanded_provider = _CountingProvider()
    expanded_run = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=expanded_provider,
        run_id="expanded",
        reuse_from=[first_run],
    )

    rows = read_jsonl(expanded_run / "predictions.jsonl")
    assert expanded_provider.calls == 1
    assert [row["question_id"] for row in rows] == ["q01", "q02"]
    assert rows[0]["reused_from"]["run_id"] == "original"
    assert rows[1]["reused_from"] is None
    config = json.loads((expanded_run / "run.json").read_text(encoding="utf-8"))
    assert config["dataset"]["question_count"] == 2
    assert config["reuse"]["sources"][0]["run_id"] == "original"


def test_changed_prompt_is_not_reused(tmp_path: Path, monkeypatch) -> None:
    selected = [(tmp_path / "exercise.yaml", _reuse_test_exercise(prompt="Identify the part."))]
    exercise_path = _configure_reuse_test(tmp_path, monkeypatch, selected)
    first_run = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=_CountingProvider(),
        run_id="original",
    )

    selected[:] = [
        (tmp_path / "exercise.yaml", _reuse_test_exercise(prompt="Identify this component."))
    ]
    changed_provider = _CountingProvider()
    changed_run = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=changed_provider,
        run_id="changed",
        reuse_from=[first_run],
    )

    row = read_jsonl(changed_run / "predictions.jsonl")[0]
    assert changed_provider.calls == 1
    assert row["reused_from"] is None


def test_reuse_rejects_incompatible_model_settings(tmp_path: Path, monkeypatch) -> None:
    selected = [(tmp_path / "exercise.yaml", _reuse_test_exercise())]
    exercise_path = _configure_reuse_test(tmp_path, monkeypatch, selected)
    first_run = runner.run_benchmark(
        provider_name="fake",
        model="candidate",
        exercises_path=exercise_path,
        manifest_path=None,
        output_root=tmp_path / "results",
        provider=_CountingProvider(),
        max_tokens=8192,
        run_id="original",
    )

    with pytest.raises(ValueError, match="incompatible run settings: max_tokens"):
        runner.run_benchmark(
            provider_name="fake",
            model="candidate",
            exercises_path=exercise_path,
            manifest_path=None,
            output_root=tmp_path / "results",
            provider=_CountingProvider(),
            max_tokens=32768,
            run_id="incompatible",
            reuse_from=[first_run],
        )
