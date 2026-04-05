---
name: course-direction-advisor
description: Turn user-provided source materials into market-fit course-topic decisions without exceeding the evidence boundary of the materials. Use when the user needs course topic selection, competitor analysis, pricing guidance, audience targeting, market positioning, or a decision on whether the material is strong and complete enough to support a course. Avoid when the topic is already fixed and the user only needs lesson breakdowns, scripts, or copy polishing.
metadata:
  short-description: Select and validate market-fit course topics from source materials
---

# Course Topic Selection

Turn messy or complete source materials into a course-topic decision that is sellable, explainable, and traceable.

## What This Skill Actually Does

This skill is not a generic naming tool. It performs a constrained commercial translation:
- Content constraint: the core of the course must come from the user's materials.
- Market constraint: the recommendation must match real demand, competition, and buying logic.

The goal is not to find the biggest possible topic. The goal is to find the smallest topic that is still credibly sellable:
- `Minimum Sellable Topic`: a topic the author can truly teach and the market can plausibly buy.

## Core Capabilities

This skill is designed to:
- translate an author's real material into market-aware course directions
- identify target users, market stage, competing solutions, and credible gaps
- judge whether a topic is too crowded, tool-replaced, weakly differentiated, or better downgraded
- decide whether the material supports a course, a lighter product, or no product at all
- judge whether the material is substantial enough to sustain a real course rather than only a topic claim

This skill can optionally expand into:
- `demand-density`
- `seo-gap`
- `trend-cycle`
- `channel-strategy`
- `content-validation`

This skill should not pretend it can do:
- precise TAM / SAM / SOM modeling
- strong demand claims based on one viral post or one hot keyword
- direct conversion from traffic heat to paid-course demand
- author positioning that the source material cannot support

## What Is Allowed vs. Not Allowed

Allowed:
- reorganizing the source material
- reframing the angle
- extracting audience, problem, and result from the material
- adjusting the packaging level to fit market language

Not allowed:
- inventing methods that are not in the material
- fabricating cases, results, authority, or credentials
- turning scattered experience into a fake complete system
- replacing real capability with trendy market language

In short:
- commercial reframing is allowed
- content fabrication is not

## Minimum Invocation Pattern

### Minimum Input
- one or more source documents, transcripts, notes, drafts, or outlines
- optional: author background, case proof, market preference, known competitors

### Typical Output
- `topic-selection-report.md`
- `topic_candidates.json`

### Typical Failure Pattern
- Failure: the material contains opinions but no stable audience, method, case, or proof, yet gets packaged as a high-promise results course.
- Fix: pull the recommendation back to the real evidence ceiling, or downgrade the product.

## Analysis Modes

Use two modes, with `B-market-scan` as default:
- `A-material-only`: analyze only the provided materials; useful when the user explicitly forbids external scanning
- `B-market-scan`: combine material analysis with current public market signals

Rules:
- Use `A-material-only` only when the user explicitly asks for material-only analysis or blocks external research.
- Use `B-market-scan` by default when you need to recommend pricing, market opportunity, validation strength, competition, or final prioritization.
- In `A-material-only`, do not make strong market claims. Use conservative labels such as “plausible,” “needs market validation,” or “not ready for final recommendation.”
- Always state the analysis mode in the output.

## Language and Market Scope

This skill is written in English, but report delivery follows the user's instruction language.

Course-topic-specific language rules:
- The final report should be written in the same language the user used to issue the task, unless the user asks otherwise.
- Market research must include, and should prioritize, countries and markets that match the instruction language.
- Example: if the user asks in Chinese, research should include and prioritize Chinese-language markets; if the user asks in English, research should include and prioritize English-language markets.
- If the topic is clearly cross-border, research should cover both the instruction-language market and the most commercially relevant adjacent market.

## Standard Lifecycle Labels

Use these five labels as the canonical lifecycle taxonomy:
- `information-explosion`
- `segmented-understanding`
- `methodology-phase`
- `toolification-phase`
- `red-ocean`

If older labels appear in historical templates, map them to the canonical set in the final output.

## Core Judgment Sequence

Do not jump to title ideas too early. Make these judgments first:

1. `content compression`
- What does the material consistently do well?
- What does it clearly not support?

2. `user mapping`
- Who is the material best suited to help?
- Who has both the need and the willingness to pay?

3. `market positioning`
- What stage is the market in?
- What kinds of solutions dominate the space?

4. `sellable packaging`
- What is the right product form and promise level for the evidence available?

5. `content sufficiency`
- Does the material contain enough distinctive viewpoints, methods, cases, experience, or teaching assets to support an actual course?
- Can the topic sustain at least three meaningful lessons without filler?
- Is there a self-consistent knowledge spine rather than scattered observations?

6. `validation strength`
- Is this topic merely logical, or does it already show enough public market support to justify building?

If any of these six steps fails, do not finalize the topic.

## Evidence Discipline

Every important claim should be tagged by source type:
- `source-direct`: stated explicitly in the material
- `source-inferred`: inferred from multiple parts of the material without exceeding it
- `market-observed`: drawn from current public market evidence
- `synthesis-judgment`: a reasoned conclusion based on source and market evidence together

Never present `market-observed` or `synthesis-judgment` as if it came directly from the source material.

## Evidence Indexing

