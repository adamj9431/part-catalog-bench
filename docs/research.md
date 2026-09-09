# Related benchmark research

Research checked on 2026-08-06. Counts below describe the cited releases, not a
minimum requirement for Part Catalog Bench.

## Closest work

- [Enginuity](https://arxiv.org/abs/2606.03410) is the closest direct
  competitor found. It uses U.S. military service and repair manuals for
  structured parts-table extraction and free-form engineering-diagram VQA. It
  confirms that dense callouts and diagram/table cross-references deserve a
  purpose-built benchmark. Part Catalog Bench remains distinct in automotive
  catalog applicability, Ford number semantics, illustration-to-text service
  lookup, deterministic typed answers, and its user-supplied-source workflow.
- [DesignQA](https://arxiv.org/abs/2404.07917) combines Formula SAE rules, CAD
  images, and engineering drawings for rule comprehension, compliance, and
  extraction. It is adjacent engineering-document work, but not a parts-catalog
  identification or assembly benchmark.
- [DrawingVQA](https://joonv2.github.io/DrawingVQA/) contains 92 expert QA pairs
  over 33 construction drawings and explicitly tests reasoning depth. Its small,
  expert-built design supports starting with a carefully reviewed pilot rather
  than mass-generating questions.
- [Visual Search & Parts Identification Benchmark](https://benchmark.nyris.io/)
  includes an automotive image-retrieval dataset. It evaluates embedding-based
  visual search rather than diagram plus text-catalog question answering.

No automotive master-parts-catalog benchmark with the same task formulation was
found. That is a dated research conclusion, not a claim that none can exist.

## Broader implementation references

- [DocVQA](https://arxiv.org/abs/2007.00398) has 50,000 questions over more than
  12,000 document images and uses normalized answer evaluation. It demonstrates
  the value of saving predictions separately from evaluation.
- [ChartQA](https://arxiv.org/abs/2203.10244) has 9,600 human-written and 23,100
  generated questions. It separates question types and compares image-only
  extraction with a condition that supplies underlying chart data—an important
  precedent for keeping OCR-assisted results separate.
- [MMMU](https://github.com/MMMU-Benchmark/MMMU) has 11,500 questions and
  publishes development, validation, and test tooling. It shows the eventual
  value of a hidden-answer test set, while its size is unrealistic for an early
  domain-expert-authored catalog benchmark.
- [HealthAdminBench](https://github.com/som-shahlab/health-admin-bench), the
  structural reference supplied for this project, defines 135 expert tasks and
  mixes 1,177 deterministic checks with 521 LLM-judge rubrics. Its hybrid
  verification and exercise/task orientation motivate atomic free-text criteria
  plus both full exercise performance and question-level diagnostics.
- [HealthBench](https://openai.com/index/healthbench/) scores open-ended answers
  against weighted, expert-written criteria and validates its model grader
  against physician judgments. It supports rubric-based partial credit, while
  also showing why grader calibration and saved per-criterion decisions are
  required for a trustworthy public score.

## Design conclusions adopted here

1. Keep source preparation, execution, and offline scoring separate.
2. Save raw responses and all run settings for auditability.
3. Use deterministic answer types and matchers wherever possible. When free
   phrasing is intrinsic to a question, use atomic expert-written weighted
   criteria, save every model-judge decision, and require a human-labeled
   grader calibration set rather than trusting an uncalibrated holistic judge.
4. Report fine-grained categories and difficulty rather than only one number.
5. Treat image-native and OCR-assisted inputs as different experimental
   conditions.
6. Begin with 100–200 expert-reviewed questions and scale after inter-reviewer
   validation exposes ambiguous templates or normalization gaps.
