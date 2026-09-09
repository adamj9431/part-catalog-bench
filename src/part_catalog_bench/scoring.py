from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from .ford_numbers import normalize_number_with_occurrence, normalize_part_number
from .models import (
    AnswerSpec,
    AnswerType,
    Exercise,
    PartPathStep,
    RubricCriterionGraderType,
)


def _normalize_text(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,:;\"'")


def _normalize_date(value: Any) -> str | None:
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})", text)
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    if year < 100:
        year += 1900 if year >= 50 else 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _normalize_boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = _normalize_text(value)
    if text in {"yes", "true", "1"}:
        return True
    if text in {"no", "false", "0"}:
        return False
    return None


def _normalize_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"[+-]?\d+", str(value).strip().replace(",", ""))
    return int(match.group()) if match else None


def _normalize_scalar(value: Any, spec: AnswerSpec) -> Any:
    if spec.type == AnswerType.PART_NUMBER:
        return normalize_part_number(str(value), spec.family)
    if spec.type == AnswerType.INTEGER:
        return _normalize_integer(value)
    if spec.type == AnswerType.DATE:
        return _normalize_date(value)
    if spec.type == AnswerType.BOOLEAN:
        return _normalize_boolean(value)
    return _normalize_text(value)


def _normalize_list_item(value: Any, spec: AnswerSpec) -> Any:
    item_type = spec.item_type or AnswerType.PART_NUMBER
    if item_type == AnswerType.PART_NUMBER:
        return normalize_number_with_occurrence(str(value), spec.item_family)
    item_spec = AnswerSpec(type=item_type, value=value, family=spec.item_family)
    return _normalize_scalar(value, item_spec)


def _coerce_list(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [part.strip() for part in re.split(r"\n|;", stripped) if part.strip()]
    return None


def _normalize_part_path(value: Any, spec: AnswerSpec) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    normalized = []
    try:
        for item in value:
            step = PartPathStep.model_validate(item)
            normalized.append(
                {
                    "part_number": normalize_part_number(step.part_number, spec.item_family),
                    "instance": step.instance,
                    "pass": step.pass_number,
                }
            )
    except Exception:
        return None
    return normalized


def _lcs_length(left: list[Any], right: list[Any]) -> int:
    previous = [0] * (len(right) + 1)
    for left_item in left:
        current = [0]
        for index, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(current[-1], previous[index]))
        previous = current
    return previous[-1]


def _contains_part_number(predicted: Any, expected: str, family: Any) -> bool:
    compact = normalize_part_number(expected, family)
    pattern = r"(?<![A-Z0-9])" + r"[\s-]*".join(map(re.escape, compact)) + r"(?![A-Z0-9])"
    return bool(re.search(pattern, str(predicted).upper()))


def _score_rubric(
    predicted: Any, spec: AnswerSpec, grading: dict[str, Any] | None
) -> dict[str, Any]:
    assert spec.grading is not None
    candidates = [spec.value, *spec.aliases]
    expected_values = [_normalize_text(value) for value in candidates]
    actual = _normalize_text(predicted) if predicted is not None else None
    if actual in expected_values:
        criteria = [
            {
                "id": criterion.id,
                "points": criterion.points,
                "required": criterion.required,
                "grader_type": criterion.grader.type.value,
                "criteria_met": True,
                "explanation": "Matched the canonical answer or an accepted alternative.",
                "source": "exact_or_alias",
            }
            for criterion in spec.grading.criteria
        ]
        return {
            "score": 1.0,
            "strict": 1.0,
            "partial": 1.0,
            "grading_method": "rubric",
            "criteria": criteria,
            "expected_normalized": expected_values,
            "predicted_normalized": actual,
        }

    semantic_results = {
        item.get("id"): item for item in (grading or {}).get("criteria", []) if item.get("id")
    }
    criteria = []
    errors = []
    earned = 0.0
    total = sum(criterion.points for criterion in spec.grading.criteria)
    required_met = True
    for criterion in spec.grading.criteria:
        if criterion.grader.type == RubricCriterionGraderType.CONTAINS_PART_NUMBER:
            met = _contains_part_number(
                predicted, criterion.grader.value or "", criterion.grader.family
            )
            result = {
                "criteria_met": met,
                "explanation": (
                    f"Response contains part number {criterion.grader.value}."
                    if met
                    else f"Response does not contain part number {criterion.grader.value}."
                ),
                "source": "deterministic",
            }
        else:
            stored = semantic_results.get(criterion.id)
            if not stored or not isinstance(stored.get("criteria_met"), bool):
                error = (stored or {}).get("error") or (
                    f"semantic rubric grade missing for criterion {criterion.id}"
                )
                errors.append(error)
                met = False
                result = {
                    "criteria_met": False,
                    "explanation": "Criterion could not be graded.",
                    "source": "semantic",
                    "error": error,
                }
            else:
                met = stored["criteria_met"]
                result = {
                    **stored,
                    "source": "semantic",
                }
        if met:
            earned += criterion.points
        if criterion.required and not met:
            required_met = False
        criteria.append(
            {
                "id": criterion.id,
                "description": criterion.description,
                "points": criterion.points,
                "required": criterion.required,
                "grader_type": criterion.grader.type.value,
                **result,
            }
        )
    score = earned / total
    strict = float(required_met and not errors)
    return {
        "score": score,
        "strict": strict,
        "partial": score,
        "grading_method": "rubric",
        "criteria": criteria,
        "expected_normalized": expected_values,
        "predicted_normalized": actual,
        "scoring_error": bool(errors),
        "errors": errors,
    }


