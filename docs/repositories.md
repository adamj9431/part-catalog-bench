# Public code and private assessment data

The project is split into two independent repositories, not two branches. Each
has a new history. Neither inherits the original working repository's commits.

| Repository | Contents | Intended visibility |
| --- | --- | --- |
| `part-catalog-bench` | Code, tests, source guide, authoring app, three-question demo, site, aggregate results | Initially private; later public after review |
| `part-catalog-bench-private` | Full exercises/answers, development histories, raw assessment runs and snapshots | Always private |

The repositories can be sibling folders. Install the public project's package
in an editable virtual environment. The public app can use the private data
through the existing `--exercises` and `--output` options; do not copy private
exercises into the public tree. Maintain code only in the public repository.

Licensed catalog PDFs and generated pages live locally outside either Git
history. They can be placed in the public checkout's ignored `catalog_sources/`
and `catalog/` directories after obtaining a personal PDF copy. Credentials
belong only in a local ignored `.env` or approved secret store.

## Maintainer workflow

From the public checkout, launch the studio against the private exercise folder:

```sh
part-catalog-bench author \
  --exercises ../part-catalog-bench-private/data/exercises \
  --manifest catalog/ford-car-master-1960-68/manifest.json
```

Run an assessment with `--exercises ../part-catalog-bench-private/data/exercises`
and `--output ../part-catalog-bench-private/results`. Pin all model and grader
settings as documented in the README. Keep model keys out of Git and chat.
Score each private run using its saved snapshot, then export reviewed aggregates:

```sh
part-catalog-bench score ../part-catalog-bench-private/results/<run>
part-catalog-bench export-site \
  --run ../part-catalog-bench-private/results/<run-one> \
  --run ../part-catalog-bench-private/results/<run-two> \
  --output site/data --release '<reviewed assessment name>'
```

Select every run desired in the snapshot: export replaces rather than appends.
No private repository token is needed by the public site or its Pages workflow.
Do not configure Actions to copy the full private results tree into a public
artifact. Export locally and commit only the deliberately allowlisted summaries.

The full private pilot retains all 119 questions, including the three public
examples, to preserve the historical dataset fingerprint. This is not a disjoint
hidden-test split. A future hidden leaderboard should exclude public examples
and use a separately versioned dataset and fingerprint.

## Before making the public repository public

- Review all tracked files, historical commits, branches, tags, and Actions logs.
- Only the three approved demo questions may appear. Neither full exercises nor
  raw predictions, rubric decisions, snapshots, development logs, or handoff
  documents belong here.
- The example answer pages may show saved final model answers and scores for
  those same three approved questions, with reviewed editorial notes. This is
  an explicit exception to aggregate-only results; provider reasoning and
  raw provider payloads remain private. See [minisite instructions](minisite.md).
- Only the selected page 30–18 illustration, owner photo, and aggregate chart
  are included as images. The catalog image remains third-party material; see
  the rights notice. No full catalog PDF belongs in either Git history.
- Keep the private companion private. Repository visibility is not a per-folder
  setting; a public repository cannot have a private branch or private folder.
- Verify the intended account and URL before setting remotes or publishing.
  GitHub creation and publication require the owner's explicit approval.

The local preparation does not itself create GitHub repositories or deploy the
site. Its configured URLs indicate the intended destination, not publication.
