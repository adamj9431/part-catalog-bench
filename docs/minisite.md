# Results minisite

`site/` is a standalone static GitHub Pages site. It needs no package install,
build service, model keys, private repository access, or external JavaScript.
All URLs are relative so a repository subpath works.

The owner selected one catalog page for the site example: illustration 30–18,
stored as `site/assets/falcon-suspension.png`. It is an unchanged copy of the
180-DPI rendering, including the original source markings. Three existing
questions from that exercise appear verbatim in the HTML. Each links to
`answer.html?example=attachment`, `hardware`, or `assembly`. Those pages use the
existing gold answers and explanatory vector highlights over the same image;
the source pixels are unchanged. Highlight labels remain fixed-size when the
diagram is enlarged. This is the only
catalog image selected for inclusion; the full catalog and remaining exercises
are not copied into the site. The image is third-party material, not covered by
the software license. No claim of permission from Ford or Forel is made here.

## Export a reviewed snapshot

The final “The car behind the benchmark” section includes the owner's supplied, AI-edited Thunderbird photo
at `site/assets/thunderbird-owner.png`, copied unchanged. Its caption discloses
the AI edit. It is a personal site illustration, not benchmark input.

First finish and score each selected run. Then export *all* models to include:

```sh
part-catalog-bench export-site \
  --run ../part-catalog-bench-private/results/assessment-2026-09-recovery/gpt-6-astra \
  --run ../part-catalog-bench-private/results/assessment-2026-09-final/claude-fable-5-1 \
  --run ../part-catalog-bench-private/results/assessment-2026-09-final/gpt-5-6-sol-pro \
  --run ../part-catalog-bench-private/results/assessment-2026-09-final/gemini-3-8-flash \
  --run ../part-catalog-bench-private/results/assessment-2026-09-final/deepseek-v4-flash-vision-exp \
  --output site/data \
  --release 'September 2026 pilot'
```

Export replaces `results.json` and `results.csv` in the destination. It makes
no model calls. Incomplete runs, duplicate predictions/models, invalid scores,
different settings, and mismatched datasets are rejected. The currently displayed
dataset is the full 119-question pilot; no public/private split is implied.

The exporter constructs a field allowlist rather than redacting a copy of the
original results. It exports model/configuration metadata, a dataset hash, and
aggregate scores, cost, latency, and reliability. It omits exercise/question IDs,
prompts, expected and predicted answers, rubric details, paths, catalog material,
and provider responses. Category and difficulty groups need at least five
questions. Review metadata and numeric summaries before public release.

### Model answers for the three public examples

The answer pages also load `site/data/example-results.js`: an explicitly approved
exception to aggregate-only publication. It contains each model's final answer,
saved score, completion status, and a short editorial note for only the three
public questions (q01, q02, and q06 of the Falcon suspension exercise).
Incomplete responses are shown separately from incorrect completed answers.
No provider reasoning, raw response payloads, or other question answers are included.

Regenerate this snapshot with `python tools/export_example_results.py --run
<completed-run-directory> --run <another-completed-run-directory> --site site`,
passing every run used for the current leaderboard. Private sibling repository
paths work too. The exporter verifies completed runs and matching models and
dataset hashes. It does not call a model or change scores. The editorial notes
are manually reviewed descriptions of the September 2026 answers, not an
automatic grader: review and update them whenever replacing runs or adding
models. Regenerate both the aggregate and example snapshots together, then run
`node --test tests/minisite.test.cjs tests/answers.test.cjs` before publishing.

Assembly dates are not necessarily inference dates. Reused response counts include
both older runs and the batches assembled into the final run. Cost accounts for
retained candidate responses and may exclude paid retries that were not recorded.

## Local preview

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8766. Reload after a new export. The site is a publication
snapshot, not a monitor of private runs. Choose a model in the chart or table to
show details; switch difficulty/category; sort numeric headings; download CSV,
JSON, or an SVG chart. Missing/incomplete costs remain unreported and are excluded
from the cost frontier. The frontier is based on observed point estimates.

## Publish after the repository split

Link previews use `site/data/pareto-preview.png`, a static 1200×630 chart generated
automatically by `export-site` from public aggregates. Open Graph and Twitter
metadata are in the initial HTML, so preview crawlers do not need JavaScript.
The absolute URLs assume `https://adamj9431.github.io/part-catalog-bench/`; update
them if deploying elsewhere. Slack and Messages cannot fetch the local preview.
They may also cache old previews after publication.

The site has a citation section and downloadable `site/citation.bib`; the root
`CITATION.cff` identifies Adam Johnson as the author. These pilot citations use
the selected repository URL, `https://github.com/adamj9431/part-catalog-bench`,
without a DOI. Before publishing, add the release version/date to the citation
metadata and keep the displayed BibTeX
and download in sync. Add a DOI only after an archive service has assigned one.

This checkout contains code, the selected three-question demo, and this site,
with a fresh history separate from the private assessment data. Review it before
making it public. In the public GitHub repo,
choose **Settings → Pages → Source → GitHub Actions**, then run **Publish results
minisite** from Actions. The workflow is manually triggered and skips private
repositories. Only `site/` is uploaded. The setup follows the
[GitHub Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The full snapshots and original run files remain private. Export into the public
repository from private run directories locally; the published site never reads
the private repository. No publication has been performed by preparing this site.
