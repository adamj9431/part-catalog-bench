from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

from .dataset import exercise_fingerprint, load_dataset_snapshot
from .models import Exercise, load_exercises
from .scoring import score_predictions
from .util import read_jsonl, write_json


def _selected_exercises(path: Path, selected_ids: set[str]) -> list[Exercise]:
    return [
        exercise
        for _, exercise in load_exercises(path)
        if not selected_ids or exercise.id in selected_ids
    ]


def _load_scoring_dataset(
    run_dir: Path, config: dict[str, Any], exercises_path: Path | None
) -> tuple[list[Exercise], dict[str, Any]]:
    selected_ids = set(config.get("exercise_ids") or [])
    run_dataset = config.get("dataset") or {}
    expected = run_dataset.get("sha256")
    if exercises_path is not None:
        exercises = _selected_exercises(exercises_path, selected_ids)
        actual = exercise_fingerprint(exercises)
        matches = actual == expected if expected else None
        return exercises, {
            **run_dataset,
            "scoring_source": "exercise_override",
            "scoring_sha256": actual,
            "verification": "verified" if matches else "mismatch" if expected else "unavailable",
        }
    snapshot_file = run_dataset.get("snapshot_file")
    if snapshot_file and expected:
        exercises = load_dataset_snapshot(run_dir / snapshot_file, expected)
        return exercises, {
            **run_dataset,
            "scoring_source": "run_snapshot",
            "scoring_sha256": expected,
            "verification": "verified",
        }
    exercise_location = Path(config["exercises_path"])
    exercises = _selected_exercises(exercise_location, selected_ids)
    return exercises, {
        "scoring_source": "live_exercises_legacy_run",
        "scoring_sha256": exercise_fingerprint(exercises),
        "verification": "unavailable",
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _first_number(mapping: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _number(mapping.get(key))
        if value is not None:
            return value
    return None


def _nested_number(mapping: dict[str, Any], groups: tuple[str, ...], key: str) -> float | None:
    for group in groups:
        details = mapping.get(group)
        if isinstance(details, dict):
            value = _number(details.get(key))
            if value is not None:
                return value
    return None


def _usage_record(usage: Any) -> dict[str, float | None]:
    usage = usage if isinstance(usage, dict) else {}
    input_tokens = _first_number(usage, "prompt_tokens", "input_tokens")
    output_tokens = _first_number(usage, "completion_tokens", "output_tokens")
    total_tokens = _first_number(usage, "total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    reasoning_tokens = _first_number(usage, "reasoning_tokens")
    if reasoning_tokens is None:
        reasoning_tokens = _nested_number(
            usage,
            ("completion_tokens_details", "output_tokens_details"),
            "reasoning_tokens",
        )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cached_tokens": _nested_number(
            usage,
            ("prompt_tokens_details", "input_tokens_details"),
            "cached_tokens",
        ),
        "cost_usd": _first_number(usage, "cost", "cost_usd"),
    }


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "reported_requests": 0,
            "total_seconds": None,
            "mean_seconds": None,
            "median_seconds": None,
            "p95_seconds": None,
            "min_seconds": None,
            "max_seconds": None,
        }
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "reported_requests": len(values),
        "total_seconds": sum(values),
        "mean_seconds": statistics.fmean(values),
        "median_seconds": statistics.median(values),
        "p95_seconds": ordered[p95_index],
        "min_seconds": ordered[0],
        "max_seconds": ordered[-1],
    }


def _workload_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    usage_records = [_usage_record(record.get("usage")) for record in records]
    costs = [item["cost_usd"] for item in usage_records if item["cost_usd"] is not None]
    latencies = [
        value
        for record in records
        if (value := _number(record.get("latency_seconds"))) is not None
    ]

    def token_total(key: str) -> float | int | None:
        values = [item[key] for item in usage_records if item[key] is not None]
        if not values:
            return None
        total = sum(values)
        return int(total) if total.is_integer() else total

    request_count = len(records)
    cost_complete = len(costs) == request_count
    reported_cost = sum(costs)
    return {
        "requests": request_count,
        "successful_requests": sum(not record.get("error") for record in records),
        "failed_requests": sum(bool(record.get("error")) for record in records),
        "cost": {
            "cost_usd": reported_cost if cost_complete else None,
            "reported_cost_usd": reported_cost,
            "reported_requests": len(costs),
            "unreported_requests": request_count - len(costs),
            "complete": cost_complete,
        },
        "tokens": {
            "input": token_total("input_tokens"),
            "output": token_total("output_tokens"),
            "total": token_total("total_tokens"),
            "reasoning": token_total("reasoning_tokens"),
            "cached": token_total("cached_tokens"),
            "reported_requests": sum(item["total_tokens"] is not None for item in usage_records),
            "unreported_requests": sum(item["total_tokens"] is None for item in usage_records),
        },
        "latency": {
            **_latency_summary(latencies),
            "unreported_requests": request_count - len(latencies),
        },
    }


