# Access and Scope Checks

Use this reference before analyzing creator-facing course data.

## Current permission model

For the current version of this skill, use the strictest simple rule:
- login check
- owner check
- evidence match check

Do not broaden this to collaborator or broader creator access unless the skill is explicitly updated later.

## 1. Login check

Before reading course analytics or using course-private data:
- confirm the user is authenticated
- if there is no authenticated user context, stop and ask for authenticated context or treat the task as offline-only analysis with no live course lookup

## 2. Owner check

For the current version:
- when the user asks to analyze a specific course by course id or `shifu_bid`, confirm that the current user is the owner of that course
- if owner status cannot be confirmed, do not continue as if access is valid
- if owner status is false, stop and explain that the current version only supports owner-level analysis

This is intentionally narrower than future collaborator-based access.

## 3. Evidence match check

When the user provides CSV, screenshots, exported tables, or offline analysis files:
- confirm that the evidence belongs to the same requested course
- check course name, course id, report title, chapter set, or other identifying markers when available
- if the evidence appears to belong to another course, stop and ask for clarification instead of blending mismatched evidence

## Allowed modes

### Live-course analysis
Require all three:
- authenticated user
- owner check passes
- evidence matches the course when offline files are mixed in

### Offline-only analysis
If the user only wants a draft analysis of manually provided files and does not ask for live system lookup:
- login check may be unavailable in practice
- owner check may be unverifiable in practice
- in that case, clearly mark the report as offline-only and unverified against live ownership

However, if the surrounding product flow is supposed to be creator-private, prefer authenticated owner-confirmed usage.

## Failure behavior

If any of the three checks fail:
- do not proceed as though the course is authorized
- do not infer hidden course data
- clearly state which check failed
- ask for corrected course identity or corrected evidence when necessary
