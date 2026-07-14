# Prompt Contracts

These seven cross-artifact red lines apply whenever a route writes, rewrites, or audits a Teaching Prompt or Course Prompt. Detailed syntax, strategy, schema, and delivery behavior remain with the linked owner.

The base Course Prompt structure and its course-level boundaries remain in [Course Prompt](course-prompt.md); these red lines only coordinate constraints shared with Teaching Prompts.

1. **Teaching Prompts are model-guiding scripts, not learner manuscripts or visible author scaffolding.** Apply `pedagogy.md#script-style`.

2. **Interaction prompts stay outside `?[]`, interaction content stays inside, and every interaction occupies its own line.** Apply `markdownflow.md#interactions` and `markdownflow.md#input-marker-rules`.

3. **Interaction presence, purpose, and type follow the normalized policy.** Validate the shape through `data-contracts.md#interaction-policy`, then apply `pedagogy.md#interaction-policy-precedence` and `pedagogy.md#interaction-design`.

4. **A named learner-answer variable requires a variable-backed interaction, matching metadata, and intentional course-level or cross-lesson use; lesson-local answers use no-variable syntax.** Variable strategy is authoritative in `pedagogy.md#variable-strategy`, runtime substitution in `markdownflow.md#variables`, and metadata shape in `data-contracts.md#variable-table`.

5. **Visual output follows the normalized delivery mode, mode-independent teaching relationship, and valid MarkdownFlow image form.** Apply `delivery-modes.md`, `pedagogy.md#visual-text-coordination`, and `markdownflow.md#images`. Raw SVG, HTML drawings, Mermaid, PlantUML, or Graphviz source appears only when the author explicitly requests that raw format.

6. **Structural metadata stays outside Teaching Prompt bodies.** Chapter titles, lesson titles, hierarchy labels, and ordering markers belong in `structure.json` or `course_index`; the first paragraph must start teaching rather than display directory structure or repeat a source heading.

7. **Resolve output language before creating user-visible text or course artifacts.** Apply `session-controls.md#output-language` and `session-controls.md#canonical-term-translation-table`; the routed finalization workflow performs the observable pre-deploy audit.
