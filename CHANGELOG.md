# Changelog

## Unreleased

- Removed make, model, year, and other vehicle metadata from exercises; relevant
  applicability information now belongs directly in the question prompt.
- Changed the headline metric to the weighted mean of all question scores, so
  exercises with more questions contribute proportionally more.
- Added a difficulty-balanced secondary score without assigning extra value to
  hard questions.
- Changed headline confidence intervals to resample complete exercises while
  retaining question weighting within each bootstrap sample.
- Added opt-in weighted rubric scoring for `short_text` answers.
- Added semantic and deterministic Ford part-number rubric criteria.
- Rubric free-text scores now contribute fractional credit to the primary
  question and exercise scores; strict accuracy still requires all required
  criteria.
- Added saved grader metadata and per-criterion decisions so rescoring remains
  offline.
- Added Authoring Studio criterion, calibration-case, grader-setting, and
  calibration-test controls.
