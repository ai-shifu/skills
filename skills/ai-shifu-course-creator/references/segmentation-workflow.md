# Segmentation Workflow

Turn course source material into traceable semantic segments and lesson-boundary candidates. This file does not orchestrate downstream generation.

## Required References

- `language-policy.md`
- `authoring-mode.md#mode-selection`
- `data-contracts.md#source-spans`
- `source-preservation.md`

## Inputs

Provide one of:

- A single long transcript or course document.
- A set of topic-aligned documents with intended order.

Input files must be readable text or Markdown. When multiple files are provided, their order must be explicit.

## Segment Schema

Each Segmentation item contains:

- `segment_id` (string, required) — stable within the run.
- `segment_type` (string enum, required) — one value from [Segment Types](#segment-types).
- `core_point` (string, required) — the single teachable point.
- `preserve_block` and `source_span` — required shared fields defined in [Source Spans](data-contracts.md#source-spans).
- `transfer_signals` (object, required) — satisfies [Transfer Signals](#transfer-signals).

### Segment Types

| Value        | Meaning                                   |
| ------------ | ----------------------------------------- |
| `concept`    | Explanatory statements and definitions.   |
| `example`    | Concrete demonstrations and walkthroughs. |
| `code`       | Executable or pseudo-code blocks.         |
| `image`      | Image files and their source references.  |
| `exercise`   | Learner action prompts.                   |
| `transition` | Bridge text that links ideas.             |

### Transfer Signals

`transfer_signals` must be non-empty. Include every applicable canonical key, omit inapplicable keys, and give every included key a non-empty, concise string value.

| Key | Meaning |
| --- | --- |
| `learner_hook` | Teaching entry point. |
| `evidence_type` | Form of source evidence. |
| `visual_cue` | Cue for expressing the segment as a slide. |
| `concept_conflict` | Conceptual conflict or misconception. |
| `boundary_cue` | Applicability boundary. |
| `action_cue` | Executable application. |
| `density_cue` | Information that must not be compressed away. |
| `quote_cue` | Quotation that should be preserved or used. |
| `visual_text_pair_cue` | Division of work between slide and text. |
| `interaction_intent_cue` | Interaction purpose and expected instructional effect. |
| `compare_cue` | Comparison objects or dimensions. |

## Segmentation

### Segmentation Methodology

#### Objective

Produce stable lesson-oriented semantic segments from noisy source material while preserving immutable artifacts.

#### Core Rules

1. Preserve source order unless explicit ordering hints are provided.
2. Keep each code block, image reference, and table block as one traceable source span. Apply `source-preservation.md` and set `preserve_block` before Teaching Prompt generation.
3. Segment by semantic shift, not heading depth alone.
4. Keep each lesson candidate centered on one teachable question.
5. Attach source spans to every segment.

#### Failure Handling

If structure is weak, output a fallback segmentation, mark uncertain spans, and provide focused rerun hints using [Segmentation Fallback Fields](#segmentation-fallback-fields).

### Outputs

Produce a segment list that conforms to [Segment Schema](#segment-schema), including its canonical segment types and transfer signals, plus workflow-local lesson-boundary candidates with one core question each.

At Segmentation handoff, summarize the source files, execution mode, total segment count, and lesson-boundary candidates. Summarize the results of [Validation](#validation), including immutable-block preservation. If issues remain, include blockers, non-blocking suggestions, focused rerun hints, and downstream handoff notes.

Apply `language-policy.md` to the complete Segmentation output.

### Validation

- Segment output covers all valid source spans in traceable order.
- Every segment passes [Segment Schema](#segment-schema).
- The preservation and one-core-question rules in [Core Rules](#core-rules) pass; each immutable span is marked according to `source-preservation.md`.

## Segmentation Fallback Fields

Per segment:

- `uncertainty` (string enum `low|medium|high`) — confidence in the segment's interpretation.

Top-level:

- `rerun_hints` (array of strings) — focused prompts describing the authoritative input needed to resolve uncertainty.
