import pytest
import yaml
from pydantic import ValidationError

from part_catalog_bench.models import AnswerSpec, Exercise, NormalizedRect, load_exercises


def _exercise() -> dict:
    return {
        "id": "annotation-example",
        "status": "draft",
        "title": "Highlighted part",
        "source_id": "ford-car-master-1960-68",
        "context": {
            "pages": [
                {
                    "ref": "illustrations:24-2",
                    "crop": {"x": 0.05, "y": 0.1, "width": 0.9, "height": 0.45},
                }
            ],
            "annotations": [
                {
                    "id": "part-a",
                    "label": "A",
                    "page_ref": "illustrations:24-2",
                    "rect": {"x": 0.2, "y": 0.2, "width": 0.1, "height": 0.1},
                }
            ],
        },
        "questions": [
            {
                "id": "q01",
                "prompt": "What does highlighted part A do?",
                "category": "functional_reasoning",
                "difficulty": "medium",
                "answer": {"type": "short_text", "value": "supports the pedal shaft"},
            }
        ],
    }


def test_crop_and_shared_annotation_validate() -> None:
    exercise = Exercise.model_validate(_exercise())
    assert exercise.context.pages[0].crop.width == 0.9
    assert exercise.context.annotations[0].label == "A"


def test_polygon_annotation_validates() -> None:
    data = _exercise()
    annotation = data["context"]["annotations"][0]
    annotation.pop("rect")
    annotation["polygon"] = [
        {"x": 0.2, "y": 0.2},
        {"x": 0.4, "y": 0.2},
        {"x": 0.3, "y": 0.4},
    ]

    exercise = Exercise.model_validate(data)

    assert exercise.context.annotations[0].rect is None
    assert len(exercise.context.annotations[0].polygon or []) == 3


def test_annotation_requires_exactly_one_geometry() -> None:
    data = _exercise()
    data["context"]["annotations"][0]["polygon"] = [
        {"x": 0.2, "y": 0.2},
        {"x": 0.4, "y": 0.2},
        {"x": 0.3, "y": 0.4},
    ]

    with pytest.raises(ValidationError, match="exactly one of rect or polygon"):
        Exercise.model_validate(data)


def test_polygon_annotation_rejects_zero_area() -> None:
    data = _exercise()
    annotation = data["context"]["annotations"][0]
    annotation.pop("rect")
    annotation["polygon"] = [
        {"x": 0.2, "y": 0.2},
        {"x": 0.3, "y": 0.3},
        {"x": 0.4, "y": 0.4},
    ]

    with pytest.raises(ValidationError, match="non-zero enclosed area"):
        Exercise.model_validate(data)


def test_annotation_must_reference_context_page() -> None:
    data = _exercise()
    data["context"]["annotations"][0]["page_ref"] = "illustrations:30-1"
    with pytest.raises(ValidationError, match="outside exercise context"):
        Exercise.model_validate(data)


def test_rect_cannot_extend_off_page() -> None:
    with pytest.raises(ValidationError, match="extends beyond"):
        NormalizedRect(x=0.9, y=0.1, width=0.2, height=0.2)


def test_difficulty_is_required() -> None:
    data = _exercise()
    del data["questions"][0]["difficulty"]
    with pytest.raises(ValidationError):
        Exercise.model_validate(data)


def test_question_category_uses_controlled_taxonomy() -> None:
    data = _exercise()
    data["questions"][0]["category"] = "miscellaneous"

    with pytest.raises(ValidationError, match="component_identification"):
        Exercise.model_validate(data)


def test_vehicle_metadata_is_rejected() -> None:
    data = _exercise()
    data["vehicle"] = {"make": "Ford", "model": "Falcon", "years": [1967]}

    with pytest.raises(ValidationError, match="put relevant details in the question prompt"):
        Exercise.model_validate(data)


def test_ordered_part_path_tracks_instances_and_repeat_passes() -> None:
    answer = AnswerSpec.model_validate(
        {
            "type": "ordered_part_path",
            "item_family": "basic",
            "value": [
                {"part_number": "2471", "instance": 1, "pass": 1},
                {"part_number": "01508", "instance": 1, "pass": 1},
                {"part_number": "2471", "instance": 2, "pass": 1},
                {"part_number": "01508", "instance": 1, "pass": 2},
            ],
        }
    )
    assert answer.value[-1] == {"part_number": "01508", "instance": 1, "pass": 2}


def test_ordered_part_path_rejects_out_of_order_passes() -> None:
    with pytest.raises(ValidationError, match="passes must appear in order; expected pass 1"):
        AnswerSpec.model_validate(
            {
                "type": "ordered_part_path",
                "value": [{"part_number": "01508", "instance": 1, "pass": 2}],
            }
        )


def test_ordered_part_path_rejects_out_of_order_new_instances() -> None:
    with pytest.raises(ValidationError, match="new instances must appear in order"):
        AnswerSpec.model_validate(
            {
                "type": "ordered_part_path",
                "value": [{"part_number": "2471", "instance": 2, "pass": 1}],
            }
        )


def test_short_text_rubric_validates_criteria_and_matchers() -> None:
    answer = AnswerSpec.model_validate(
        {
            "type": "short_text",
            "value": "Only in kit 3A187",
            "grading": {
                "method": "rubric",
                "criteria": [
                    {
                        "id": "meaning",
                        "description": "States that the part is kit-only.",
                        "points": 0.6,
                        "grader": {"type": "semantic"},
                    },
                    {
                        "id": "kit",
                        "description": "Names kit 3A187.",
                        "points": 0.4,
                        "grader": {
                            "type": "contains_part_number",
                            "value": "3A187",
                            "family": "basic",
                        },
                    },
                ],
                "calibration_cases": [{"response": "Only sold in the kit.", "expected_score": 0.6}],
            },
        }
    )

    assert answer.grading is not None
    assert answer.grading.criteria[1].grader.value == "3A187"
    assert answer.grading.calibration_cases[0].expected_score == 0.6


def test_rubric_rejects_duplicate_ids_and_non_text_answers() -> None:
    duplicate = {
        "method": "rubric",
        "criteria": [
            {"id": "same", "description": "First criterion.", "points": 1},
            {"id": "same", "description": "Second criterion.", "points": 1},
        ],
    }
    with pytest.raises(ValidationError, match="criterion IDs must be unique"):
        AnswerSpec.model_validate({"type": "short_text", "value": "answer", "grading": duplicate})
    with pytest.raises(ValidationError, match="only for short_text"):
        AnswerSpec.model_validate(
            {
                "type": "integer",
                "value": 1,
                "grading": {
                    "method": "rubric",
                    "criteria": [
                        {"id": "meaning", "description": "A valid criterion.", "points": 1}
                    ],
                },
            }
        )


def test_load_exercises_ignores_recovery_trash(tmp_path) -> None:
    active = tmp_path / "active.yaml"
    trash = tmp_path / ".trash"
    trash.mkdir()
    serialized = yaml.safe_dump(_exercise(), sort_keys=False)
    active.write_text(serialized, encoding="utf-8")
    (trash / "archived.yaml").write_text(serialized, encoding="utf-8")

    loaded = load_exercises(tmp_path)

    assert [path for path, _ in loaded] == [active]
