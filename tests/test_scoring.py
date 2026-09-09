from part_catalog_bench.models import AnswerSpec, AnswerType, Exercise
from part_catalog_bench.scoring import score_answer, score_predictions


def _rubric_spec() -> AnswerSpec:
    return AnswerSpec.model_validate(
        {
            "type": "short_text",
            "value": "The part is supplied only in kit 3A187",
            "aliases": ["Only available in kit 3A187"],
            "grading": {
                "method": "rubric",
                "criteria": [
                    {
                        "id": "kit_only",
                        "description": "States that the part is supplied only as part of a kit.",
                        "points": 0.6,
                        "grader": {"type": "semantic"},
                    },
                    {
                        "id": "kit_number",
                        "description": "Identifies kit 3A187.",
                        "points": 0.4,
                        "grader": {
                            "type": "contains_part_number",
                            "value": "3A187",
                            "family": "basic",
                        },
                    },
                ],
            },
        }
    )


def test_part_number_separator_tolerance_preserves_finish() -> None:
    spec = AnswerSpec(type="part_number", value="34445-S8", family="standard")
    assert score_answer("34445 S8", spec)["score"] == 1
    assert score_answer("34445-S", spec)["score"] == 0


def test_ordered_list_is_strict_with_partial_diagnostic() -> None:
    spec = AnswerSpec(
        type=AnswerType.ORDERED_LIST,
        value=["33798-S", "2455", "33798-S#2"],
        item_type="part_number",
    )
    result = score_answer(["33798 S", "33798-S#2"], spec)
    assert result["score"] == 0
    assert 0 < result["partial"] < 1


def test_ordered_part_path_distinguishes_instances_from_repeat_passes() -> None:
    spec = AnswerSpec(
        type=AnswerType.ORDERED_PART_PATH,
        item_family="basic",
        value=[
            {"part_number": "2471", "instance": 1, "pass": 1},
            {"part_number": "01508", "instance": 1, "pass": 1},
            {"part_number": "2471", "instance": 2, "pass": 1},
            {"part_number": "01508", "instance": 1, "pass": 2},
        ],
    )
    assert score_answer(spec.value, spec)["score"] == 1
    conflated = [
        {"part_number": "2471", "instance": 1, "pass": 1},
        {"part_number": "01508", "instance": 1, "pass": 1},
        {"part_number": "2471", "instance": 1, "pass": 2},
        {"part_number": "01508", "instance": 2, "pass": 1},
    ]
    result = score_answer(conflated, spec)
    assert result["score"] == 0
    assert result["partial"] == 0.5


def test_rubric_exact_alias_receives_full_credit_without_semantic_grade() -> None:
    result = score_answer("Only available in kit 3A187.", _rubric_spec())

    assert result["score"] == 1.0
    assert result["strict"] == 1.0
    assert {item["source"] for item in result["criteria"]} == {"exact_or_alias"}


def test_rubric_combines_semantic_and_deterministic_partial_credit() -> None:
    spec = _rubric_spec()
    semantic_only = score_answer(
        "It is available only as part of a kit.",
        spec,
        {
            "criteria": [
                {
                    "id": "kit_only",
                    "criteria_met": True,
                    "explanation": "It clearly says the part is kit-only.",
                }
            ]
        },
    )
    kit_number_only = score_answer(
        "It is included in kit 3 A 187.",
        spec,
        {
            "criteria": [
                {
                    "id": "kit_only",
                    "criteria_met": False,
                    "explanation": "It does not say the part is unavailable separately.",
                }
            ]
        },
    )

    assert semantic_only["score"] == 0.6
    assert semantic_only["strict"] == 0.0
    assert kit_number_only["score"] == 0.4
    assert kit_number_only["strict"] == 0.0


def test_missing_semantic_grade_is_a_scoring_error_not_a_silent_failure() -> None:
    result = score_answer("It belongs to kit 3A187.", _rubric_spec())

    assert result["score"] == 0.4
    assert result["scoring_error"] is True
    assert "semantic rubric grade missing" in result["errors"][0]


def test_candidate_error_on_rubric_question_scores_zero_without_invalidating_run() -> None:
    exercise = Exercise.model_validate(
        {
            "id": "candidate-error",
            "status": "ready",
            "title": "Candidate error",
            "source_id": "ford-car-master-1960-68",
            "context": {"catalog_refs": ["illustrations:24-2"]},
            "questions": [
                {
                    "id": "q1",
                    "prompt": "Explain the function.",
                    "category": "functional_reasoning",
                    "difficulty": "hard",
                    "answer": _rubric_spec().model_dump(mode="json"),
                }
            ],
        }
    )
    scored = score_predictions(
        [exercise],
        [
            {
                "exercise_id": exercise.id,
                "question_id": "q1",
                "answer": None,
                "error": "IncompleteResponseError: no final answer",
            }
        ],
    )

    assert scored["summary"]["headline_score"] == 0.0
    assert scored["summary"]["scoring_errors"] == 0
    assert scored["summary"]["valid_for_comparison"] is True
    assert scored["questions"][0]["error"] == "IncompleteResponseError: no final answer"


