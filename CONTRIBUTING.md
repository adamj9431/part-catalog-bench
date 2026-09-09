# Contributing

## Adding questions

Questions and answers are supplied by domain experts. The benchmark tooling does
not generate gold questions or answers.

1. Copy `data/exercises/example-ford-illustration-30-18-1967-falcon.yaml`.
2. Give the exercise and every question stable IDs.
3. Select only the catalog pages required to answer the question.
4. Choose the narrowest answer type that fits.
5. Choose one controlled reasoning category using `docs/benchmark-spec.md`.
6. Record evidence notes that are hidden from tested models.
7. Run `part-catalog-bench exercises validate data/exercises`.
8. Have a second person answer the question without seeing the gold answer.
9. Resolve disagreements before changing `status` from `draft` to `ready`.

Every question requires `difficulty: easy`, `medium`, or `hard` and a brief
`difficulty_note`. Use the supplied-context rubric in
`docs/benchmark-spec.md`: direct reads are easy, linked observations or a
straight illustration-to-text lookup are medium, and crowded multi-step tracing
or subtle applicability reconciliation is hard. Difficulty affects reporting,
not question weight.

Questions should be self-contained because isolated-question mode is primary.
If subparts genuinely depend on the same referent, use a compound answer rather
than conversation-dependent phrases such as "the aforementioned part."

## Crops and annotations

Use `context.pages` when a catalog page needs an overall crop. This is useful
when a physical page contains two illustrations and only one belongs in the
exercise. Rectangle values are normalized to the full page:

```yaml
context:
  pages:
    - ref: illustrations:24-2
      crop: {x: 0.08, y: 0.04, width: 0.75, height: 0.44}
```

Put reusable highlighted regions in `context.annotations`; put a region used by
only one question in that question's `annotations`. Each annotation names its
page, label, and normalized rectangle or polygon. The visual authoring studio is
the preferred way to create these coordinates.

## Answer types

- `part_number`: Ford service, engineering, or standard hardware numbers.
- `integer`: quantities and counts.
- `date`: ISO `YYYY-MM-DD` dates.
- `boolean`: yes/no answers.
- `ordered_list`: a sequence whose items do not need physical-instance identity.
- `ordered_part_path`: an installed or traced path where repeated part numbers
  may mean separate physical copies or repeated passes through one copy. Use the
  studio's row editor to create these answers.
- `unordered_set`: collections where order is irrelevant.
- `short_text`: names or descriptions, scored either by exact alternatives or
  an author-written weighted rubric.
- `compound`: multiple named fields, each with its own answer definition.

Use exact alternatives when the answer has only a small, enumerable set of
forms. For genuinely free phrasing, split correctness into atomic rubric
criteria. Prefer deterministic criteria for identifiers such as Ford part
numbers and semantic criteria only for propositions that cannot be normalized
reliably. Every semantic rubric should include calibration examples covering a
full answer, meaningful partial answers, a contradiction or negation, and an
incorrect identifier where applicable. Run those examples in the studio and
have a second reviewer confirm both the criteria and point weights.

## Adding a catalog source

A new source package requires:

- A YAML definition under `sources/`.
- Acquisition and rights instructions.
- Source identity checks.
- Bookmark-root matching rules.
- Logical page-reference rules.
- A catalog-specific model guide under `prompts/sources/`.
- At least one catalog-processing fixture or test.

Source-specific rules must not be added to the provider adapters or generic
scoring code.
