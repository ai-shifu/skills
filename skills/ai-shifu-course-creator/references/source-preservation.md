# Source Preservation

Identify source material whose wording, values, order, or structure must remain exact and verify it after affected transformations. MarkdownFlow encoding belongs to [teaching-prompt.md#source-encoding](teaching-prompt.md#source-encoding).

## Preservation Decisions

Required code and fence languages, fixed numeric thresholds, regulated wording, quotations, tables, image URLs, alt text, and ordering may need exact preservation. Select the smallest spans whose exactness is required by the source or author; keep surrounding explanation adaptable.

- Honor explicit immutable content even when nearby text is localized.
- Do not freeze a whole lesson merely for convenience. An explicit requirement for exact content remains binding.
- Retain enough source information to verify a span, such as file and heading, page, line range, or a quotation. No formal segmentation record, character-offset map, or `preserve_block` field is required.
- Keep authoritative source content distinct from authoring assumptions and generated additions.

## Verification

Compare affected immutable spans with their source after authoring or repair. Verify applicable content, fence language, numeric value, URL, alt or caption text, order, and table structure. Check the runtime encoding when a change touches a deterministic or preserved span.

Missing, altered, duplicated, or incorrectly reordered required exact content is a correctness defect. Report an unverifiable span as uncertain rather than claiming source fidelity without evidence.