def test_results_are_aggregated_by_difficulty() -> None:
    exercise = Exercise.model_validate(
        {
            "id": "difficulty",
            "status": "ready",
            "title": "Difficulty report",
            "source_id": "ford-car-master-1960-68",
            "context": {"catalog_refs": ["illustrations:24-2"]},
            "questions": [
                {
                    "id": "easy",
                    "prompt": "Read the number.",
                    "category": "component_identification",
                    "difficulty": "easy",
                    "answer": {"type": "part_number", "value": "2455", "family": "basic"},
                },
                {
                    "id": "hard",
                    "prompt": "Trace the assembly.",
                    "category": "assembly_stack_tracing",
                    "difficulty": "hard",
                    "answer": {"type": "integer", "value": 3},
                },
            ],
        }
    )
    scores = score_predictions(
        [exercise],
        [
            {"exercise_id": "difficulty", "question_id": "easy", "answer": "2455"},
            {"exercise_id": "difficulty", "question_id": "hard", "answer": 2},
        ],
    )
    assert scores["by_difficulty"]["easy"]["score"] == 1
    assert scores["by_difficulty"]["hard"]["score"] == 0


def test_headline_is_question_weighted_and_difficulty_balance_is_secondary() -> None:
    short_exercise = Exercise.model_validate(
        {
            "id": "short",
            "status": "ready",
            "title": "One question",
            "source_id": "ford-car-master-1960-68",
            "context": {"catalog_refs": ["illustrations:24-2"]},
            "questions": [
                {
                    "id": "easy",
                    "prompt": "Read the number.",
                    "category": "component_identification",
                    "difficulty": "easy",
                    "answer": {"type": "integer", "value": 1},
                }
            ],
        }
    )
    long_exercise = Exercise.model_validate(
        {
            "id": "long",
            "status": "ready",
            "title": "Three questions",
            "source_id": "ford-car-master-1960-68",
            "context": {"catalog_refs": ["illustrations:30-18"]},
            "questions": [
                {
                    "id": "medium-1",
                    "prompt": "Read the first number.",
                    "category": "component_identification",
                    "difficulty": "medium",
                    "answer": {"type": "integer", "value": 1},
                },
                {
                    "id": "medium-2",
                    "prompt": "Read the second number.",
                    "category": "component_identification",
                    "difficulty": "medium",
                    "answer": {"type": "integer", "value": 1},
                },
                {
                    "id": "hard",
                    "prompt": "Trace the path.",
                    "category": "assembly_stack_tracing",
                    "difficulty": "hard",
                    "answer": {"type": "integer", "value": 1},
                },
            ],
        }
    )
    predictions = [
        {"exercise_id": "short", "question_id": "easy", "answer": 1},
        {"exercise_id": "long", "question_id": "medium-1", "answer": 0},
        {"exercise_id": "long", "question_id": "medium-2", "answer": 0},
        {"exercise_id": "long", "question_id": "hard", "answer": 1},
    ]

    scores = score_predictions([short_exercise, long_exercise], predictions)
    summary = scores["summary"]

    assert summary["headline_score"] == 0.5
    assert summary["question_weighted_score"] == 0.5
    assert summary["macro_exercise_score"] == 2 / 3
    assert summary["difficulty_balanced_score"] == 2 / 3
    assert scores["by_difficulty"]["easy"]["score"] == 1
    assert scores["by_difficulty"]["medium"]["score"] == 0
    assert scores["by_difficulty"]["hard"]["score"] == 1
    assert summary["bootstrap_95_ci"] == [1 / 3, 1.0]


def test_question_weights_apply_to_headline_and_group_scores() -> None:
    exercise = Exercise.model_validate(
        {
            "id": "weighted",
            "status": "ready",
            "title": "Weighted questions",
            "source_id": "ford-car-master-1960-68",
            "context": {"catalog_refs": ["illustrations:24-2"]},
            "questions": [
                {
                    "id": "correct",
                    "prompt": "Read the first number.",
                    "category": "component_identification",
                    "difficulty": "easy",
                    "answer": {"type": "integer", "value": 1},
                    "weight": 1,
                },
                {
                    "id": "incorrect",
                    "prompt": "Read the second number.",
                    "category": "component_identification",
                    "difficulty": "easy",
                    "answer": {"type": "integer", "value": 1},
                    "weight": 3,
                },
            ],
        }
    )
    scores = score_predictions(
        [exercise],
        [
            {"exercise_id": "weighted", "question_id": "correct", "answer": 1},
            {"exercise_id": "weighted", "question_id": "incorrect", "answer": 0},
        ],
    )

    assert scores["summary"]["question_weighted_score"] == 0.25
    assert scores["by_difficulty"]["easy"]["score"] == 0.25
    assert scores["summary"]["bootstrap_95_ci"] == [0.25, 0.25]
