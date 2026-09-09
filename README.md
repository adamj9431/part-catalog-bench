# Part Catalog Bench

Part Catalog Bench evaluates how well multimodal AI systems read illustrated
parts catalogs: callouts, exploded views, assembly order, attachment
relationships, quantities, symbols, applicability tables, and full part-number
lookups.

The benchmark core is source-agnostic. The first source package targets the
*1960-68 Ford Car Master Parts and Accessories Catalog*, but future source
packages can add other catalogs without changing the runner or scoring system.

## Status

This repository contains the benchmark framework, authoring studio, Ford source
adapter, and results minisite. The public demo contains **one exercise with three
questions** from illustration 30–18. The published assessment covers **10 exercises
and 119 questions**; the full question set, answers, and individual model responses
are held separately in a private repository. Running the public demo does not
reproduce the full leaderboard. Draft exercises are excluded from scored runs.

The September 2026 results were obtained through OpenRouter. Databricks support
exists in the runner, but no Databricks results are included. Source PDFs are
user-supplied; only the single example diagram is included on the site.

## Obtain the Ford catalog

The catalog is copyrighted and is not included here. Purchase product **D10063,
1960-68 Ford Car Master Parts and Accessories Catalog** from the
[official Forel eBook catalog](https://www.forelpublishing.com/clickbank/index.html).
It should contain 5,445 pages.

Place the downloaded PDF at:

```text
catalog_sources/ford-car-master-1960-68.pdf
```

The original Forel filename is also recognized when supplied explicitly to the
preparation command.

## Install

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Prepare the catalog

```bash
part-catalog-bench catalog inspect \
  catalog_sources/ford-car-master-1960-68.pdf \
  --source ford-car-master-1960-68

part-catalog-bench catalog split \
  catalog_sources/ford-car-master-1960-68.pdf \
  --source ford-car-master-1960-68

part-catalog-bench catalog validate \
  catalog/ford-car-master-1960-68/manifest.json
```

The split command produces separate `text/` and `illustrations/` trees, nested
by bookmarked catalog section. Licensed outputs remain local and are ignored by
Git.

Render a logical catalog page for use in an exercise:

```bash
part-catalog-bench catalog render \
  catalog/ford-car-master-1960-68/manifest.json \
  illustrations:24-2
```

## Visual authoring studio

The studio renders PDF pages with Poppler. Install it before starting the
studio (`brew install poppler` on macOS, or `apt install poppler-utils` on
Debian/Ubuntu). Already-rendered pages are cached, so a missing Poppler install
may otherwise appear to affect only pages you have not viewed before.

After preparing the catalog, launch the local authoring application:

```bash
part-catalog-bench author \
  --manifest catalog/ford-car-master-1960-68/manifest.json
```

The studio opens illustration pages on the left and text pages on the right. It
provides bookmark-based section and subsection navigation with page-within-section
offsets, one-click matching between illustration and text sections, and lets a
domain expert create and edit exercises, see which exercises already use the
current page, draw a crop around one of multiple illustrations on a page, draw
labeled rectangular or polygonal highlights, delete them either on the page or
from the editor, assign highlights to the whole exercise or only the selected
question, build typed answers without writing JSON, and run that question once
during development. Attachment-path answers have row controls for separate
physical copies and repeated passes through the same copy. Archived exercises
are moved to `data/exercises/.trash/` rather than permanently deleted.

Free-text answers can use either exact alternatives or a weighted rubric. The
studio provides editors for semantic criteria, deterministic Ford part-number
criteria, point weights, strict-pass requirements, and calibration examples.
Calibration examples can be run against the configured grader directly in the
studio, with per-criterion decisions shown alongside the resulting score.

Each catalog viewer supports independent pinch-to-zoom and panning without
scaling the rest of the studio. Zoom resets to 100% when that viewer changes
pages; annotation outlines remain a fixed visual width as the page is zoomed.
The adjacent controls provide keyboard/mouse-accessible zoom and reset.
The top-bar controls can hide either catalog viewer so the remaining viewer and
editor have more room, or hide both viewers for a full-width editor. Either
viewer can be restored without losing the page it was displaying.

The editor marks exercise and question changes as saved or unsaved. A question
with unsaved changes must be saved or explicitly discarded before another
question can be selected. Exercise-wide setup and question detail use separate
editor views, with the exercise picker, question picker, and save state always
visible above the scrolling form. On wider screens, drag the dividers between
the catalog and editor columns to resize them; the chosen catalog widths are
remembered locally. Development model runs appear under their question
as a persistent newest-first history of model/response pairs with strict
pass, fail, or provider-error status. Development runs expose reasoning effort
and maximum output tokens; the default output allowance is 8,192 tokens.
The model field loads a searchable provider model list while retaining manual
entry as a fallback. Up to five recently used models are shown first for each
provider, with the latest one selected by default on later studio visits. Other
models are ordered newest-first when the provider supplies an availability or
creation timestamp, then alphabetically when it does not.
Before a development run, the request preview shows the exact system and user
prompt text plus every attached catalog image. Its download includes the full
provider request JSON, including base64 image data, for byte-level inspection.
Responses that exhaust that allowance without producing a complete final
answer are reported as errors rather than scored as incorrect answers.

Coordinates are normalized fractions of the full page with a top-left origin.
At run time, the model receives both a visibly highlighted/cropped PNG and the
numeric crop and annotation coordinates. This remains image-native: embedded
PDF OCR is not sent to the model.

## Validate exercises

```bash
part-catalog-bench exercises validate data/exercises
```

Exercises are YAML files containing shared context and multiple scored
questions. The primary evaluation condition is **isolated-question mode**: each
question is sent in a fresh request with the same exercise context. This avoids
cross-question clues and order effects. Truly dependent subparts can be encoded
as a compound answer with independently scored fields.

## Run models

Copy `.env.example` to `.env` or export the relevant variables in your shell.

OpenRouter:

```bash
export OPENROUTER_API_KEY='...'
part-catalog-bench run \
  --provider openrouter \
  --model openai/gpt-5.6-sol \
  --reasoning-effort low \
  --max-tokens 8192 \
  --grader-provider openrouter \
  --grader-model openai/gpt-5.6-sol \
  --exercises data/exercises \
  --manifest catalog/ford-car-master-1960-68/manifest.json
```

Reasoning effort is optional and accepts `none`, `low`, `medium`, `high`,
`xhigh`, or `max`. If omitted, the provider/model default applies. Record this
setting when comparing reasoning models because it affects quality, latency,
and cost.

`--grader-provider` and `--grader-model` select the independent model used for
semantic free-text rubric criteria. If omitted, they default to the tested
provider and model for convenient development. Published comparisons should
pin one grader model, reasoning setting, and prompt version for every candidate
model. Deterministic rubric criteria, such as the presence of a normalized Ford
part number, do not make a grader call.

Databricks Unity AI Gateway or Model Serving:

```bash
export DATABRICKS_TOKEN='...'
export DATABRICKS_BASE_URL='https://workspace.cloud.databricks.com/ai-gateway/mlflow/v1'
part-catalog-bench run \
  --provider databricks \
  --model system.ai.claude-sonnet-4-5 \
  --exercises data/exercises \
  --manifest catalog/ford-car-master-1960-68/manifest.json
```

Only completed exercises are run unless `--include-drafts` is supplied.
Requests and raw responses are saved under `results/`. Runs are resumable.
Every new run also freezes the selected exercise definitions, including answer
specifications, in `dataset_snapshot.json`. `run.json` records a SHA-256
fingerprint of that snapshot plus the current Git commit when available. A run
cannot be resumed if the selected exercises no longer match its fingerprint.

### Add questions without rerunning unchanged ones

Create a new run ID for the expanded dataset and point it at the earlier result:

```bash
part-catalog-bench run \
  --provider openrouter \
  --model openai/gpt-5.6-sol \
  --max-tokens 32768 \
  --timeout 600 \
  --retries 2 \
  --grader-provider openrouter \
  --grader-model google/gemini-3.5-flash-lite \
  --grader-max-tokens 512 \
  --exercises data/exercises \
  --manifest catalog/ford-car-master-1960-68/manifest.json \
  --run-id expanded-gpt-5-6-sol \
  --reuse-from results/original-gpt-5-6-sol
```

The runner reuses an earlier prediction only when the candidate model settings,
complete prompt, and rendered catalog-image hashes match. New questions and
questions whose prompt, context, annotation, crop, catalog image, or output
shape changed receive fresh model requests. A changed answer key can reuse the
candidate response; semantic rubric grading is rerun when its answer
specification or grader configuration changed. Infrastructure failures are not
reused, while output-limit failures are retained as reproducible model outcomes.
Use the same provider, model, temperature, reasoning effort, output limit,
timeout, retry count, and rendering DPI as the source run; incompatible settings
are rejected rather than silently mixing evaluation conditions.

Each reused row records its source run and dataset fingerprint. Score and report
commands operate on the new run's expanded dataset snapshot, so all overall,
difficulty, category, exercise, confidence-interval, and efficiency metrics are
recomputed across the combined results. Supply `--reuse-from` more than once
to search multiple compatible source runs in order.

## Score and report

```bash
part-catalog-bench score results/<run-id>
part-catalog-bench report results/<run-id>
```

The headline score is the weighted mean of all question scores, so an exercise
with more questions contributes proportionally more. Difficulty does not change
a question's weight. The report separately includes easy, medium, and hard
scores plus a difficulty-balanced diagnostic that averages the represented
difficulty-level scores equally. Rubric-scored free text contributes its
fractional score to the headline result; strict accuracy still requires every
required criterion. Reports also include diagnostic partial credit for list/set
answers, category breakdowns, scoring errors, latency, token usage, and an
exercise-clustered bootstrap confidence interval. A run with any rubric scoring
error is explicitly marked invalid for comparison until it is re-graded
successfully.

`scores.json` separates candidate-model, semantic-grader, and combined
efficiency metrics. Each includes request counts, provider-reported cost, input,
output, total, reasoning, and cached tokens, plus total, mean, median, p95,
minimum, and maximum recorded latency. Missing provider cost or token fields are
marked incomplete instead of being treated as zero. `report.md` presents the
main totals in an Efficiency table.

Scoring uses the frozen snapshot by default, so later edits to live exercise
files cannot change an old run's score. Supplying `--exercises` explicitly is
still supported for diagnostics; a fingerprint mismatch is recorded and marks
that score invalid for official comparison. Runs created before snapshots were
introduced remain scoreable from their original exercise path, but their
dataset verification is reported as unavailable and they are not marked valid
for official comparison.

## Import predictions

Models without a built-in adapter can produce JSONL predictions using the
documented schema and place them in a run directory. Semantic rubric decisions
are saved with each prediction, so scoring and reporting never require a live
model call and can be reproduced from the saved run artifact.

A complete run directory contains:

```text
results/<run-id>/
├── run.json                 model settings and dataset fingerprint
├── dataset_snapshot.json    frozen questions and answer specifications
├── predictions.jsonl        one durable model result per question
├── scores.json              scores, provenance, cost, tokens, and latency
└── report.md                human-readable report
```

## Repository layout

The static results minisite lives in `site/`. `part-catalog-bench export-site`
creates its aggregate-only data from completed, scored runs without exposing
private questions, answers, or catalog assets. See [minisite instructions](docs/minisite.md)
for previewing, refreshing, and publishing it to GitHub Pages.

```text
src/part_catalog_bench/  benchmark library and CLI
sources/                 source-package definitions
prompts/                 shared and source-specific model instructions
data/exercises/          public exercise definitions
data/splits/             versioned benchmark splits
schemas/                 JSON schemas for external tooling
tests/                   offline tests
catalog_sources/         user-supplied PDFs (ignored)
catalog/                 generated PDFs and page images (ignored)
results/                 model runs (ignored)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the authoring and verification
workflow and [DATA_AND_CATALOG_NOTICE.md](DATA_AND_CATALOG_NOTICE.md) for source
material restrictions.

For the public/private repository boundary and the maintainer's local workflow,
see [repository separation](docs/repositories.md).

The complete design is in [docs/benchmark-spec.md](docs/benchmark-spec.md), and
the benchmark/competition survey is in [docs/research.md](docs/research.md).
