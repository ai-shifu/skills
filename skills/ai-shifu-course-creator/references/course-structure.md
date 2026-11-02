# Source Analysis and Course Structure

Turn source materials, a brief, or an existing course into an understandable chapter and lesson structure. The using agent may analyze sources, propose boundaries, or revise structure independently; segmentation is an available technique, not a required phase before writing.

## Inputs and Representations

Work from the information available: documents, transcripts, topic notes, a supplied outline, existing Teaching Prompts, or a course directory. There is no required segment schema, fixed source type, or intermediate JSON.

For long or noisy material, semantic segments can help preserve traceability. Record a source file and heading, page, line range, quotation, or other locator sufficient to find important evidence. Code, images, and tables may be kept as coherent units. Exact-source decisions and verification belong to [source-preservation.md](source-preservation.md).

## Structure Design

- Choose lesson boundaries around teachable questions, skills, or outcomes rather than heading depth alone. A single core question is useful when it makes a lesson coherent; it is not a universal quota.
- Choose chapter grouping, lesson granularity, and ordering for the audience, prerequisites, source relationships, and requested result. Honor explicit ordering and count constraints.
- Choose genuine learning dependencies rather than copying an expert's work sequence automatically. Independent modules may stay parallel; a low-cost first draft can precede deeper instruction when the necessary prerequisites are available. Use a learner's existing draft or result as an entry point where it serves the goal, rather than forcing a restart.
- Increase task complexity, independence, and transfer distance in relation to available performance evidence and support. Return from prerequisite help to the original task or an appropriate equivalent. Course-level orientation and integration can connect the whole experience without becoming repeated openings and closes in every lesson.
- When reconstructing an existing course faithfully, preserve its required coverage and ordering. When restructuring is requested or useful within the task, keep required facts and source relationships intact and make consequential rearrangements clear.
- Keep required source points and immutable spans represented. Do not drop difficult material merely to fit a lesson count.
- Separate uncertainty in the source from a design choice. Identify missing evidence or conflicting constraints without inventing source claims; a useful draft may state its assumptions.

[teaching-design.md](teaching-design.md) offers teaching approaches. [course-design-choices.md](course-design-choices.md) explains author-facing choices when clarification would help.

## Results and Checks

Return the requested structure at the useful level of detail: chapter and lesson titles, objectives or core questions, source associations, and unresolved assumptions where relevant. The caller decides whether it needs an outline, a local `structure.json`, or information for another capability. The actual directory format belongs to [cli/course-directory-spec.md](cli/course-directory-spec.md).

Check coherence, requested source coverage, explicit counts and order, and exact preservation within the affected scope. Do not generate Teaching Prompts, a separate cross-lesson planning table, or a phase report merely because a structure was requested.

### Outline Presentation

When showing a course outline to the teacher, include a concise teaching-strategy entry for every lesson shown. For a strategy established by the available material or proposed within the user's requested scope, name the approach and describe the concrete teaching action and how it serves that lesson's goal; a method label alone is insufficient. For example: "Compare a discussion record with a decision record to make the missing owner and deadline visible." A table or lesson list is sufficient; no new planning artifact is required. Follow [approach selection](teaching-design.md#selecting-an-approach-for-the-learning-task) and [method attribution](teaching-design.md#method-attribution) for recommendations and their sources.

Reuse confirmed teaching choices. For an existing course, ground each summary in the available Teaching Prompt or design material rather than inferring a strategy from the title alone. Mark unsupported or unresolved strategies as not yet established; this entry needs no approach or teaching action, and a read-only summary must not add a new design. Distinguish any proposed change from the course's current design.
