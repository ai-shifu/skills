# Image Assets

Authoritative cross-phase workflow for inspecting, uploading, embedding, and validating author-provided image assets. This file coordinates those stages without redefining image syntax, teaching placement, delivery-mode behavior, authentication, or CLI flags owned by the linked references.

## When to Apply

Apply this workflow when the author supplies a local image file or remote image URL, when an existing lesson contains an external or invented image URL that must be repaired, or when any later phase changes an image-bearing lesson. An already-valid platform resource needs no upload or new manifest entry; if a manifest entry already exists, confirm that it remains consistent, but do not add work merely because another phase reads or deploys the lesson.

Complete [Authentication](authentication.md) before an upload. The calling authoring or deployment route remains responsible for authentication and course-target resolution.

## Inspect

Understand each image before choosing its lesson, position, or alt text.

- When the image is visible in the conversation and the model can inspect it, summarize in one sentence the concept, relationship, or example it conveys, then choose its lesson and position through `pedagogy.md#visual-text-coordination`.
- When only a file path or URL is available, or the model cannot inspect images, stop and ask the author to provide a one-sentence description for each image or rename each file to a semantically meaningful name. Do not infer content from an opaque filename, and do not continue until one of those descriptions is available.

## Upload

When the input is already a valid platform resource, preserve it without uploading. Otherwise upload through `shifu-cli.py upload-image` using the complete local-or-remote command contract in `cli/cli-reference.md#image-upload`.

- Supply the source, course directory, and inspected semantic description through the forms owned by that command interface.
- Capture the exact stdout URL and resulting course-directory manifest entry returned by the command.
- Never invent a platform URL and never embed an external source URL directly.

## Embed

Embed the returned platform URL through `markdownflow.md#images`.

- Choose the default MarkdownFlow image form unless an explicit layout requirement needs one of the advanced forms owned by the syntax contract; do not reproduce or alter that contract here.
- Choose placement and the standard visual-text relationship through `pedagogy.md#visual-text-coordination`, then apply any cross-artifact explanation override from the already resolved profile in `delivery-modes.md`.

## Validate

Before returning the asset handoff, verify all of the following:

- Every newly embedded resource uses the exact URL returned by `upload-image` and matches the platform resource shape defined by `markdownflow.md#images`; no local path, external source URL, placeholder, or invented platform URL remains.
- For a resource uploaded by this workflow, the course-directory manifest entry points from the original local path or source URL to that same platform URL and retains the inspected semantic alt text.
- For a preserved existing platform resource, the URL still matches the platform resource shape and the embedding remains valid; the absence of a local manifest entry is not a failure.
- The chosen MarkdownFlow image form satisfies `markdownflow.md#images`, including deterministic wrapping or instruction-style layout locks as applicable.
- The lesson position and any required standard visual-text explanation still match the inspected meaning and the resolved delivery profile.

## Handoff

Return whether the resource was preserved or uploaded, the exact platform URL, semantic alt text, selected embedding form, and lesson position to the calling phase. Include the manifest entry when an upload occurred or one already exists. The caller must preserve this handoff unchanged unless the author changes the image, its meaning, or its intended layout.