def score_answer(
    predicted: Any, spec: AnswerSpec, grading: dict[str, Any] | None = None
) -> dict[str, Any]:
    if spec.grading is not None:
        return _score_rubric(predicted, spec, grading)
    if spec.type == AnswerType.COMPOUND:
        if not isinstance(predicted, dict):
            return {"score": 0.0, "strict": 0.0, "fields": {}, "reason": "expected object"}
        field_scores = {
            name: score_answer(predicted.get(name), field_spec)
            for name, field_spec in spec.fields.items()
        }
        score = sum(item["score"] for item in field_scores.values()) / len(field_scores)
        strict = float(all(item["strict"] == 1.0 for item in field_scores.values()))
        return {"score": score, "strict": strict, "fields": field_scores}

    if spec.type == AnswerType.ORDERED_PART_PATH:
        expected = _normalize_part_path(spec.value, spec)
        actual = _normalize_part_path(predicted, spec)
        if actual is None or expected is None:
            return {
                "score": 0.0,
                "strict": 0.0,
                "partial": 0.0,
                "reason": "expected an array of {part_number, instance, pass} objects",
            }
        expected_tokens = [
            (item["part_number"], item["instance"], item["pass"]) for item in expected
        ]
        actual_tokens = [
            (item["part_number"], item["instance"], item["pass"]) for item in actual
        ]
        strict = float(actual_tokens == expected_tokens)
        partial = _lcs_length(actual_tokens, expected_tokens) / max(
            len(actual_tokens), len(expected_tokens), 1
        )
        return {
            "score": strict,
            "strict": strict,
            "partial": partial,
            "expected_normalized": expected,
            "predicted_normalized": actual,
        }

    if spec.type in {AnswerType.ORDERED_LIST, AnswerType.UNORDERED_SET}:
        predicted_list = _coerce_list(predicted)
        if predicted_list is None:
            return {"score": 0.0, "strict": 0.0, "partial": 0.0, "reason": "expected list"}
        expected = [_normalize_list_item(value, spec) for value in spec.value]
        actual = [_normalize_list_item(value, spec) for value in predicted_list]
        if spec.type == AnswerType.ORDERED_LIST:
            strict = float(actual == expected)
            lcs = _lcs_length(actual, expected)
            partial = lcs / max(len(actual), len(expected), 1)
            return {
                "score": strict,
                "strict": strict,
                "partial": partial,
                "expected_normalized": expected,
                "predicted_normalized": actual,
            }
        expected_counter = Counter(expected)
        actual_counter = Counter(actual)
        overlap = sum((expected_counter & actual_counter).values())
        precision = overlap / len(actual) if actual else float(not expected)
        recall = overlap / len(expected) if expected else float(not actual)
        partial = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        strict = float(actual_counter == expected_counter)
        return {
            "score": strict,
            "strict": strict,
            "partial": partial,
            "precision": precision,
            "recall": recall,
            "expected_normalized": expected,
            "predicted_normalized": actual,
        }

    candidates = [spec.value, *spec.aliases]
    expected_values = [_normalize_scalar(value, spec) for value in candidates]
    actual = _normalize_scalar(predicted, spec) if predicted is not None else None
    strict = float(actual in expected_values)
    return {
        "score": strict,
        "strict": strict,
        "expected_normalized": expected_values,
        "predicted_normalized": actual,
    }


