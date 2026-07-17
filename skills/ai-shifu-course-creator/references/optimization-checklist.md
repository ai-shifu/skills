# Optimization Checklist

Observable acceptance criteria for Optimization. Use each linked owner to interpret the rule; this checklist records `pass`, `fail`, or `not-assessed` without redefining that rule.

For a pasted content-only Prompt, run every check observable from the body and record any check that needs an unprovided schema envelope or metadata table as `not-assessed`; do not manufacture the missing wrapper.

## Required References

- `language-policy.md#language-audit`

## Conditional References

- When authoritative source material or selected immutable spans are in the audit scope: `source-preservation.md#verification`
- When a Teaching Prompt is in scope: `teaching-prompt.md#validation`
- When a Course Prompt is in scope: `course-prompt.md#materialization-checks`
- When a course description is in scope: `course-description.md#validation`
- When the audited artifacts use image assets: `image-authoring.md#image-output-validation`

## Coverage and Fidelity

- When authoritative source material is supplied, every critical source point in scope is represented and no unsupported addition changes its meaning.
- Meaning and information density observable in the supplied artifact remain intact after repair.
- When selected immutable spans are in scope, every span passes `source-preservation.md#verification`.
- A content-only audit does not claim coverage of or fidelity to an external source that was not supplied.

## Artifact Boundaries

- Teaching Prompts contain lesson method and flow; the Course Prompt contributes only course-wide role and presentation behavior.
- Chapter titles, lesson titles, numbering, hierarchy, and ordering remain in structure metadata rather than Teaching Prompt bodies.
- No artifact relies on another artifact to supply behavior that its owner requires locally.

## Teaching Prompt Behavior

- Each lesson resolves one core question through a complete loop and valid teaching pattern under `pedagogy.md`.
- The Teaching Prompt states executable intent and must-cover content without prewriting ordinary lecture prose or surface formatting that the runtime LLM can decide.
- No direction remains at the empty-outline level of "explain the concept", "add an example", or "ask a question" without the content, purpose, boundaries, or expected effect needed to execute it.
- No unnecessary transcript, fixed slide count, ready-made title sequence, uniform point quota, font or color choice, pixel coordinate, or animation constrains adaptive delivery.
- Removing over-scripted wording or unnecessary layout rules does not remove the core question, intended understanding, critical facts and boundaries, material teaching order, interaction purpose and visible effect, or closing result.
- Every resolved constraint island remains complete and exact under its owning MarkdownFlow authoring, source-preservation, or image-authoring rule; surrounding teaching remains adaptive.
- The first non-empty line teaches directly instead of repeating a heading or structure label.
- A heading used to teach Markdown syntax, a code comment beginning with `#`, or a heading explicitly permitted by the author is flagged for review rather than automatically deleted.
- Interaction presence, placement, selection type, feedback effect, and lesson close match the resolved interaction policy.
- Each action or carryover has the downstream use required by `pedagogy.md`.
- Pure-slide and standard visual-text behavior match `pedagogy.md#visual-text-coordination`.
- A schema-bearing Teaching Prompt item passes all of `teaching-prompt.md#validation`. A content-only Prompt body passes every observable body and runtime check there; its schema envelope is `not-assessed`.

## Interaction and Variable Safety

- Every interaction has the observable instructional effect and branch behavior selected by `pedagogy.md`.
- Each control, option set, input hint, assignment, and branch instruction passes `markdownflow-authoring.md#validation`.
- Every named variable has exactly one valid collection, complete supplied metadata, and a cross-lesson or Course Prompt consumer; lesson-local answers remain unnamed. Metadata checks are `not-assessed` when a content-only input does not supply the required table.
- The observed interaction and variable counts stay within `pedagogy.md` and `data-contracts.md`.
- Learner-facing content contains no unresolved authoring placeholder; runtime `UNKNOWN` behavior remains valid only where `markdownflow.md#variables` defines it.

## Runtime Stability

- MarkdownFlow syntax produces the observable effects defined in `markdownflow.md`.
- Deterministic and inline preservation forms match their selected scope.
- Code fences, required source spans, and applicable image records survive preprocessing and generation unchanged where required.
- When images are present, each one passes `image-authoring.md#image-output-validation`; when none are present, image authoring is not loaded or required.

## Course Prompt

- The existing Course Prompt keeps all six required sections in order and has no unresolved `XXX` placeholder.
- Every non-placeholder instruction remains behaviorally represented after localization.
- Standard and pure-slide delivery behavior matches `course-prompt.md`; lesson pedagogy is not duplicated there.
- The complete artifact passes `course-prompt.md#materialization-checks` and `prompt-contracts.md`.

## Course Description

- The existing description clearly states audience fit, course topic, and supported outcomes.
- It contains no authoring notes, workflow state, unsupported guarantee, Prompt content, or structure dump.
- The complete artifact passes `course-description.md#validation`.

## Language and Repair Scope

- Every applicable human-readable surface passes `language-policy.md#language-audit`, including effective build values when those are in scope.
- Each applied change is the smallest coherent repair and has a traceable rationale.
- Remaining gaps are reported with their risk and owner instead of being hidden by broad rewriting.
