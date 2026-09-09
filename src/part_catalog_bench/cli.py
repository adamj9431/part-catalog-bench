from __future__ import annotations

import json
import webbrowser
from collections import Counter
from pathlib import Path

import typer

from .assets import render_catalog_ref
from .authoring import create_authoring_app
from .catalog import inspect_catalog, split_catalog, validate_manifest
from .models import load_exercises
from .publication import export_site
from .reporting import score_run, write_report
from .runner import run_benchmark
from .source import load_source_definition
from .util import load_dotenv

app = typer.Typer(no_args_is_help=True, help="Benchmark multimodal models on parts catalogs.")
catalog_app = typer.Typer(no_args_is_help=True, help="Prepare a locally supplied catalog PDF.")
exercises_app = typer.Typer(no_args_is_help=True, help="Validate benchmark exercise files.")
app.add_typer(catalog_app, name="catalog")
app.add_typer(exercises_app, name="exercises")


def _print_json(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, sort_keys=True))


@catalog_app.command("inspect")
def catalog_inspect(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    source_id: str = typer.Option(..., "--source"),
) -> None:
    """Check that a PDF matches a source package and show its bookmark roots."""
    definition = load_source_definition(source_id)
    report = inspect_catalog(pdf, definition)
    _print_json(report)
    if report["identity_errors"]:
        raise typer.Exit(1)


@catalog_app.command("split")
def catalog_split(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    source_id: str = typer.Option(..., "--source"),
    output: Path = typer.Option(Path("catalog"), "--output", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Split a user-supplied catalog into bookmarked section PDFs."""
    definition = load_source_definition(source_id)
    manifest = split_catalog(pdf, output, definition, overwrite=overwrite)
    typer.echo(str(manifest.resolve()))


@catalog_app.command("validate")
def catalog_validate(
    manifest: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    verify_hashes: bool = typer.Option(True, "--verify-hashes/--skip-hashes"),
) -> None:
    """Validate page coverage, files, page counts, hashes, and logical references."""
    errors = validate_manifest(manifest, verify_hashes=verify_hashes)
    if errors:
        for error in errors:
            typer.echo(f"ERROR: {error}", err=True)
        raise typer.Exit(1)
    typer.echo("Catalog manifest and split PDFs are valid.")


@catalog_app.command("render")
def catalog_render(
    manifest: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    catalog_ref: str = typer.Argument(...),
    output: Path | None = typer.Option(None, "--output", "-o"),
    dpi: int = typer.Option(300, min=72, max=600),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Render one logical catalog page to a standardized PNG."""
    path = render_catalog_ref(
        manifest, catalog_ref, dpi=dpi, output_path=output, overwrite=overwrite
    )
    typer.echo(str(path.resolve()))


@exercises_app.command("validate")
def exercises_validate(
    exercises: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Validate exercise files and summarize author-assigned difficulty."""
    loaded = load_exercises(exercises)
    question_ids: set[tuple[str, str]] = set()
    difficulty: Counter[str] = Counter()
    status: Counter[str] = Counter()
    for path, exercise in loaded:
        status[exercise.status.value] += 1
        for question in exercise.questions:
            key = (exercise.id, question.id)
            if key in question_ids:
                raise typer.BadParameter(f"duplicate question key {key} (found at {path})")
            question_ids.add(key)
            difficulty[question.difficulty.value] += 1
    _print_json(
        {
            "exercise_files": len(loaded),
            "questions": len(question_ids),
            "by_status": dict(sorted(status.items())),
            "by_difficulty": dict(sorted(difficulty.items())),
        }
    )


@app.command("run")
def run_command(
    provider: str = typer.Option(..., "--provider"),
    model: str = typer.Option(..., "--model"),
    exercises: Path = typer.Option(Path("data/exercises"), "--exercises", exists=True),
    manifest: Path | None = typer.Option(None, "--manifest", exists=True, dir_okay=False),
    output: Path = typer.Option(Path("results"), "--output"),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    temperature: float = typer.Option(0.0),
    max_tokens: int = typer.Option(8192, min=1),
    reasoning_effort: str | None = typer.Option(
        None,
        "--reasoning-effort",
        help="Optional model reasoning effort: none, low, medium, high, xhigh, or max.",
    ),
    timeout: float = typer.Option(180.0, min=1),
    retries: int = typer.Option(2, min=0, max=10),
    dpi: int = typer.Option(300, min=72, max=600),
    run_id: str | None = typer.Option(None, "--run-id"),
    grader_provider: str | None = typer.Option(
        None,
        "--grader-provider",
        help="Provider for semantic rubric grading; defaults to the tested provider.",
    ),
    grader_model: str | None = typer.Option(
        None,
        "--grader-model",
        help="Model for semantic rubric grading; defaults to the tested model.",
    ),
    grader_max_tokens: int = typer.Option(1024, "--grader-max-tokens", min=128),
    grader_reasoning_effort: str | None = typer.Option(
        None,
        "--grader-reasoning-effort",
        help="Optional reasoning effort for the rubric grader.",
    ),
    reuse_from: list[Path] | None = typer.Option(
        None,
        "--reuse-from",
        exists=True,
        file_okay=False,
        help=(
            "Reuse matching question results from an earlier run directory. "
            "Repeat for multiple compatible runs."
        ),
    ),
) -> None:
    """Run every selected question in an independent model request."""
    load_dotenv()
    run_dir = run_benchmark(
        provider_name=provider,
        model=model,
        exercises_path=exercises,
        manifest_path=manifest,
        output_root=output,
        include_drafts=include_drafts,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        retries=retries,
        dpi=dpi,
        run_id=run_id,
        grader_provider_name=grader_provider,
        grader_model=grader_model,
        grader_max_tokens=grader_max_tokens,
        grader_reasoning_effort=grader_reasoning_effort,
        reuse_from=reuse_from,
    )
    typer.echo(str(run_dir.resolve()))


@app.command("score")
def score_command(
    run_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    exercises: Path | None = typer.Option(None, "--exercises", exists=True),
) -> None:
    """Score saved predictions without making model calls."""
    scores = score_run(run_dir, exercises)
    _print_json(scores["summary"])


@app.command("report")
def report_command(
    run_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    exercises: Path | None = typer.Option(None, "--exercises", exists=True),
) -> None:
    """Write a Markdown report, including results by difficulty."""
    scores = score_run(run_dir, exercises) if exercises is not None else None
    typer.echo(str(write_report(run_dir, scores).resolve()))


@app.command("export-site")
def export_site_command(
    runs: list[Path] = typer.Option(..., "--run", exists=True, file_okay=False),
    output: Path = typer.Option(Path("site/data"), "--output"),
    release: str = typer.Option("September 2026 pilot", "--release"),
) -> None:
    """Export aggregate-only results for the static minisite (no model calls)."""
    try:
        destination = export_site(runs, output, release)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(str(destination.resolve()))


@app.command("author")
def author_command(
    manifest: Path = typer.Option(
        Path("catalog/ford-car-master-1960-68/manifest.json"),
        "--manifest",
        exists=True,
        dir_okay=False,
    ),
    exercises: Path = typer.Option(Path("data/exercises"), "--exercises"),
    host: str = typer.Option("127.0.0.1", help="Local bind address."),
    port: int = typer.Option(8765, min=1, max=65535),
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser"),
) -> None:
    """Launch the local visual benchmark authoring application."""
    import uvicorn

    load_dotenv()
    local_app = create_authoring_app(manifest.resolve(), exercises.resolve())
    url = f"http://{host}:{port}"
    typer.echo(f"Authoring application: {url}")
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(local_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
