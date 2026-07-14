# Course Target Resolution

## Resolve the Course Target

This workflow is mandatory before course creation, course-content editing, or deploy-only work. Read and complete `authentication.md` first.

**This runs first for every course-creation or editing request — before
Orchestration, before proposing any course architecture/outline, before writing a
single lesson.** The AI-Shifu platform DB is the single source of truth; you must
know whether you are creating a brand-new course or editing an existing one
*before* you invest in authoring. **Do NOT jump straight to a course outline or
"架构方案".** Even when the user clearly says "make a new course", first check the
cloud for an existing one.

1. **Recognize intent** — new course, or edit an existing one?
2. **Check whether a related course already exists** — run
   `shifu-cli.py find-title <keyword>` (targeted title search; do **not** dump the
   whole `list`).
3. **Branch:**
   - **New intent + a match exists** → **ASK the user**: edit that existing course, or create a separate new one? *Edit it* → `pull <bid> --course-dir <dir>` and resolve an existing target; *Create new* → resolve a new local target.
   - **New intent + no match** → resolve a new local target.
   - **Edit intent + a match exists** → `pull <bid> --course-dir <dir>`, then edit locally. **Do NOT ask** new-vs-edit; if several match, only resolve *which* one.
   - **Edit intent + no match** → resolve a new local target and record that no existing BID was found.

## Resolved Target State

Only after the branch above is complete, record the state that downstream work consumes:

- `target_kind`: `new` or `existing`.
- `matched_bid`: the selected BID for an existing course, otherwise `null`.
- `course_dir`: the pulled directory for an existing course or the planned local directory for a new course.
- `source_state`: `pulled_cloud_copy` for an existing course or `new_local_course` for a new course.

Hand this resolved state to the selected downstream route. Existing-course authoring must build on the pulled cloud copy; new-course authoring starts from the planned local directory.
