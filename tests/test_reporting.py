import json

import pytest

from part_catalog_bench.dataset import write_dataset_snapshot
from part_catalog_bench.models import load_exercises
from part_catalog_bench.reporting import aggregate_run_metrics, score_run, write_report
from part_catalog_bench.util import write_json


def test_report_presents_question_weighted_headline(tmp_path) -> None:
    scores = {
        "summary": {
            "exercises": 2,
            "questions": 4,
            "question_weighted_score": 0.5,
            "difficulty_balanced_score": 2 / 3,
            "macro_exercise_score": 2 / 3,
            "strict_question_accuracy": 0.5,
            "diagnostic_partial_accuracy": 0.625,
            "scoring_errors": 0,
            "valid_for_comparison": True,
            "bootstrap_95_ci": [1 / 3, 1.0],
        },
        "run": {
            "run_id": "test-run",
            "provider": "test",
            "model": "test-model",
            "evaluation_mode": "isolated-question",
            "input_modality": "image-native",
        },
        "by_difficulty": {
            "easy": {
                "questions": 1,
                "score": 1.0,
                "strict_accuracy": 1.0,
                "partial_accuracy": 1.0,
            }
        },
        "by_category": {},
        "by_answer_type": {},
        "exercises": [
            {
                "exercise_id": "example",
                "questions": 4,
                "score": 0.5,
                "partial_accuracy": 0.625,
            }
        ],
    }

    report = write_report(tmp_path, scores).read_text(encoding="utf-8")

    assert "Question-weighted score: **50.0%**" in report
    assert "Difficulty-balanced score: 66.7%" in report
    assert "Macro exercise score (diagnostic): 66.7%" in report
    assert "95% exercise-clustered bootstrap interval: 33.3%–100.0%" in report


def test_aggregate_run_metrics_separates_candidate_and_grader_costs() -> None:
    metrics = aggregate_run_metrics(
        [
            {
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "cost": 0.01,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
                "latency_seconds": 2.0,
                "grading": {
                    "criteria": [
                        {
                            "usage": {
                                "input_tokens": 30,
                                "output_tokens": 5,
                                "total_tokens": 35,
                                "cost_usd": 0.002,
                            },
                            "latency_seconds": 0.5,
                        }
                    ]
                },
            },
            {
                "usage": {
                    "input_tokens": 80,
                    "output_tokens": 10,
                    "total_tokens": 90,
                    "cost": 0.008,
                },
                "latency_seconds": 4.0,
            },
        ]
    )

    assert metrics["candidate"]["cost"]["cost_usd"] == pytest.approx(0.018)
    assert metrics["candidate"]["tokens"]["total"] == 210
    assert metrics["candidate"]["latency"]["mean_seconds"] == 3.0
    assert metrics["candidate"]["latency"]["p95_seconds"] == 4.0
    assert metrics["grader"]["cost"]["cost_usd"] == 0.002
    assert metrics["combined"]["cost"]["cost_usd"] == pytest.approx(0.02)
    assert metrics["combined"]["tokens"]["total"] == 245


def test_score_run_uses_frozen_snapshot_and_flags_mismatched_override(tmp_path) -> None:
    exercise_path = tmp_path / "exercise.yaml"
    initial = {
        "schema_version": 1,
        "id": "snapshot-example",
        "status": "ready",
        "title": "Snapshot example",
        "source_id": "test-source",
        "context": {"assets": ["unused.png"]},
        "questions": [
            {
                "id": "q01",
                "prompt": "Which number?",
                "category": "component_identification",
                "difficulty": "easy",
                "answer": {"type": "part_number", "value": "1234", "family": "basic"},
            }
        ],
    }
    exercise_path.write_text(json.dumps(initial), encoding="utf-8")
    selected = load_exercises(exercise_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    dataset = write_dataset_snapshot(run_dir, selected, exercise_path)
    write_json(
        run_dir / "run.json",
        {
            "schema_version": 2,
            "run_id": "snapshot-run",
            "provider": "test",
            "model": "test-model",
            "exercises_path": str(exercise_path),
            "exercise_ids": ["snapshot-example"],
            "dataset": dataset,
        },
    )
    (run_dir / "predictions.jsonl").write_text(
        json.dumps(
            {
                "exercise_id": "snapshot-example",
                "question_id": "q01",
                "answer": "1234",
                "usage": {"total_tokens": 10, "cost": 0.01},
                "latency_seconds": 1.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    changed = json.loads(json.dumps(initial))
    changed["questions"][0]["answer"]["value"] = "9999"
    exercise_path.write_text(json.dumps(changed), encoding="utf-8")

    frozen_scores = score_run(run_dir)
    assert frozen_scores["summary"]["question_weighted_score"] == 1.0
    assert frozen_scores["dataset"]["verification"] == "verified"
    assert frozen_scores["dataset"]["scoring_source"] == "run_snapshot"
    assert frozen_scores["metrics"]["candidate"]["cost"]["cost_usd"] == 0.01

    override_scores = score_run(run_dir, exercise_path)
    assert override_scores["summary"]["question_weighted_score"] == 0.0
    assert override_scores["dataset"]["verification"] == "mismatch"
    assert override_scores["summary"]["valid_for_comparison"] is False
