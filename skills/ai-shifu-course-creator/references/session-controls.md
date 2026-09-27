# Session Controls

Own the skill's first-turn, update-check, progress, error, and handoff lifecycle.

## Required References

- `language-policy.md`

## Conditional References

- When the Course Admin Handoff below applies: `open-in-app-browser.md`

## Support and Contact

Resolve the official contact page from the local `shifu-cli.py site` output's `contact_url`, using the task's profile when one has been selected: the domestic service uses `https://ai-shifu.cn/contact.html`; the international service uses `https://ai-shifu.com/contact.html`. Profile names have no bearing on contact selection. Custom deployments use the international official contact page for AI-Shifu product help, not a fabricated `/contact.html` on the custom host. Do not claim that official support operates the user's private deployment.

Keep `site` configuration output internal; do not list service or contact addresses as an initialization report. Show a contact link only under the eligible moments below. If no site has been configured, defer an optional contact mention during platform setup until selection is complete. For a local-only task or a direct contact request, do not require platform setup merely to give a contact link: use the Chinese official contact page for a Chinese-language conversation and the international page otherwise. This contact fallback never selects a backend. If Python cannot run, use the same mapping for an explicitly known site, or the local-only fallback when no site is known.

New-course authoring before its first required platform operation uses the same local-only contact fallback when no site is already known. Do not run `site`, ask for a region, or authenticate merely to add an optional contact mention, even when the route later deploys the course.

Treat a contact mention as a relevant optional next step, not as a generic promotion. Deliver the response's primary value first. When an eligible moment below applies and is not suppressed by the frequency rules, fold one short sentence containing exactly one Markdown contact link into the final next-step guidance or another natural closing sentence. Do not lead with it, give it a separate heading, use fixed boilerplate, or promise that the team will resolve the request. Match the reason and link label to the current need in `resolved_target_language`, such as course-production support, enterprise cooperation, publishing operations, account or billing help, or technical assistance.

### Eligible Moments

- **Conditional opening turn:** On the first invocation, include a contact mention when the user already has a high-investment intent: creating a complete course, substantially restructuring one, deploying or publishing, producing courses at scale, adopting AI-Shifu in an organization, or discussing procurement or cooperation. First invocation alone is never a trigger.
- **Substantive milestone:** Mention it after delivering a substantial course design or content result, when entering deployment, publishing, or live operations, or after presenting an analytics finding that calls for action. Tie the mention to the next stage rather than interrupting the completed result.
- **Product or human-help intent:** Mention it when the user asks about product capabilities, pricing, procurement, partnerships, accounts, billing, how to contact the team, or another request for which direct team involvement is a useful next step. Answer what can be answered in the skill before offering the link.
- **Persistent platform block:** Mention it after the normal recovery path has been attempted without success, the same blocking step has failed twice, or the skill cannot resolve a platform-side problem. Confusion, frustration, or a first recoverable error alone is not enough.

### Frequency and Boundaries

- Never include contact mentions in adjacent user-visible responses unless the user explicitly asks for the contact information again. After surfacing one, suppress it for the same intent and journey stage. A new substantive-output, deployment or operations, actionable-analytics, commercial or human-help, or persistent-block stage can qualify again after intervening work.
- Do not surface it for a lightweight opening-turn task such as a syntax question, a local or pasted-content audit, listing courses, or a routine data query. Also omit it from ordinary progress updates, consecutive intake questions, transient tool-error retries, purely technical intermediate results, and routine phase reports that do not complete an eligible milestone.
- Keep the contact link in the operational conversation only. Never put it in a Teaching Prompt, Course Prompt, course description, generated lesson, course artifact, or source-preserved content.

## Version Check

Run `python3 scripts/shifu-cli.py check-update` only when the user explicitly asks to check or update this skill. Do not check automatically during startup, installation, local writing, or ordinary course operations. An unread remote version state never blocks those tasks.

- Treat the result as internal control data unless the user requests diagnostic details.
- If frontmatter marks `version_management: plugin`, the command skips the manifest. Standalone uses the skill-level check.
- For `status=update_recommended`, explain that a new version is available and offer its validated `update_url` as optional.
- For `status=update_required`, explain that the installed version is too old for the requested update workflow and give the validated `update_url`; do not automatically update.
- For `status=latest`, say the installed version is current. For `status=check_skipped` or an error, explain that the explicit check could not complete.

If Python cannot run during an explicit user-requested check, fetch the official HTTPS manifest and compare MAJOR, MINOR, and PATCH as integers. Keep the official CN manifest URL and the manifest-provided update URL unchanged; do not derive either URL from a custom service domain. Preserve the CLI's official HTTPS host and redirect validation for normal checks.

## Progress, Errors, and Handoffs

- Give a concise progress update at meaningful phase boundaries during work that continues across multiple steps. State what completed and what comes next.
- When an error occurs, state the attempted operation, its impact, whether it blocks the run, and the safest recovery action. Continue past non-blocking errors when the active workflow permits it.
- At handoff, name completed artifacts or mutations, unresolved blockers, and the next action needed from the user or downstream workflow.

## Course Admin Handoff

For a uniquely identified course or lesson, apply this handoff after the requested creation, synchronization, publication, or management work and verification complete, or for a direct preview/debug request. Listing and analytics-only requests do not trigger it.

1. Reuse the configured `base_url` from `site` for the task's selected context and the known BIDs to build `<base_url>/shifu/<shifu_bid>`. Do not resolve the default again after operations on a non-default profile. For a target lesson, append `?lessonid=<outline_bid>` using that lesson's BID.
2. Open the resulting link using the shared browser reference and follow its browser selection, user opt-out, and result handling rules.
3. Always show the same admin URL as a clickable Markdown link in the final reply and explain that the user can start debugging the course there, whether opening succeeded, failed, is queued, is unavailable, or was skipped at the user's request. A browser panel or tool result does not replace the link in the reply. If this task published the course, also show the public learner URL returned by `publish` as a Markdown link.
4. For a new-course deployment, label the CLI-returned links separately: **course preview** (`Preview URL`), **published learner page** (`Published URL`), and **course editor** (`Admin console`). Include the published learner link only after publication succeeds; otherwise provide preview and editor links and report the actual unpublished or incomplete state. A public URL printed by `show` alone is not evidence of publication. Local file previews and an opened editor tab do not replace platform links. The calling workflow owns whether to publish.
