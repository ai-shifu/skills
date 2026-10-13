# Source Analysis and Course Structure

Turn source materials, a brief, or an existing course into an understandable chapter and lesson structure. The using agent may analyze sources, propose boundaries, or revise structure independently; segmentation is an available technique, not a required phase before writing.

## Inputs and Representations

Work from the information available: documents, transcripts, topic notes, a supplied outline, existing Teaching Prompts, or a course directory. There is no required segment schema, fixed source type, or intermediate JSON.

For long or noisy material, semantic segments can help preserve traceability. Record a source file and heading, page, line range, quotation, or other locator sufficient to find important evidence. Code, images, and tables may be kept as coherent units. Exact-source decisions and verification belong to [source-preservation.md](source-preservation.md).

## Structure Design

- Choose lesson boundaries around teachable questions, skills, or outcomes rather than heading depth alone. A single core question is useful when it makes a lesson coherent; it is not a universal quota.
- Choose chapter grouping, lesson granularity, and ordering for the audience, prerequisites, source relationships, and requested result. Honor explicit ordering and count constraints.
- When reconstructing an existing course faithfully, preserve its required coverage and ordering. When restructuring is requested or useful within the task, keep required facts and source relationships intact and make consequential rearrangements clear.
- Keep required source points and immutable spans represented. Do not drop difficult material merely to fit a lesson count.
- Separate uncertainty in the source from a design choice. Identify missing evidence or conflicting constraints without inventing source claims; a useful draft may state its assumptions.

[teaching-design.md](teaching-design.md) offers teaching approaches. [course-design-choices.md](course-design-choices.md) explains author-facing choices when clarification would help.

## Results and Checks

Return the requested structure at the useful level of detail: chapter and lesson titles, objectives or core questions, source associations, and unresolved assumptions where relevant. The caller decides whether it needs an outline, a local `structure.json`, or information for another capability. The actual directory format belongs to [cli/course-directory-spec.md](cli/course-directory-spec.md).

Check coherence, requested source coverage, explicit counts and order, and exact preservation within the affected scope. Do not generate Teaching Prompts, cross-lesson tables, or a phase report merely because a structure was requested.
