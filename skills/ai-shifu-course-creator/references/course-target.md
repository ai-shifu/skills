# Course Target Resolution

## Required References

- `authentication.md`
- `language-policy.md`
- `cli/cli-reference.md#query-commands`

## Resolve the Target

Resolve whether the operation targets a new course or one existing platform course before any course architecture or lesson content is proposed. The platform database is the source of truth even when the user explicitly asks for a new course.

1. Identify the user's intent as **create** or **edit**.
2. Run `find-title <keyword>` with a targeted title keyword. Do not replace this search with an unfiltered `list`.
3. Resolve the result:
   - Create intent with no match: resolve **new course**.
   - Create intent with one or more matches: ask whether to edit a matching course or create a separate course. If several matches could be edited, ask which one only after the user chooses the existing-course branch.
   - Edit intent with one match: resolve that **existing course** without asking whether to create a new one.
   - Edit intent with several plausible matches: ask which course to edit.
   - Edit intent with no match: explain that no current title matches, then resolve **new course** so the requested work can create it.
4. Record the resolved kind (`new` or `existing`), exact course title, and, for an existing course, its Shifu BID.

Write match summaries, choice questions, and no-match explanations according to `language-policy.md`. Preserve titles, Shifu BIDs, paths, and CLI commands verbatim.

## Output

Return the resolved kind (`new` or `existing`), exact title, and any resolved Shifu BID. Target resolution does not pull, author, create, or mutate a course.