def aggregate_run_metrics(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_records = [
        {
            "usage": prediction.get("usage"),
            "latency_seconds": prediction.get("latency_seconds"),
            "error": prediction.get("error"),
        }
        for prediction in predictions
    ]
    grader_records = []
    for prediction in predictions:
        grading = prediction.get("grading")
        if not isinstance(grading, dict):
            continue
        for criterion in grading.get("criteria") or []:
            if not isinstance(criterion, dict):
                continue
            # Only semantic criteria that actually attempted a provider call have these fields.
            if not any(
                key in criterion
                for key in ("usage", "latency_seconds", "raw_response", "response_model", "error")
            ):
                continue
            grader_records.append(
                {
                    "usage": criterion.get("usage"),
                    "latency_seconds": criterion.get("latency_seconds"),
                    "error": criterion.get("error"),
                }
            )
    candidate = _workload_metrics(candidate_records)
    grader = _workload_metrics(grader_records)
    combined = _workload_metrics([*candidate_records, *grader_records])
    return {"candidate": candidate, "grader": grader, "combined": combined}


def score_run(run_dir: Path, exercises_path: Path | None = None) -> dict[str, Any]:
    config_path = run_dir / "run.json"
    if not config_path.exists():
        raise FileNotFoundError(f"run configuration not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    exercises, dataset = _load_scoring_dataset(run_dir, config, exercises_path)
    predictions = read_jsonl(run_dir / "predictions.jsonl")
    scores = score_predictions(exercises, predictions)
    if dataset["verification"] != "verified":
        scores["summary"]["valid_for_comparison"] = False
        message = (
            "scoring exercise fingerprint does not match the dataset used for the run"
            if dataset["verification"] == "mismatch"
            else "run predates frozen dataset snapshots; dataset identity cannot be verified"
        )
        scores["summary"].setdefault("validation_errors", []).append(message)
    scores["run"] = {
        "run_id": config.get("run_id", run_dir.name),
        "provider": config.get("provider"),
        "model": config.get("model"),
        "evaluation_mode": config.get("evaluation_mode"),
        "input_modality": config.get("input_modality"),
        "reasoning_effort": config.get("reasoning_effort"),
        "max_tokens": config.get("max_tokens"),
        "grader": config.get("grader"),
    }
    scores["dataset"] = dataset
    scores["metrics"] = aggregate_run_metrics(predictions)
    write_json(run_dir / "scores.json", scores)
    return scores


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _integer(value: Any) -> str:
    return "—" if value is None else f"{value:,.0f}"


def _seconds(value: Any) -> str:
    return "—" if value is None else f"{value:,.2f} s"


def _cost(cost: dict[str, Any]) -> str:
    if cost.get("complete"):
        return f"${cost.get('cost_usd', 0.0):,.4f}"
    reported = cost.get("reported_cost_usd", 0.0)
    return f"${reported:,.4f} reported (incomplete)"


def _efficiency_table(metrics: dict[str, Any]) -> list[str]:
    lines = [
        "## Efficiency",
        "",
        "Costs are shown only when reported by the provider. Latency is the recorded time for "
        "the final candidate attempt and saved semantic-grader calls.",
        "",
        "| Workload | Requests | Cost | Input tokens | Output tokens | Total tokens | "
        "Recorded latency | Mean latency | P95 latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "candidate": "Candidate model",
        "grader": "Rubric grader",
        "combined": "Combined",
    }
    for key, label in labels.items():
        values = metrics.get(key) or {}
        tokens = values.get("tokens") or {}
        latency = values.get("latency") or {}
        lines.append(
            f"| {label} | {values.get('requests', 0)} | {_cost(values.get('cost') or {})} | "
            f"{_integer(tokens.get('input'))} | {_integer(tokens.get('output'))} | "
            f"{_integer(tokens.get('total'))} | {_seconds(latency.get('total_seconds'))} | "
            f"{_seconds(latency.get('mean_seconds'))} | {_seconds(latency.get('p95_seconds'))} |"
        )
    lines.append("")
    return lines


def _breakdown_table(title: str, rows: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| Group | Questions | Primary score | Strict accuracy | Partial diagnostic |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, values in rows.items():
        lines.append(
            f"| {label} | {values['questions']} | {_percent(values['score'])} | "
            f"{_percent(values['strict_accuracy'])} | {_percent(values['partial_accuracy'])} |"
        )
    lines.append("")
    return lines


def write_report(run_dir: Path, scores: dict[str, Any] | None = None) -> Path:
    if scores is None:
        # Re-score from durable predictions so reports never reuse an older scores.json shape.
        scores = score_run(run_dir)
    summary = scores["summary"]
    run = scores.get("run", {})
    dataset = scores.get("dataset", {})
    ci_low, ci_high = summary["bootstrap_95_ci"]
    headline = summary.get(
        "question_weighted_score",
        summary.get("micro_question_score", summary.get("macro_exercise_score", 0.0)),
    )
    difficulty_groups = scores.get("by_difficulty", {})
    difficulty_balanced = summary.get(
        "difficulty_balanced_score",
        (
            sum(group["score"] for group in difficulty_groups.values())
            / len(difficulty_groups)
            if difficulty_groups
            else 0.0
        ),
    )
    lines = [
        "# Benchmark report",
        "",
        f"- Run: `{run.get('run_id', run_dir.name)}`",
        f"- Provider: `{run.get('provider', 'unknown')}`",
        f"- Model: `{run.get('model', 'unknown')}`",
        f"- Reasoning effort: `{run.get('reasoning_effort') or 'provider default'}`",
        f"- Maximum output tokens: {run.get('max_tokens', 'unknown')}",
        f"- Evaluation mode: `{run.get('evaluation_mode', 'unknown')}`",
        f"- Input modality: `{run.get('input_modality', 'unknown')}`",
        "- Dataset fingerprint: `"
        f"{dataset.get('sha256') or dataset.get('scoring_sha256', 'unavailable')}`",
        f"- Dataset verification: `{dataset.get('verification', 'unavailable')}`",
        f"- Exercises: {summary['exercises']}",
        f"- Questions: {summary['questions']}",
        "",
        "## Headline results",
        "",
        f"- Question-weighted score: **{_percent(headline)}**",
        "- 95% exercise-clustered bootstrap interval: "
        f"{_percent(ci_low)}–{_percent(ci_high)}",
        f"- Difficulty-balanced score: {_percent(difficulty_balanced)}",
        f"- Macro exercise score (diagnostic): {_percent(summary['macro_exercise_score'])}",
        f"- Strict question accuracy: {_percent(summary['strict_question_accuracy'])}",
        f"- Diagnostic partial accuracy: {_percent(summary['diagnostic_partial_accuracy'])}",
        f"- Scoring errors: {summary.get('scoring_errors', 0)}",
        f"- Valid for comparison: {'yes' if summary.get('valid_for_comparison', True) else 'no'}",
    ]
    for error in summary.get("validation_errors", []):
        lines.append(f"- Validation issue: {error}")
    lines.append("")
    if metrics := scores.get("metrics"):
        lines.extend(_efficiency_table(metrics))
    lines.extend(_breakdown_table("Results by difficulty", scores["by_difficulty"]))
    lines.extend(_breakdown_table("Results by category", scores["by_category"]))
    lines.extend(_breakdown_table("Results by answer type", scores["by_answer_type"]))
    lines.extend(
        [
            "## Exercise results",
            "",
            "| Exercise | Questions | Score | Partial diagnostic |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in scores["exercises"]:
        lines.append(
            f"| {row['exercise_id']} | {row['questions']} | {_percent(row['score'])} | "
            f"{_percent(row['partial_accuracy'])} |"
        )
    lines.append("")
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
