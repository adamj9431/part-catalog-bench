"""Guard the deliberately small demo and allowlisted publication surface."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_only_approved_demo_questions_are_shipped():
    files = list((ROOT / "data/exercises").glob("*.yaml"))
    assert len(files) == 1
    example = yaml.safe_load(files[0].read_text())
    assert example["id"] == "ford-illustration-030-018-1967-falcon-suspension"
    assert {q["id"] for q in example["questions"]} == {"q01", "q02", "q06"}


def test_publication_assets_are_allowlisted():
    assert {p.name for p in (ROOT / "site/assets").iterdir() if p.is_file()} == {
        "falcon-suspension.png", "thunderbird-owner.png",
    }
    assert not list((ROOT / "site").rglob("*.pdf"))
    assert not list((ROOT / "site").rglob("predictions.jsonl"))
    assert not list((ROOT / "site").rglob("dataset_snapshot.json"))