Before analysis, build an evidence index:
- assign `source_ref` IDs to material chunks, such as `SRC-001`, `SRC-002`
- maintain a short `trace_map`: `source_ref -> excerpt / summary / location`
- record market evidence separately as `market_ref`, with concrete dates and links

Output rules:
- every major claim should be traceable to `source_ref[]`, `market_ref[]`, or both
- recommendations, unique-value claims, audience claims, risk claims, and no-go conclusions should all be traceable at the claim level
- `source_evidence_map.json` is recommended by default for decision-oriented reports

## Priority Rules

When “bigger market” conflicts with “truer material,” prioritize the material boundary.

The same material may legitimately be translated:
- from expression-oriented material into a problem-oriented course
- from experience-oriented material into a method-oriented course
- from a broad theme into a narrower segment

But only if:
- the new topic can still be proven directly or indirectly by the material
- the author can genuinely teach it without sounding empty
- the material contains enough internal structure to support a course, not just a catchy title

## Course-Readiness Standard

Finding a plausible topic is not enough. The material must also be able to carry a course.

Before finalizing any recommended topic, test all of the following:
- `knowledge depth`: are there enough real concepts, judgments, or principles to teach?
- `knowledge breadth`: is there enough material to cover at least three meaningful lessons?
- `internal coherence`: do the viewpoints, methods, cases, and examples form a self-consistent whole?
- `teaching assets`: are there usable cases, scenarios, mistakes, comparisons, workflows, or exercises?
- `distinctive kernel`: compared with competitors, does the material contain a real teachable edge such as a distinct viewpoint, specific method, unusual experience, or an interest-triggering angle?

Do not approve a course topic when the material has only one of the following:
- a marketable headline without enough teaching substance
- generic opinions that competitors can also say
- fragmented notes without a stable method or teaching path
- inspiration value but no repeatable knowledge structure

Minimum rule:
- a full course recommendation should normally be able to support at least three lessons with non-redundant knowledge points
- if the material cannot support that threshold, downgrade the recommendation to a lighter product form

## Market Scan Rules

If you use `B-market-scan` or make market claims:
- research current public discussion rather than relying on memory or general intuition
- prioritize the last 90 days; extend to 12 months for mature topics
- write concrete dates instead of “recently” or “now”
- state clearly when evidence is insufficient

See also:
- [input-contract.md](references/input-contract.md)
- [decision-model.md](references/decision-model.md)
- [market-analysis.md](references/market-analysis.md)
- [output-contract.md](references/output-contract.md)
- [gating-rules.md](references/gating-rules.md)
- [decision-report-template.md](references/decision-report-template.md)

## Recommended Workflow

1. clean and group the source material
2. extract theme, audience, problem, result, proof, and boundary cues
3. compress the content into a real capability core
4. separate “people who need this” from “people who will pay for this”
5. derive search terms from the material
6. scan public discussion, paid products, user complaints, and solution promises
7. identify market stage, competition type, saturation, and replacement risk
8. extract the material's real differentiation and test it against the market gap
9. output a recommended topic, backup options, or a `not-viable / downgraded` result
10. add optional deep scans only if the user asks for them

## Reporting and Communication Rules

The quality of the topic decision depends on how it is communicated.

### Start from user problems, not author method names

- Start by aggregating high-frequency market problems, complaints, and substitute solutions.
- Then map the source material back to those problem clusters.
- A course is a solution to a market problem, not a renamed table of contents.
- After a topic is found, verify that the material contains enough high-quality knowledge points to deliver the solution credibly.

### Main and backup directions must be genuinely different

`1 main + 2 backups` does not mean three headline variations of the same idea.

Backup directions should differ from the main direction on at least one of:
- target audience
- topic angle
- teaching objective
- product form

If the difference is only wording, treat it as the same direction.

### Competitor analysis must answer the real buying question

Do not stop at names and links. For each competitor or substitute, explain:
- what problem it solves
- who it serves
- why people buy it
- what it does not solve
- where that leaves room for this topic

Then make one more comparison:
- what teachable kernel this material has that those competitors do not clearly provide
- whether that kernel is strong enough to support a course, not just a positioning sentence

Competitors are not limited to “similar courses.” They also include:
- tools
- free tutorials
- training camps
- platform features
- service substitutes

### Human-facing reports should not read like API output

If the report is meant for people rather than downstream systems:
- use natural language first
- avoid field-name overload, placeholder-style presentation, and excessive shorthand
- make the conclusion obvious on the first screen
- explain how the conclusion was formed on the second screen
- repeat the full topic name at key points rather than overusing vague references such as “this direction”

When helpful, produce two versions:
- a structured version for traceability and reuse
- a readable version for decision-making and communication

## Output Boundary

- Start with the strict evidence-based recommendation.
- Only provide an “expanded packaging version” if the user explicitly asks for it.
- Never set the course promise above the real evidence ceiling.
- For decision-oriented work, also include decision status, risks, evidence mapping, and a short validation plan.

## Valid Downgrade Paths

If the material does not support a full course, downgrade rather than forcing one:
- case breakdown
- experience sharing
- conceptual clarification
- method fragment
- observation report

Downgrading is not failure. It preserves truth.

## Failure Handling

When the material is weak, fragmented, or under-evidenced:
- say that the material is currently not strong enough for a competitive course topic
- or recommend the smallest version that still holds
- explicitly list what additional material would strengthen the recommendation
- do not invent method, proof, demand, or outcome claims to satisfy commercialization pressure