def score_predictions(
    exercises: list[Exercise], predictions: list[dict[str, Any]]
) -> dict[str, Any]:
    prediction_map = {(row.get("exercise_id"), row.get("question_id")): row for row in predictions}
    question_rows: list[dict[str, Any]] = []
    exercise_rows: list[dict[str, Any]] = []

    for exercise in exercises:
        weighted_total = 0.0
        weight_total = 0.0
        strict_total = 0.0
        partial_total = 0.0
        for question in exercise.questions:
            prediction = prediction_map.get((exercise.id, question.id), {})
            if prediction.get("error"):
                # Candidate/provider failures are benchmark outcomes, not scoring
                # failures. In particular, rubric answers without model output
                # cannot have semantic grader records and should receive zero
                # without invalidating the full run.
                result = {
                    "score": 0.0,
                    "strict": 0.0,
                    "partial": 0.0,
                    "predicted_normalized": None,
                    "candidate_error": True,
                }
            else:
                result = score_answer(
                    prediction.get("answer"), question.answer, prediction.get("grading")
                )
            partial = result.get("partial", result["score"])
            row = {
                "exercise_id": exercise.id,
                "question_id": question.id,
                "category": question.category,
                "difficulty": question.difficulty.value,
                "answer_type": question.answer.type.value,
                "weight": question.weight,
                "score": result["score"],
                "strict": result["strict"],
                "partial": partial,
                "missing": not bool(prediction),
                "error": prediction.get("error") or "; ".join(result.get("errors", [])) or None,
                "scoring_error": bool(result.get("scoring_error")),
                "details": result,
            }
            question_rows.append(row)
            weighted_total += result["score"] * question.weight
            weight_total += question.weight
            strict_total += result["strict"]
            partial_total += partial
        count = len(exercise.questions)
        exercise_rows.append(
            {
                "exercise_id": exercise.id,
                "title": exercise.title,
                "questions": count,
                "score": weighted_total / weight_total,
                "strict_accuracy": strict_total / count,
                "partial_accuracy": partial_total / count,
            }
        )

    macro_exercise = (
        sum(row["score"] for row in exercise_rows) / len(exercise_rows) if exercise_rows else 0.0
    )
    question_weight_total = sum(row["weight"] for row in question_rows)
    question_weighted = (
        sum(row["score"] * row["weight"] for row in question_rows) / question_weight_total
        if question_weight_total
        else 0.0
    )
    strict = (
        sum(row["strict"] for row in question_rows) / len(question_rows) if question_rows else 0.0
    )
    partial = (
        sum(row["partial"] for row in question_rows) / len(question_rows) if question_rows else 0.0
    )
    scoring_errors = sum(bool(row["scoring_error"]) for row in question_rows)
    by_difficulty = aggregate(question_rows, "difficulty")
    difficulty_balanced = (
        sum(group["score"] for group in by_difficulty.values()) / len(by_difficulty)
        if by_difficulty
        else 0.0
    )
    ci_low, ci_high = bootstrap_clustered_question_ci(question_rows)
    return {
        "summary": {
            "exercises": len(exercise_rows),
            "questions": len(question_rows),
            "headline_score": question_weighted,
            "question_weighted_score": question_weighted,
            "difficulty_balanced_score": difficulty_balanced,
            "macro_exercise_score": macro_exercise,
            "micro_question_score": question_weighted,
            "strict_question_accuracy": strict,
            "diagnostic_partial_accuracy": partial,
            "scoring_errors": scoring_errors,
            "valid_for_comparison": scoring_errors == 0,
            "bootstrap_95_ci": [ci_low, ci_high],
        },
        "by_difficulty": by_difficulty,
        "by_category": aggregate(question_rows, "category"),
        "by_answer_type": aggregate(question_rows, "answer_type"),
        "exercises": exercise_rows,
        "questions": question_rows,
    }


def aggregate(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {
        key: {
            "questions": len(items),
            "score": sum(item["score"] * item["weight"] for item in items)
            / sum(item["weight"] for item in items),
            "strict_accuracy": sum(item["strict"] for item in items) / len(items),
            "partial_accuracy": sum(item["partial"] for item in items) / len(items),
        }
        for key, items in sorted(groups.items())
    }


def bootstrap_clustered_question_ci(
    rows: list[dict[str, Any]], *, samples: int = 1000, seed: int = 42
) -> tuple[float, float]:
    """Bootstrap the question-weighted score while keeping exercises intact."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["exercise_id"])].append(row)
    clusters = list(grouped.values())
    if not clusters:
        return 0.0, 0.0

    def weighted_score(sampled_clusters: list[list[dict[str, Any]]]) -> float:
        sampled_rows = [row for cluster in sampled_clusters for row in cluster]
        total_weight = sum(row["weight"] for row in sampled_rows)
        return (
            sum(row["score"] * row["weight"] for row in sampled_rows) / total_weight
            if total_weight
            else 0.0
        )

    if len(clusters) == 1:
        score = weighted_score(clusters)
        return score, score

    generator = random.Random(seed)
    scores = []
    for _ in range(samples):
        sampled = [generator.choice(clusters) for _ in clusters]
        scores.append(weighted_score(sampled))
    scores.sort()
    low_index = math.floor(0.025 * (samples - 1))
    high_index = math.ceil(0.975 * (samples - 1))
    return scores[low_index], scores[high_index]


def bootstrap_ci(
    values: list[float], *, samples: int = 1000, seed: int = 42
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    generator = random.Random(seed)
    means = []
    for _ in range(samples):
        sample = [generator.choice(values) for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    low_index = math.floor(0.025 * (samples - 1))
    high_index = math.ceil(0.975 * (samples - 1))
    return means[low_index], means[high_index]
