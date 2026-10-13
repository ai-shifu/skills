# Course Review and Repair

Review the available Teaching Prompts, Course Prompt, or learner-facing description and make repairs within the requested scope. The using agent decides whether review is needed and whether it is an audit, focused correction, or broader rewrite; this capability does not schedule authoring or platform operations.

Review teaching design, MarkdownFlow expression, or both according to the request. Platform readback and publication verification belong to the corresponding CLI capability rather than this content review.

## Available Scope

Work with one pasted Prompt body, selected files, or a complete course. Identify the version being reviewed when multiple candidates could differ. An absent companion artifact or source is a limit on what can be assessed, not a reason to invent an envelope or create unrelated content.

Use [course-review-checklist.md](course-review-checklist.md) for observable criteria relevant to the artifacts and requested scope. With authoritative source material, compare source coverage and required exact content under [source-preservation.md](source-preservation.md). Without it, assess the supplied content without claiming external-source fidelity.

## Review and Repair

- Prioritize factual correctness, source fidelity, runtime behavior, and learner impact over cosmetic polish.
- For an audit or focused fix, preserve existing meaning and information density and use the smallest coherent repair. A requested rewrite permits broader changes within the author's constraints.
- Teaching patterns, lesson sequences, visual cadence, interaction quotas, and optional source layouts are design choices; do not classify the absence of a preferred option as a defect.
- Audit-only work does not add navigation comments or normalize an existing Teaching Prompt's layout. A new or explicitly rewritten Prompt uses the mandatory source-only comments and an appropriate layout under [teaching-prompt.md](teaching-prompt.md).
- Do not introduce silent factual changes or omit required evidence. Explain consequential structural or content changes when repairing them.
- Recheck the behavior actually affected by an interaction, variable, branch, image, or deterministic-span change. Check available consumers when a shared value or course-wide instruction changes.

## Results

Report the conclusion and actionable findings at a level useful for the request. Distinguish actual defects, optional design suggestions, and checks that could not be assessed. Include locations and the reason for material repairs when helpful; no fixed report envelope, phase status, fallback mode, or exhaustive issue taxonomy is required.

An unverifiable source claim, absent companion, or unavailable metadata is `not-assessed`, never silently passed. Return only repairs in scope and make remaining correctness or runtime blockers clear. Human-facing output follows [language-policy.md](language-policy.md).
