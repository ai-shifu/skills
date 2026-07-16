# Optimization Workflow

## Optimization

Audit and improve existing Teaching Prompts (and the Course Prompt). This phase is not for writing from scratch.

### When to Use

Use Optimization when existing Teaching Prompts or a Course Prompt need audit and targeted improvement — gap analysis against source, quality upgrades through controlled rewriting, and lower runtime failure risk. Not for from-scratch authoring.

### High-Standard Constraints

Apply Optimization audits against artifact-specific constraints:

- Teaching Prompt pedagogical constraints (interaction-policy effects, variable strategy, interaction design, visual-text coordination, and lesson loop): `pedagogy.md#interaction-policy-precedence`, `pedagogy.md#variable-strategy`, `pedagogy.md#interaction-design`, `pedagogy.md#visual-text-coordination`, and `pedagogy.md#lesson-loop`.
- Course Prompt responsibility and presentation-layer boundary: `prompt-contracts.md#artifact-responsibilities`; materialization checks: `course-prompt.md#materialization-checks`.
- Interaction-policy shape and enums: `data-contracts.md#interaction-policy`.
- Syntax / runtime constraints (preservation, deterministic blocks, variable references): `markdownflow.md`.
- Observable audit checks: `review-checklist.md`.

### Optimization Methodology

#### Principles

1. Correctness before style.
2. Minimal safe edits before broad rewrites.
3. Learner impact before formatting polish.
4. Traceable changes with explicit rationale.

#### Content Fidelity and Controlled Rewriting

- Preserve source coverage, intended meaning, information density, non-negotiable fragments, and immutable assets. Do not trade substance for fluency.
- Keep immutable code blocks and fence languages, image URLs, alt text and ordering, regulated wording, fixed numeric thresholds, required quotes, and table blocks intact.
- Prefer targeted edits that repair the identified issue while leaving unaffected content intact.
- Allowed targeted rewrites include filler removal, sentence smoothing, and structural reorganization for lesson clarity when the fidelity constraints above still pass.
- Never introduce a silent factual change or an unmarked omission of required source evidence.
- Broaden a rewrite only when a smaller edit cannot resolve the issue coherently. Keep the rewrite within the declared scope, record its rationale, and revalidate the affected source-to-Prompt coverage afterward.

#### Issue Taxonomy

- Coverage gap
- Meaning shift
- Explanation clarity
- Interaction no-branching (only for a viewpoint or path-choice interaction whose answer should drive distinct next steps, or when `require_branching_feedback` explicitly requires branching)
- Visual requirement missing
- Variable or syntax risk

Other instructional interactions satisfy their effect requirement through immediate feedback or another visible current-lesson effect; they do not require option-by-option branching.

#### Execution Sequence

1. Define scope (single lesson vs full course); if multiple script versions exist, declare the authoritative one before editing.
2. Build a source-to-Prompt coverage matrix.
3. Run the full audit per `review-checklist.md` and classify findings with the [Issue Taxonomy](#issue-taxonomy).
4. Rank issues by learner risk and runtime risk.
5. Fix blockers first, applying the [Content Fidelity and Controlled Rewriting](#content-fidelity-and-controlled-rewriting) rules.
6. Revalidate variable lifecycle and every interaction effect that is present.
7. Run final syntax and density checks.

### Course Prompt

Optimization also produces a course-level `course_prompt` artifact when input includes course material. Generate it by **copying and filling `course-prompt.md#fillable-template`, not by free-form composition**. Preserve the six sections, their order, and every non-placeholder instruction; replace every `XXX` with course-specific content and render the result in the resolved output language.

Load and apply `prompt-contracts.md#artifact-responsibilities` before materializing the Course Prompt; Optimization does not reinterpret that boundary.

Auto-fill placeholders from existing artifacts (`course_author_name`, `course_profile`, `delivery_constraints`, resolved target language per `data-contracts.md#language-resolution`, and relevant [Segmentation transfer signals](data-contracts.md#transfer-signals)). The Role must use the course author's real name; if `course_author_name` is missing, ask the author instead of inventing a persona.

### Validation

- Conclusion and overall risk level presented first (report structure per `report-template.md`).
- Full review against `review-checklist.md` passes, or remaining gaps are explicitly listed as non-blocking suggestions.
- Coverage, meaning, information density, and immutable source content remain intact; every broader rewrite is scoped, justified, and revalidated.
- A `course_prompt` artifact is produced when input includes course material, with all six required canonical sections present.
- Generated `course_prompt` has no unresolved `XXX`, retains every non-placeholder template instruction, and applies delivery-mode behavior consistent with the Course Design Intake.
