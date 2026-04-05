# Input Contract

## P0 Required Inputs

At minimum, the analysis needs:
- core source material: transcripts, articles, outlines, notes, interviews, case writeups, or fragmented documents
- source ownership: whose experience, viewpoint, or method the material represents
- grouping or order across multiple documents, so different themes do not get merged by accident

Without P0, do not finalize a course-topic recommendation.

## P1 Strongly Recommended Inputs

- author background: role, experience, long-term expertise, representative outcomes
- proof assets: case studies, numbers, user feedback, before/after evidence, screenshots, work samples
- preferred market: geography, language, B2C vs B2B
- product constraints: format, duration, price band, whether coaching/community/training is in scope
- analysis mode: `A-material-only` or `B-market-scan` (`B-market-scan` is the default)
- research boundaries: which countries, platforms, and time windows should be prioritized

These inputs materially affect audience selection, promise ceiling, and differentiation strength.

## P2 Optional but High-Value Inputs

- existing target-customer hypotheses
- known competitors or reference courses
- explicitly forbidden directions
- already validated conversion angles or known failed angles
- seed keywords, user phrasing, or search phrases
- known effective channels
- existing validation signals: inquiry logs, sales calls, comments, high-performing content, landing-page data

## Language and Market Inputs

If the user's instruction language implies a market focus, the research scope should reflect that.

Rules:
- the final report should follow the user's instruction language unless the user says otherwise
- the market scan must include, and should prioritize, countries and markets aligned with the instruction language
- if the topic is cross-border, include the instruction-language market plus the most commercially relevant adjacent market

## Preprocessing Rules

- deduplicate the source set and preserve version relationships
- separate facts, cases, opinions, methods, and spoken texture before analysis
- record missing information explicitly rather than filling it in by guesswork
- assign `source_ref` IDs before analysis
- create a lightweight `trace_map`: `source_ref -> file / section / excerpt`

## Required Extraction Fields

Every run should extract at least:
- `theme_cue`: core themes and recurring claims
- `audience_cue`: audience, role, stage, baseline ability
- `problem_cue`: pain points, failure cases, blocked moments
- `outcome_cue`: outcomes the material can truly support
- `proof_cue`: cases, experience, numbers, methods, assets
- `boundary_cue`: limits, exclusions, assumptions, promise ceiling
- `language_cue`: recurring phrasing, tone, judgment style, voice markers
- `keyword_cue`: theme words, problem words, result words, alternative phrasing
- `platform_cue`: which platforms or formats the material naturally fits
- `monetization_cue`: whether the material leans toward course, community, tool, service, or pure content validation
- `evidence_ref`: the `source_ref[]` that supports each extracted cue

For stronger decision reports, target segments should also capture:
- `current_state`: what is true before the course
- `job_to_be_done`: the progress the user is trying to make
- `purchase_motivation`: why this person would actively buy
- `willingness_to_pay`: high / medium / low / unknown
- `budget_band`: rough spending range if visible
- `current_alternatives`: what the user is likely to buy or use instead

## Missing-Information Handling

If author-proof material is missing:
- you may say the topic is plausible but differentiation is weak
- you may not invent authority, years of experience, or proprietary methodology

If audience evidence is missing:
- you may propose 2-3 candidate audience groups
- each candidate group still needs a material-based reason

If market evidence is missing:
- downgrade the conclusion to “needs market validation”
- do not make strong opportunity claims
- if the task is a go/no-go decision, default toward `HOLD`, not `GO`

If keyword or competitor evidence is missing:
- generate an initial search set from the material itself
- explicitly note that SEO / trend / channel confidence is lower

If content-validation evidence is missing:
- you may judge topic plausibility
- you may not upgrade the conclusion to “validated to sell”
