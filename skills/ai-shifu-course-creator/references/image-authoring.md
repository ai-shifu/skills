# Image Authoring

Understand, upload, compose, embed, and validate image assets used by Teaching Prompts. Load this file only for tasks that actually use image assets.

Teacher avatars are platform metadata rather than Teaching Prompt image assets. Route avatar work to `course-management.md` and do not add it to `assets/image-manifest.json`.

## Required References

- `language-policy.md`
- `pedagogy.md#visual-text-coordination`
- `markdownflow.md#deterministic-blocks`
- `markdownflow.md#images`
- `cli/cli-reference.md#image-upload`
- `cli/course-directory-spec.md#assets`

## Conditional References

- When an image URL, alt, caption, or ordering was selected as immutable source content: `source-preservation.md`
- Immediately before uploading an image to the platform: `authentication.md`

## Asset Intake

Understand every image before choosing its lesson, position, or alt text:

- If the image is visible, identify in one sentence the concept, relation, or example it conveys.
- If only an opaque path or URL is available, ask the author for a one-sentence description or a semantically meaningful filename. Do not guess from an opaque filename.

When the selected route permits platform access and an upload is needed, complete `authentication.md` at this boundary, then upload local or remote assets with `shifu-cli.py upload-image`, always passing `--course-dir` and an informative `--alt`. An upload needs neither a course BID nor a title lookup or course creation. Use the exact resource URL returned by the selected deployment and the stored manifest record as the authoritative asset identity. If authentication or upload is deferred or fails, preserve local assets and report the blocked image and missing resource URL to the caller; do not fabricate a URL or pass Image Output Validation.

For explicitly local artifact-only work where upload is excluded, do not call `upload-image`. Use the authoritative URL and metadata supplied by the source record instead. Stop when that record lacks the remote URL, informative alt, or another field required by the selected image form; never invent a missing value from a filename.

## Image Composition

Raw SVG, HTML drawings, Mermaid, PlantUML, and Graphviz source are not image-embedding forms by default. Include raw graphic source only when the author explicitly requests it.

Choose one form after the visual intent is known:

| Authoring intent | Form |
| --- | --- |
| Display the uploaded image without layout customization | `===![informative alt](url)===` on its own line |
| Control width, alignment, caption, or multi-image layout | A natural-language HTML-view instruction |

For fixed display, write informative alt text. When an alt was selected as immutable source content, load `source-preservation.md` and retain it exactly. The deterministic line bypasses the Teaching Agent.

For HTML-view, keep the instruction outside deterministic markers and require the Teaching Agent to render each image with an HTML `<figure>` element and, when a caption is selected, a `<figcaption>` element. Encode every applicable image property below in natural language:

| Image property | Required instruction |
| --- | --- |
| Position | State where the image appears relative to the surrounding lesson content. |
| Resource | Use the exact URL returned by the selected deployment or supplied by the authoritative source record. |
| Semantic content | Describe the specific concept, relation, or example that the image conveys so the Teaching Agent can produce informative alt text. |
| Caption | Preserve the selected caption exactly and state whether it appears. |
| Layout | Describe alignment, width, grouping, and responsive behavior without fixed pixel values. |
| Ordering | Preserve the selected order when the view contains multiple images. |
| Aspect ratio | Preserve the original aspect ratio unless the approved design explicitly requires another treatment. |

The preservation wording constrains the Teaching Agent but is not parser-level locking.

## Image Output Validation

1. Build an expected-image record from `assets/image-manifest.json`, selecting the upload for the task's service under the provenance rules in `cli/course-directory-spec.md#assets`, then adding the selected form, caption, position, layout constraints, ordering, and aspect-ratio behavior. For explicitly local artifact-only work where upload is excluded, use the authoritative source record instead.
2. Stop before generation when the authoritative record lacks `remote`, informative `alt`, or a field required by the selected form.
3. Compare the generated Teaching Prompt with every expected record. Verify URL, description or alt, caption, position, layout constraints, ordering, aspect-ratio behavior, and form.
4. Regenerate only the affected image instruction or lesson when a field is missing, changed, duplicated, or reordered.
5. If the second comparison still fails, stop that lesson and report the mismatched fields as blocking. Do not finalize or hand off the Teaching Prompt.
