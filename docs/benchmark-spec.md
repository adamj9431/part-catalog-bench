# Benchmark specification

## Objective

Part Catalog Bench measures whether a multimodal model can use one or more parts
illustrations together with the relevant text-catalog pages to answer practical,
domain-expert questions. The benchmark core is independent of any publisher or
vehicle make. A source package supplies catalog identification, bookmark rules,
logical page references, acquisition instructions, and catalog-specific model
guidance.

The Ford 1960–68 source package is the pilot and initial v1 corpus. Catalog
content is not redistributed except for the single illustration selected for
the public demo (see `DATA_AND_CATALOG_NOTICE.md`). Each evaluator supplies a
licensed PDF and the preparation tool checks its identity before creating
ignored local derivatives.

## Evaluation unit

An **exercise** has shared context—normally an illustration and one or more text
pages—and one or more questions. The primary condition is
`isolated-question`: every question receives a fresh request containing the same
context, source guide, and only that question. This prevents an earlier answer
from revealing a callout or part number to a later question.

If a question has inseparable subparts, its answer is a typed `compound` object.
Conversation-dependent question sequences are outside the v1 headline score.

## Input conditions

### Image-native (primary)

Catalog pages are rendered to PNG at 300 DPI and sent as images. The source
PDF's imperfect OCR layer is neither removed nor exposed to the model. This is
the comparable headline condition because the model must read the same pixels
regardless of provider-specific PDF preprocessing.

An exercise can crop each page independently, which also allows one of several
illustrations on a scanned page to be selected. Labeled annotations may be
rectangles or arbitrary polygons and may be shared by an exercise or scoped to
one question. Rectangle geometry is stored as normalized `(x, y, width, height)`
values; polygon geometry is stored as three or more normalized `(x, y)` points.
Both use a top-left origin relative to the full uncropped page. A tested model
receives the cropped and visibly marked image plus the numeric crop/annotation
record in its prompt.

### OCR-assisted (future ablation)

A future non-headline condition may provide a versioned OCR transcript alongside
the same images. The OCR engine, version, settings, and transcript hash must be
recorded. It must not be mixed with image-native results.

### Section retrieval (future track)

The initial benchmark supplies the relevant pages and measures comprehension.
A separate retrieval track may instead supply complete section PDFs and require
the model to locate evidence. Retrieval and comprehension scores remain
separate so a failed lookup is not mistaken for failed diagram reasoning.

## Answers and scoring

Gold answers are written and verified by domain experts. The framework does not
generate benchmark questions or answers.

Answers use typed specifications: part number, integer, date, boolean, ordered
list, ordered part path, unordered set, short text, or compound. Short text can
use exact normalized alternatives or an author-written weighted rubric. Rubric
criteria are atomic and independently graded. Identifier criteria should use
deterministic catalog-aware matchers; genuinely semantic propositions may use a
versioned model grader. The headline metric is the weighted average of all
question scores. Exercises with more questions therefore contribute more to the
headline result. Author-assigned difficulty does not alter question weight;
easy, medium, and hard results are reported separately. A secondary
difficulty-balanced score averages the represented difficulty-level scores
equally. Strict question accuracy and the macro-average of exercise scores are
also reported as diagnostics.

For rubric-scored free text, the question score is earned criterion points
divided by total available points. Strict credit requires every criterion marked
`required`. An exact match to the canonical answer or an accepted alternative
receives full credit without a grader call. The scorer never substitutes token
overlap or embedding similarity when a semantic grade is missing: an absent or
invalid grade is recorded as a scoring error.

Semantic graders receive only the question, candidate response, and one rubric
criterion at a time. The tested model never receives the gold answer, rubric,
or calibration cases. Runs record the grader provider, requested and returned
model, prompt version, settings, raw criterion responses, explanations, usage,
and errors. Those saved decisions make later scoring offline and reproducible.
Authors must calibrate semantic rubrics with human-labeled full-credit,
partial-credit, contradiction, and incorrect-identifier examples. Published
comparisons pin one grader configuration for every candidate model.

