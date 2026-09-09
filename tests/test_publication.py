import json
import shutil

import pytest
from PIL import Image

from part_catalog_bench.dataset import write_dataset_snapshot
from part_catalog_bench.models import Exercise
from part_catalog_bench.publication import export_site, public_run
from part_catalog_bench.reporting import score_run
from part_catalog_bench.util import append_jsonl, write_json


@pytest.fixture
def private_run(tmp_path):
    exercise = Exercise.model_validate({
        "id": "SECRET_EXERCISE", "title": "SECRET_TITLE", "status": "ready",
        "source_id": "ford-car-master-1960-68",
        "context": {"catalog_refs": ["illustrations:24-2"]},
        "questions": [{
            "id": f"SECRET_Q{i}", "prompt": "SECRET_PROMPT",
            "category": "component_identification", "difficulty": "easy",
            "answer": {"type": "short_text", "value": "SECRET_ANSWER"},
        } for i in range(6)],
    })
    run = tmp_path / "run"
    dataset = write_dataset_snapshot(run, [(tmp_path / "SECRET_FILE.yaml", exercise)], tmp_path)
    write_json(run / "run.json", {
        "dataset": dataset, "model": "test/model", "provider": "test",
        "created_at": "2026-09-08T12:00:00Z", "evaluation_mode": "isolated-question",
        "input_modality": "image-native", "max_tokens": 32768, "temperature": 0,
        "dpi": 300, "timeout": 600, "retries": 2,
        "grader": {"model": "test/grader", "max_tokens": 512},
    })
    append_jsonl(run / "predictions.jsonl", [{
        "exercise_id": exercise.id, "question_id": q.id, "answer": "SECRET_ANSWER",
        "provider_response": {"reasoning": "SECRET_REASONING", "key": "SECRET_KEY"},
        "usage": {"cost": .1}, "latency_seconds": 2,
    } for q in exercise.questions])
    score_run(run)
    return run


def test_export_contains_only_aggregates(private_run, tmp_path):
    output = tmp_path / "public"
    result = export_site([private_run], output, "Test release")
    for artifact in output.iterdir():
        if artifact.suffix == ".png":
            with Image.open(artifact) as preview:
                assert preview.size == (1200, 630)
                assert preview.mode == "RGB"
                assert not preview.info
            continue
        assert "SECRET" not in artifact.read_text()
        assert str(tmp_path) not in artifact.read_text()
    payload = json.loads(result.read_text())
    row = payload["models"][0]
    assert row["score"] == 1
    assert row["questions"] == 6
    assert row["by_difficulty"]["easy"]["questions"] == 6
    assert row["cost_usd"] == pytest.approx(.6)
    assert set(output.iterdir()) == {
        output / "results.json", output / "results.csv", output / "pareto-preview.png",
    }


def test_incomplete_predictions_rejected(private_run, tmp_path):
    file = private_run / "predictions.jsonl"
    file.write_text("\n".join(file.read_text().splitlines()[:-1]))
    with pytest.raises(ValueError, match="incomplete"):
        export_site([private_run], tmp_path / "public", "Test")
    assert not (tmp_path / "public").exists()


def test_invalid_scores_rejected(private_run):
    file = private_run / "scores.json"
    scores = json.loads(file.read_text())
    scores["summary"]["valid_for_comparison"] = False
    write_json(file, scores)
    with pytest.raises(ValueError, match="invalid"):
        public_run(private_run)


def test_missing_cost_is_not_zero_and_small_groups_are_suppressed(private_run):
    file = private_run / "scores.json"
    scores = json.loads(file.read_text())
    scores["metrics"]["candidate"]["cost"]["complete"] = False
    scores["by_category"]["quantity_reasoning"] = {"questions": 3, "score": 1}
    scores["by_category"]["SECRET_LABEL"] = {"questions": 6, "score": 1}
    write_json(file, scores)
    row = public_run(private_run)
    assert row["cost_usd"] is None
    assert "quantity_reasoning" not in row["by_category"]
    assert "SECRET_LABEL" not in row["by_category"]


def test_duplicate_models_rejected(private_run, tmp_path):
    with pytest.raises(ValueError, match="one run per model"):
        export_site([private_run, private_run], tmp_path / "public", "Test")


def test_equivalent_numeric_settings_accepted(private_run, tmp_path):
    other = tmp_path / "other"
    shutil.copytree(private_run, other)
    config = json.loads((other / "run.json").read_text())
    config.update(model="test/other", timeout=600.0, temperature=0.0)
    write_json(other / "run.json", config)
    score_run(other)
    export_site([private_run, other], tmp_path / "public", "Test")
    config["timeout"] = 601.0
    write_json(other / "run.json", config)
    score_run(other)
    with pytest.raises(ValueError, match="different evaluation settings"):
        export_site([private_run, other], tmp_path / "public", "Test")
