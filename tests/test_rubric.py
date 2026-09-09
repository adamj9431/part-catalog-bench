from typing import Any

from part_catalog_bench.models import AnswerSpec
from part_catalog_bench.providers import ProviderResponse
from part_catalog_bench.rubric import grade_rubric_answer, rubric_semantic_grade_required


def _spec() -> AnswerSpec:
    return AnswerSpec.model_validate(
        {
            "type": "short_text",
            "value": "Only in kit 3A187",
            "grading": {
                "method": "rubric",
                "criteria": [
                    {
                        "id": "meaning",
                        "description": "States that the part is supplied only in a kit.",
                        "points": 1,
                    },
                    {
                        "id": "number",
                        "description": "Names kit 3A187.",
                        "points": 1,
                        "grader": {
                            "type": "contains_part_number",
                            "value": "3A187",
                        },
                    },
                ],
            },
        }
    )


class FakeGrader:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> ProviderResponse:
        self.calls.append(kwargs)
        return ProviderResponse(
            text=(
                '{"criteria_met":true,"explanation":'
                '"The response says the part is kit-only."}'
            ),
            raw={"model": "fixed-grader"},
            response_model="fixed-grader",
            usage={"total_tokens": 20},
        )


def test_rubric_grader_calls_model_only_for_semantic_criteria() -> None:
    provider = FakeGrader()
    grading = grade_rubric_answer(
        question_prompt="What does the square mean?",
        predicted="It is only available in kit 3A187.",
        spec=_spec(),
        provider=provider,
        provider_name="openrouter",
        model="fixed-grader",
    )

    assert len(provider.calls) == 1
    assert grading["criteria"][0]["id"] == "meaning"
    assert grading["criteria"][0]["criteria_met"] is True
    assert grading["grader"]["requested_model"] == "fixed-grader"


def test_exact_reference_does_not_require_semantic_grading() -> None:
    assert rubric_semantic_grade_required("Only in kit 3A187.", _spec()) is False
    assert rubric_semantic_grade_required("A paraphrase", _spec()) is True