Ordered lists require the complete correct sequence for headline credit.
Ordered part paths additionally identify each separate physical instance of a
part and each repeated pass through the same instance. A path step has the form
`{"part_number":"01508","instance":1,"pass":2}`. Instance and pass sequences
start at 1 without gaps. Strict scoring compares the complete ordered triples
after catalog-aware part-number normalization.
Unordered sets require the complete correct multiset. Partial sequence/set
scores are diagnostics only; weighted free-text rubric scores are primary
question scores. Part-number matching tolerates omitted hyphens or
spaces, but never collapses meaningful letters, design suffixes, standard-part
finish codes, or occurrence markers.

Reports include results by:

- author-assigned difficulty (`easy`, `medium`, `hard`);
- reasoning category;
- answer type; and
- exercise.

The primary confidence interval uses an exercise-clustered bootstrap: complete
exercises are resampled, while the score within each bootstrap sample remains
question-weighted. This preserves the dependence among questions that share an
illustration.

## Reasoning categories

Each question has exactly one primary category describing the main reasoning
operation. Categories do not encode answer format, vehicle subsystem, or whether
an authoring annotation happens to be present.

- `component_identification`: identify a component or fastener from its depiction,
  callout, type, or immediate assembly context.
- `spatial_relationship`: determine what attaches, threads, fits, mates, connects
  to, or contains another component.
- `catalog_notation`: interpret symbols, legends, dates, revisions, applicability
  notes, or catalog lookup codes.
- `routed_system_tracing`: follow wiring, vacuum, hydraulic, hose, or cable routing
  to endpoints or branches.
- `cross_view_matching`: match the same component between installed, exploded, or
  alternate views.
- `assembly_stack_tracing`: follow a shaft, bolt, or other physical axis through
  multiple components in order, including repeated instances or passes.
- `quantity_reasoning`: count components or infer per-assembly or per-vehicle
  quantity.
- `functional_reasoning`: infer mechanical purpose, function, or permitted motion.

When more than one seems applicable, select in this order: quantity, catalog
notation, cross-view matching, functional reasoning, assembly-stack tracing,
routed-system tracing, spatial relationship, then component identification.

## Difficulty rubric

Difficulty describes the work needed with the supplied context, not general
automotive obscurity.

- **Easy:** one direct read, callout trace, relationship, lookup, or
  transcription with little ambiguity.
- **Medium:** two linked observations or an illustration-to-text lookup, plus
  modest applicability or number-family interpretation.
- **Hard:** several cross-references, visually crowded tracing, assembly order,
  subtle applicability constraints, or reconciliation of multiple plausible
  candidates.

Authors must provide a short `difficulty_note`. A second reviewer should confirm
both the answer and difficulty before an exercise becomes `ready`. Difficulty
is metadata for analysis, not a scoring weight.

## Proposed release sizes

Specialist benchmarks vary from roughly one hundred expert tasks to many
thousands of automatically or crowd-authored questions. For this benchmark,
answer verification is more valuable than chasing a large question count.

- **Pilot:** 20–30 exercises and 100–200 questions, spanning the intended
  categories and all three difficulty levels.
- **v1:** 75–150 exercises and 500–1,000 questions, with no single functional
  section or question template dominating the score.
- **Suggested difficulty target:** approximately 30% easy, 40% medium, and 30%
  hard. Treat this as a coverage target, not a quota that overrides honest
  labels.

Before a leaderboard, the public set can be used to stabilize schemas and
scorers. A later release can keep the same public runner while placing final
test answers behind a submission service.

## Reproducibility record

Every run records provider, requested and returned model names, temperature,
maximum output tokens, timeout/retry settings, prompt hash, individual rendered
page hashes, latency, token usage, parsed answer, raw response, and errors.
Scoring is offline and can be reproduced without another provider call.

## Versioning policy

Changing a prompt, source guide, page rendering, gold answer, normalization
rule, split membership, or scoring rule changes benchmark behavior and must be
recorded in release notes. Old run artifacts remain scoreable with the code
version that produced them.
