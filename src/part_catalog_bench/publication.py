"""Deliberately small, aggregate-only exports for the public results site."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from .dataset import load_dataset_snapshot
from .models import QuestionCategory
from .social_preview import render_social_preview
from .util import read_jsonl, write_json


def public_run(run_dir: Path) -> dict:
    config = json.loads((run_dir / "run.json").read_text())
    scores = json.loads((run_dir / "scores.json").read_text())
    summary = scores["summary"]
    dataset = config["dataset"]
    fingerprint = dataset["sha256"]
    exercises = load_dataset_snapshot(run_dir / dataset["snapshot_file"], fingerprint)
    expected = {(e.id, q.id) for e in exercises for q in e.questions}
    predictions = read_jsonl(run_dir / "predictions.jsonl")
    actual = [(p.get("exercise_id"), p.get("question_id")) for p in predictions]
    scored = [(q["exercise_id"], q["question_id"]) for q in scores["questions"]]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError(f"{run_dir.name}: incomplete or duplicate predictions")
    if set(scored) != expected or len(scored) != len(expected):
        raise ValueError(f"{run_dir.name}: scores do not cover the frozen dataset")
    if (
        not summary.get("valid_for_comparison")
        or scores["dataset"].get("verification") != "verified"
        or scores["dataset"].get("scoring_sha256") != fingerprint
        or scores["run"]["model"] != config["model"]
    ):
        raise ValueError(f"{run_dir.name}: invalid or mismatched scores; score the run again")

    def groups(key: str, allowed: set[str]) -> dict:
        # Suppress small slices, and never copy arbitrary group labels or details.
        return {
            name: {"questions": int(row["questions"]), "score": float(row["score"])}
            for name, row in scores[key].items()
            if name in allowed and row["questions"] >= 5
        }

    candidate = scores["metrics"]["candidate"]
    cost = candidate["cost"]
    grader_cost = scores["metrics"]["grader"]["cost"]
    failed = sum(bool(p.get("error")) for p in predictions)
    # Construct every field explicitly: full scores, provider payloads, source
    # paths, private exercise IDs, answers and rubric criteria must never escape.
    return {
        "model": str(config["model"]),
        "provider": str(config["provider"]),
        "assembled_at": config["created_at"],
        "dataset_sha256": fingerprint,
        "questions": len(expected),
        "exercises": len(exercises),
        "score": float(summary["headline_score"]),
        "ci95": [float(v) for v in summary["bootstrap_95_ci"]],
        "partial_score": float(summary["diagnostic_partial_accuracy"]),
        "strict_score": float(summary["strict_question_accuracy"]),
        "cost_usd": float(cost["cost_usd"]) if cost.get("complete") else None,
        "reported_cost_usd": float(cost["reported_cost_usd"]),
        "grader_cost_usd": (
            float(grader_cost["cost_usd"]) if grader_cost.get("complete") else None
        ),
        "median_seconds": candidate["latency"].get("median_seconds"),
        "p95_seconds": candidate["latency"].get("p95_seconds"),
        "failed_responses": failed,
        "reused_responses": sum(bool(p.get("reused_from")) for p in predictions),
        "by_difficulty": groups("by_difficulty", {"easy", "medium", "hard"}),
        "by_category": groups("by_category", {c.value for c in QuestionCategory}),
        "settings": {
            "evaluation_mode": config["evaluation_mode"],
            "input_modality": config["input_modality"],
            "max_tokens": config["max_tokens"],
            "reasoning_effort": config.get("reasoning_effort"),
            "temperature": config.get("temperature"),
            "dpi": config["dpi"],
            "timeout_seconds": config["timeout"],
            "retries": config["retries"],
            "grader_model": config["grader"]["model"],
            "grader_max_tokens": config["grader"]["max_tokens"],
            "grader_reasoning_effort": config["grader"].get("reasoning_effort"),
        },
    }


def export_site(run_dirs: list[Path], output: Path, release: str) -> Path:
    if not run_dirs:
        raise ValueError("select at least one completed, scored run")
    rows = [public_run(p) for p in run_dirs]
    if len({r["dataset_sha256"] for r in rows}) != 1:
        raise ValueError("a leaderboard must use one dataset fingerprint")
    if len({r["model"] for r in rows}) != len(rows):
        raise ValueError("select one run per model")
    if any(r["settings"] != rows[0]["settings"] for r in rows[1:]):
        raise ValueError("candidate runs use different evaluation settings")
    rows.sort(key=lambda row: (-row["score"], row["model"]))
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "results.json"
    render_social_preview(rows, output / "pareto-preview.png")
    write_json(destination, {
        "schema_version": 1,
        "release": release,
        "exported_at": datetime.now(UTC).isoformat(),
        "scope": (
            "These results cover the full pilot. "
            "A separate public demo and private test set are planned."
        ),
        "models": rows,
    })
    fields = [
        "model", "provider", "questions", "exercises", "score", "ci95_low", "ci95_high",
        "partial_score", "cost_usd", "grader_cost_usd", "median_seconds", "p95_seconds",
        "failed_responses", "reused_responses", "assembled_at", "dataset_sha256",
    ]
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            record = {k: row.get(k) for k in fields}
            record.update(ci95_low=row["ci95"][0], ci95_high=row["ci95"][1])
            # Spreadsheet applications must not interpret model metadata as formulas.
            writer.writerow({
                k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@"))
                else v for k, v in record.items()
            })
    return destination
