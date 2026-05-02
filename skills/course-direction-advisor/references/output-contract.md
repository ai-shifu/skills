# Output Contract

## Required Outcome

The result must end in one of two states:
- viable: one recommended topic plus two to three backup directions
- not viable: a formal `not-viable` conclusion, optionally with downgrade paths

## Required Fields for Every Topic Direction

- `analysis_mode`: `A-material-only` or `B-market-scan`
- `viability_status`: `recommended`, `alternative`, `downgraded`, or `not-viable`
- `topic_type`: cognitive, method, case, execution, outcome-led, or hybrid
- `title`: the course title
- `one_line_pitch`: who it is for and what problem it solves
- `source_boundary`: what the topic is strictly based on, and what it does not include
- `source_evidence`: the supporting cases, methods, excerpts, and proof, with `source_ref[]`
- `target_users`: one to three audience segments, each with stage, pain point, and buying reason
- for stronger reports, each target segment should also explain current state, job to be done, purchase motivation, willingness to pay, and current alternatives
- `non_buyers`: who should not be targeted, and why they are unlikely to buy
- `lifecycle_stage`: the current market stage
- `competition_type`: content, tool, service, or a combination
- `market_summary`: current heat, dominant solution types, and characteristic competitive patterns
- `opportunity_gap`: why the topic still has room, or why room is limited
- `unique_value`: the real differentiators supported by the material
- `buying_driver`: the dominant buying logic, explained through `trust / relevance / executability / value`
- `promise_ceiling`: the strongest promise level the material can honestly support
- `risk_note`: why the topic may not sell, or why it may sound empty in delivery
- `course_readiness`: whether the material is strong enough to support a course rather than only a topic angle
- `lesson_spine`: the minimum coherent lesson structure the material can support; use `insufficient` if it cannot yet support a real course
- `missing_info`: what additional evidence would make the conclusion stronger

## Required Additions for Decision / Approval Reports

- `decision_status`: `GO / HOLD / REWORK / NO-GO`
- `decision_reason`: why this is the right decision rather than a more optimistic or more conservative one
- `top_risks`: at least three risks, typically including competition, evidence weakness, and differentiation weakness
- `competition_matrix`: a matrix that explains what major competitors or substitutes solve, who they serve, why people buy them, and what gap remains
- `claim_evidence_map`: a claim-level map to `source_ref[]` and `market_ref[]`
- `scorecard`: an optional weighted scorecard if the user wants a sharper go / hold / rework judgment
- `price_hint`: recommended pricing or price band; use `unknown` if evidence is insufficient
- `mvp_scope`: the smallest launchable version of the course
- `validation_plan_7d`: a seven-day validation plan for testing demand, messaging, and sample content
- `teachable_kernel`: the distinctive viewpoints, methods, cases, experience, or insight density that make the topic teachable versus generic competitors

## Optional Additions for Deeper Market Work

Add only when the user asks for more depth:
- `demand_density`: `small / medium / large / unknown`
- `market_size_note`: a rough market-size note grounded in public signals
- `trend_pattern`: `event-spike / seasonal / steady-demand / declining / reframed-demand`
- `saturation_level`: `under-contested / segmentable / red-ocean / tool-replaced`
- `seo_gap`: public-content keyword and positioning gap
- `channel_hint`: likely entry channels and content angles
- `content_validation_status`: `validated / partially-validated / weakly-validated / unvalidated`
- `validation_basis`: the market evidence behind the validation judgment

## Required Additions for the Recommended Direction

The recommended topic must also explain:
- `why_this_one`: why it wins over larger, hotter, or more obvious directions
- `fit_reason`: how it matches the material, the user problem, and the market stage at the same time
- `go_to_market_hint`: the best packaging angle for entering the market
- `growth_shape`: whether it behaves more like a trend-led topic, a durable demand topic, or a hybrid
- `expected_curve`: whether the direction is likely to spike, compound steadily, or follow a hybrid curve
- `upside_case`: what has to go right for the topic to work especially well
- `downside_case`: what could make the topic underperform
- `course_readiness_reason`: why the material is sufficient to support a course, including the minimum three-lesson threshold when applicable

## Human-Facing Report Rules

If the report is meant for humans rather than downstream systems:
- the main and backup directions must differ meaningfully in audience, angle, teaching objective, or product form
- competitor analysis cannot stop at links; it must explain what problem each product actually solves
- the report should explicitly state whether the material is topic-ready only or genuinely course-ready
- prefer natural language over field-name-heavy presentation
- if both traceability and readability matter, produce:
  - `selection_report.md`: structured version
  - `decision_brief.md`: readable version

## `not-viable` Output

If no competitive topic can be justified:
- use `viability_status: not-viable`
- state whether the failure is due to content, audience, market, or delivery weakness
- include downgrade options where appropriate

## Title Rules

A title should express at least two of the following:
- audience
- problem
- result

It must not:
- exceed the material boundary
- promise results the evidence cannot support
- become abstract or “high-level” at the cost of specificity

## Recommended Output Order

1. conclusion first
2. backup options and why they rank below the winner
3. `not-viable` or downgrade conclusion if needed
4. market judgment: stage, competition, dominant solutions, room to win
5. deeper scans only if required
6. real material-based advantages
7. risks and missing evidence

## Reusable Output Files

When useful, also generate:
- `topic_candidates.json`
- `market_scan.md`
- `source_evidence_map.json`
- `selection_report.md`
- `decision_brief.md`
