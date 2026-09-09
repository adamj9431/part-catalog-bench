"""Export only the three approved demo answers; never export provider reasoning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from part_catalog_bench.publication import public_run
from part_catalog_bench.util import read_jsonl

EXERCISE = "ford-illustration-030-018-1967-falcon-suspension"
QUESTIONS = {"attachment": "q06", "hardware": "q02", "assembly": "q01"}
NAMES = {
    "openai/gpt-6-astra": "GPT-6 Astra",
    "anthropic/claude-fable-5.1": "Claude Fable 5.1",
    "openai/gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
    "google/gemini-3.8-flash": "Gemini 3.8 Flash",
    "x-ai/grok-4.6": "Grok 4.6",
    "qwen/qwen3.8-max-0902": "Qwen 3.8 Max 0902",
    "qwen/qwen3.8-flash": "Qwen 3.8 Flash",
    "z-ai/glm-5.3-flash": "GLM 5.3 Flash",
    "bytedance-seed/seed-2-1-turbo": "Seed 2.1 Turbo",
    "deepseek/deepseek-v4-flash-vision-exp": "DeepSeek V4 Vision Exp",
}
# Editorial notes describe observed final answers, not inferred internal reasoning.
ASSEMBLY_NOTES = {
    "openai/gpt-6-astra": (
        "Listed all 13 parts in order, including the separate copies of the washers and bushings."
    ),
    "anthropic/claude-fable-5.1": (
        "Listed only five parts. Omitted most of the stack, including 378866-S, 5482 and 3397, "
        "and added 3368 and 34447-S."
    ),
    "openai/gpt-5.6-sol-pro": (
        "Got the first nine part numbers in order, then gave 3078 instead of 3397 "
        "(lower control arm) and omitted 5A491."
    ),
    "google/gemini-3.8-flash": (
        "Listed 11 parts in the wrong order. Omitted 378866-S, 3397 and 5A491, and added 34447-S."
    ),
    "x-ai/grok-4.6": (
        "Listed only four pieces: two bushings, the spacer and one washer. "
        "Omitted the rest of the 13-part stack."
    ),
    "qwen/qwen3.8-max-0902": (
        "Listed nine parts. Omitted the top nut, stabilizer bar and lower control arm, "
        "included 3368, and put 5A491 near the beginning instead of below the arm."
    ),
    "deepseek/deepseek-v4-flash-vision-exp": (
        "Listed four parts instead of 13. Only 5490 matches a part number in the expected stack; "
        "37169-S is not the required 371169-S."
    ),
}
HARDWARE_NOTES = {
    "openai/gpt-6-astra": "Identified both the nut replacement and the bolt replacement correctly.",
    "anthropic/claude-fable-5.1": (
        "Identified both replacements correctly, including the changeover date."
    ),
    "google/gemini-3.8-flash": (
        "Identified both replacements correctly, including the changeover date."
    ),
    "openai/gpt-5.6-sol-pro": (
        "Identified the nut change but omitted the bolt change from 355471-S to 378940-S. "
        "Earned half credit."
    ),
    "x-ai/grok-4.6": (
        "Gave the two nut numbers in the correct before/after order, but omitted the bolt change. "
        "Earned half credit."
    ),
    "z-ai/glm-5.3-flash": (
        "Identified the change from 33923-S to 34392-S, but omitted the bolt change. "
        "Earned half credit."
    ),
    "qwen/qwen3.8-flash": (
        "Read the nut numbers but called them bolts, and missed the actual bolt replacement. "
        "The saved rubric awarded neither criterion."
    ),
    "bytedance-seed/seed-2-1-turbo": (
        "Read the nut numbers but described them as an attachment bolt, "
        "and omitted the actual bolt replacement. The saved rubric awarded neither criterion."
    ),
    "deepseek/deepseek-v4-flash-vision-exp": (
        "Gave 35547-S and 37940-S rather than the complete bolt numbers 355471-S and 378940-S, "
        "and omitted the nut change."
    ),
}


def export_examples(runs: list[Path], site: Path) -> Path:
    leaderboard = json.loads((site / "data/results.json").read_text())
    verified = {public_run(p)["model"]: p for p in runs}
    if len(verified) != len(runs):
        raise ValueError("Duplicate model runs")
    if set(verified) != {r["model"] for r in leaderboard["models"]}:
        raise ValueError("Example runs must match the current leaderboard exactly")
    output = {key: [] for key in QUESTIONS}
    for model_row in leaderboard["models"]:
        model = model_row["model"]
        path = verified[model]
        if public_run(path)["dataset_sha256"] != model_row["dataset_sha256"]:
            raise ValueError("Example dataset must match the leaderboard")
        scores = json.loads((path / "scores.json").read_text())["questions"]
        predictions = read_jsonl(path / "predictions.jsonl")
        for key, question_id in QUESTIONS.items():
            pred = next(
                p
                for p in predictions
                if p["exercise_id"] == EXERCISE and p["question_id"] == question_id
            )
            score = next(
                s
                for s in scores
                if s["exercise_id"] == EXERCISE and s["question_id"] == question_id
            )
            value = float(score["score"])
            error = pred.get("error")
            status = (
                "incomplete"
                if error
                else ("correct" if value == 1 else "partial" if value > 0 else "incorrect")
            )
            if error:
                note = (
                    "Reached the 32,768-token output limit without a complete final answer. "
                    "Scored zero; there is no completed answer to compare."
                    if "Output limit reached" in error
                    else "The provider returned an error with no final answer. Scored zero; "
                    "this does not establish what the model would have answered."
                )
            elif key == "attachment":
                note = (
                    "Identified 3397, the lower control arm."
                    if value == 1
                    else (f"Answered {pred['answer']} instead of 3397 (lower control arm).")
                )
            else:
                note = (ASSEMBLY_NOTES if key == "assembly" else HARDWARE_NOTES)[model]
            # Construct an allowlist, not a redacted prediction object. No paths,
            # private questions, reasoning, raw provider responses or grader payloads.
            output[key].append(
                {
                    "model": model,
                    "name": NAMES[model],
                    "score": value,
                    "status": status,
                    "answer": None if error else pred["answer"],
                    "note": note,
                }
            )
    data = {
        "schema_version": 1,
        "release": leaderboard["release"],
        "dataset_sha256": leaderboard["models"][0]["dataset_sha256"],
        "examples": output,
    }
    target = site / "data/example-results.js"
    # A static script also works on answer pages opened locally without a server.
    target.write_text(
        "const EXAMPLE_RESULTS = "
        + json.dumps(data, ensure_ascii=True, indent=2).replace("<", "\\u003c")
        + ";\n"
    )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--site", type=Path, default=Path("site"))
    args = parser.parse_args()
    print(export_examples(args.run, args.site))
