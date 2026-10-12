# Course Description

Create and validate the learner-facing SEO and listing description for a course. This file owns only the description artifact; it does not define course structure, lesson pedagogy, Prompt behavior, or deployment metadata precedence.

## Authoring

Derive the description from the available course topic, target learner, prerequisites, learning goal, and concrete outcomes. These may come from the request, source, existing content, or current design; no prior authoring phase or separate approval is required. State what the learner will understand or be able to do using supported claims.

- Write complete learner-facing prose in the language resolved under [language-policy.md](language-policy.md).
- Make the opening specific enough to work as listing copy and search-result context.
- Prefer concrete outcomes and audience fit over workflow terminology or generic praise.
- Keep author-side assumptions, issue notes, implementation details, and deployment status out of the description.
- Do not copy the Course Prompt, lesson sequence, or structure metadata into the description.

## Output

Return the requested learner-facing prose. When materializing a course directory, write it to `course-description.md` under [cli/course-directory-spec.md](cli/course-directory-spec.md). A separate output envelope is not required.

## Validation

- The target learner, course topic, and concrete outcomes are clear.
- Every substantive claim is supported by the source or course content and respects explicit author constraints.
- The complete artifact passes `language-policy.md`.
- No authoring notes, unresolved placeholders, unsupported guarantees, or machine-facing metadata appear.
