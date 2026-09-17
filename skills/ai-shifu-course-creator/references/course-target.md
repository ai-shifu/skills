# Course Target Resolution

## Required References

- `authentication.md`
- `language-policy.md`
- `cli/cli-reference.md#query-commands`

## Preconditions

The calling route has selected an existing-platform-course operation and completed authentication. This reference identifies the course; it does not classify the overall task, pull content, author, or mutate a course.

## Resolve Existing Course

1. For an explicit Shifu BID, run `show <shifu_bid>` to verify access and read the current title. If it succeeds, resolve that **existing course** and skip title matching. If it fails, keep the target unresolved and report the CLI error; do not substitute another course or create one.
2. Otherwise, obtain a targeted title keyword from the request, or ask for a course name or link if absent. Run `find-title <keyword>`; do not replace this search with an unfiltered `list`.
3. One match resolves the existing course. Several plausible matches require the user to select one. With no matches, report the no-match result to the calling route and leave the target unresolved.
4. For a uniquely resolved course, record kind `existing`, its exact platform title, and its Shifu BID.

Write match summaries, choice questions, and no-match explanations according to `language-policy.md`. Preserve titles, Shifu BIDs, paths, and CLI commands verbatim.

## Output

Return kind `existing`, the exact title, and the Shifu BID for a uniquely resolved course; otherwise return the unresolved lookup result or error. The caller owns any subsequent choice to create a new course.
