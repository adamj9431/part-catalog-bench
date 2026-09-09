import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from part_catalog_bench.authoring import _recent_development_models, create_authoring_app


def test_recent_development_models_are_distinct_and_newest_first(tmp_path: Path) -> None:
    development = tmp_path / "development"
    for index, (model, created_at) in enumerate(
        [
            ("older/model", "2026-08-01T12:00:00+00:00"),
            ("newer/model", "2026-08-03T12:00:00+00:00"),
            ("older/model", "2026-08-04T12:00:00+00:00"),
            ("middle/model", "2026-08-02T12:00:00+00:00"),
        ]
    ):
        run_dir = development / f"run-{index}"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps(
                {
                    "run_id": run_dir.name,
                    "created_at": created_at,
                    "provider": "openrouter",
                    "model": model,
                }
            ),
            encoding="utf-8",
        )

    assert _recent_development_models(development, "openrouter") == [
        {"id": "older/model", "used_at": "2026-08-04T12:00:00+00:00"},
        {"id": "newer/model", "used_at": "2026-08-03T12:00:00+00:00"},
        {"id": "middle/model", "used_at": "2026-08-02T12:00:00+00:00"},
    ]


def test_authoring_app_saves_and_indexes_exercises(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": {"id": "ford-car-master-1960-68", "title": "Test catalog"},
                "logical_pages": {
                    "illustrations:24-2": {
                        "catalog": "illustrations",
                        "source_page": 2,
                    },
                    "text:24-1": {"catalog": "text", "source_page": 1},
                },
                "catalogs": {
                    "text": {"source_start_page": 1, "source_end_page": 1},
                    "illustrations": {
                        "root_title": "Illustrations",
                        "source_start_page": 2,
                        "source_end_page": 4,
                    },
                },
                "documents": [
                    {
                        "catalog": "illustrations",
                        "title": "Section 20 - Brakes",
                        "bookmark_path": ["Illustrations", "Section 20 - Brakes"],
                        "source_start_page": 2,
                        "source_end_page": 2,
                    },
                    {
                        "catalog": "illustrations",
                        "title": "Section 20",
                        "bookmark_path": [
                            "Illustrations",
                            "Section 20 - Brakes",
                            "Section 20",
                        ],
                        "source_start_page": 3,
                        "source_end_page": 4,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    development = tmp_path / "development"
    client = TestClient(create_authoring_app(manifest, tmp_path / "exercises", development))
    home = client.get("/")
    assert home.status_code == 200
    assert 'data-zoom-reset="illustrations"' in home.text
    assert 'data-zoom-reset="text"' in home.text
    assert 'data-toggle-panel="illustrations"' in home.text
    assert 'data-toggle-panel="text"' in home.text
    assert "classList.toggle(`hide-${kind}`)" in home.text
    assert 'id="illustrations-resizer"' in home.text
    assert 'id="text-resizer"' in home.text
    assert 'data-editor-view="exercise"' in home.text
    assert 'data-editor-view="question"' in home.text
    assert 'id="question-picker"' in home.text
    assert '<select id="q-category">' in home.text
    assert 'id="vehicle-make"' not in home.text
    assert 'id="vehicle-model"' not in home.text
    assert 'id="vehicle-years"' not in home.text
    assert 'value="assembly_stack_tracing"' in home.text
    assert 'value="routed_system_tracing"' in home.text
    assert "initColumnResizers()" in home.text
    assert "button.primary:disabled" in home.text
    assert "Exact-answer fields are hidden" in home.text
    assert 'data-shape="polygon"' in home.text
    assert "Delete annotation" in home.text
    assert 'vector-effect="non-scaling-stroke"' in home.text
    assert 'class="polygon-vertex' in home.text
    assert "width:7px;height:7px" in home.text
    assert "finishPolygon()" in home.text
    assert 'addEventListener("gesturechange"' in home.text
    assert 'id="question-save-state"' in home.text
    assert 'id="test-history"' in home.text
    assert 'id="test-reasoning"' in home.text
    assert 'id="test-max-tokens"' in home.text
    assert 'list="test-models"' in home.text
    assert 'id="refresh-models"' in home.text
    assert "/api/models?provider=" in home.text
    assert "part-catalog-bench:last-model:" in home.text
    assert "part-catalog-bench:recent-models:" in home.text
    assert "Recently used" in home.text
    assert "newest first when dates are provided" in home.text
    assert 'id="grader-model"' in home.text
    assert 'id="grader-max-tokens"' in home.text
    assert 'id="preview-request"' in home.text
    assert 'id="download-request"' in home.text
    assert '"/api/preview-question"' in home.text
    assert "Weighted free-text rubric" in home.text
    assert "Test all examples" in home.text
    payload = {
        "id": "ui-example",
        "status": "draft",
        "title": "UI example",
        "source_id": "ford-car-master-1960-68",
        "context": {"catalog_refs": ["illustrations:24-2"]},
        "questions": [
            {
                "id": "q01",
                "prompt": "What is this part?",
                "category": "component_identification",
                "difficulty": "easy",
                "answer": {
                    "type": "ordered_part_path",
                    "item_family": "basic",
                    "value": [
                        {"part_number": "2455", "instance": 1, "pass": 1},
                        {"part_number": "01508", "instance": 1, "pass": 1},
                        {"part_number": "2455", "instance": 1, "pass": 2},
                    ],
                },
            }
        ],
    }
    assert client.post("/api/exercises", json={"exercise": payload}).status_code == 200
    bootstrap = client.get("/api/bootstrap").json()
    assert bootstrap["exercises"][0]["refs"] == ["illustrations:24-2"]
    assert bootstrap["logical_refs"]["illustrations"] == [
        "illustrations:24-2",
        "illustrations@source:3",
        "illustrations@source:4",
    ]
    saved = client.get("/api/exercises/ui-example").json()
    assert saved["questions"][0]["answer"]["value"][-1] == {
        "part_number": "2455",
        "instance": 1,
        "pass": 2,
    }
    run_dir = development / "author-test"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "author-test",
                "created_at": "2026-08-06T12:00:00+00:00",
                "provider": "openrouter",
                "model": "openai/test-model",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "predictions.jsonl").write_text(
        json.dumps(
            {
                "exercise_id": "ui-example",
                "question_id": "q01",
                "provider": "openrouter",
                "requested_model": "openai/test-model",
                "raw_response": '{"answer":[{"part_number":"2455","instance":1,"pass":1},'
                '{"part_number":"01508","instance":1,"pass":1},'
                '{"part_number":"2455","instance":1,"pass":2}]}',
                "answer": [
                    {"part_number": "2455", "instance": 1, "pass": 1},
                    {"part_number": "01508", "instance": 1, "pass": 1},
                    {"part_number": "2455", "instance": 1, "pass": 2},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    history = client.get("/api/development-history/ui-example/q01").json()["history"]
    assert history[0]["requested_model"] == "openai/test-model"
    assert history[0]["raw_response"].startswith('{"answer"')
    assert history[0]["outcome"] == "pass"
    assert history[0]["passed"] is True
    rubric_test = client.post(
        "/api/test-rubric",
        json={
            "question_prompt": "Which kit is referenced?",
            "answer": {
                "type": "short_text",
                "value": "Kit 3A187",
                "grading": {
                    "method": "rubric",
                    "criteria": [
                        {
                            "id": "kit",
                            "description": "Names kit 3A187.",
                            "points": 1,
                            "grader": {
                                "type": "contains_part_number",
                                "value": "3A187",
                            },
                        }
                    ],
                },
            },
            "response": "It refers to kit 3 A 187.",
            "provider": "openrouter",
            "model": "unused-for-deterministic-check",
        },
    )
    assert rubric_test.status_code == 200
    assert rubric_test.json()["score"]["score"] == 1.0
    truncated_dir = development / "author-truncated"
    truncated_dir.mkdir()
    (truncated_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "author-truncated",
                "created_at": "2026-08-06T13:00:00+00:00",
                "provider": "openrouter",
                "model": "openai/gpt-5.6-sol",
                "max_tokens": 2048,
                "reasoning_effort": "medium",
            }
        ),
        encoding="utf-8",
    )
    truncated_prediction = {
        "exercise_id": "ui-example",
        "question_id": "q01",
        "provider": "openrouter",
        "requested_model": "openai/gpt-5.6-sol",
        "raw_response": "None",
        "answer": "None",
        "provider_response": {
            "model": "openai/gpt-5.6-sol",
            "choices": [
                {
                    "finish_reason": "length",
                    "native_finish_reason": "max_output_tokens",
                    "message": {"content": None},
                }
            ],
            "usage": {"cost": 0.09},
        },
        "usage": {"cost": 0.09},
    }
    (truncated_dir / "predictions.jsonl").write_text(
        json.dumps(truncated_prediction) + "\n", encoding="utf-8"
    )
    (truncated_dir / "development.json").write_text(
        json.dumps(
            {
                **truncated_prediction,
                "run_id": "author-truncated",
                "created_at": "2026-08-06T13:00:00+00:00",
                "outcome": "fail",
                "passed": False,
                "score": {"strict": 0.0},
            }
        ),
        encoding="utf-8",
    )
    truncated_history = client.get("/api/development-history/ui-example/q01").json()["history"]
    assert truncated_history[0]["outcome"] == "error"
    assert truncated_history[0]["raw_response"] is None
    assert "Output limit reached" in truncated_history[0]["error"]
    assert truncated_history[0]["max_tokens"] == 2048
    assert truncated_history[0]["reasoning_effort"] == "medium"
    assert bootstrap["sections"]["illustrations"] == [
        {
            "title": "Section 20 - Brakes",
            "path": ["Section 20 - Brakes"],
            "depth": 1,
            "source_start_page": 2,
            "source_end_page": 4,
            "id": "illustrations-bookmark-0001",
            "page_count": 3,
        },
        {
            "title": "Section 20",
            "path": ["Section 20 - Brakes", "Section 20"],
            "depth": 2,
            "source_start_page": 3,
            "source_end_page": 4,
            "id": "illustrations-bookmark-0002",
            "page_count": 2,
        },
    ]


def test_authoring_save_overwrites_opened_exercise_filename(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": {"id": "test", "title": "Test catalog"},
                "logical_pages": {},
                "catalogs": {
                    "text": {"source_start_page": 1, "source_end_page": 1},
                    "illustrations": {"source_start_page": 2, "source_end_page": 2},
                },
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    exercises = tmp_path / "exercises"
    exercises.mkdir()
    original = exercises / "example-filename.yaml"
    exercise = {
        "id": "stable-id",
        "status": "draft",
        "title": "Before",
        "source_id": "test",
        "context": {"catalog_refs": ["illustrations@source:2"]},
        "questions": [
            {
                "id": "q01",
                "prompt": "What is this part?",
                "category": "component_identification",
                "difficulty": "easy",
                "answer": {"type": "short_text", "value": "part"},
            }
        ],
    }
    original.write_text(yaml.safe_dump(exercise, sort_keys=False), encoding="utf-8")
    client = TestClient(create_authoring_app(manifest, exercises))

    exercise["title"] = "After"
    response = client.post(
        "/api/exercises",
        json={"exercise": exercise, "original_id": "stable-id"},
    )

    assert response.status_code == 200
    assert response.json()["saved"] == str(original)
    assert yaml.safe_load(original.read_text(encoding="utf-8"))["title"] == "After"
    assert not (exercises / "stable-id.yaml").exists()
    assert len(client.get("/api/bootstrap").json()["exercises"]) == 1
