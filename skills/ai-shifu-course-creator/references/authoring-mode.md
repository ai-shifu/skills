# Authoring Mode

Select one execution mode for each Segmentation, Orchestration, Generation, or Optimization run.

## Required References

None.

## Mode Selection

- **Standard mode** (default): Use when the input quality is sufficient. Run the selected phases with their standard schemas. Omit phase-specific fallback fields.
- **Fallback mode:** Use when the input is incomplete, conflicting, or low-quality. Produce coarse outputs, mark uncertainty explicitly, and give focused rerun hints. The selected phase owns its additive fallback fields; add them to its standard output.
