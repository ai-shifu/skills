# Repository Instructions

## Git Commit Message Requirements

- Subject: use English Conventional Commits without scope parentheses, such as `type: summary`; do not use `type(scope): summary`. Write the summary in plain language that product users can understand. When a change affects users, describe the user-visible outcome or benefit instead of only naming the internal implementation detail.
- Body: include exactly two sections, `Changed:` and `Benefit:`.
- Classification: use `chore` for repository-maintenance-only instructions, guidance updates like this file, or non-behavioral skill maintenance.
- Skill content changes affect skill behavior and capability: inside a skill directory, only changes limited to intentionally present `README*` files count as documentation-only. Changes to `SKILL.md` (including its frontmatter), references, prompts, templates, examples, scripts, or other skill assets must use `feat` when adding capability and `fix` when correcting behavior; do not use `docs`.

Example:

```text
chore: centralize commit message requirements

Changed:
Moved repository commit message requirements into the root AGENTS.md file.

Benefit:
Contributors have one place to check the required commit title and body format.
```

## Skill Content Rule

- Do not use the abbreviation `MDF` anywhere in a skill document (including frontmatter); always write `MarkdownFlow` in full. Exception: a skill's `description` frontmatter field may include `MarkdownFlow (MDF)` once for discoverability, so users searching for `MDF` still find the skill.

## Workflow Ownership and Change Scope

- Callers own **when and why to invoke a capability**, including task routing, phase order, and invocation conditions. Called references own **how to perform that capability**, including inputs, operations, outputs, validation, and local error handling. Do not make a called reference redispatch the overall task or decide what its caller should do next.
- A capability may call another capability required for its own work. For example, image upload may invoke authentication before uploading; `authentication.md` explains how authentication works, while its callers decide when it is needed.
- Give each rule one canonical owner. Consumers should use its result or cite the owning reference instead of repeating its policy. Reporting and handoff code should reflect actual execution results, not decide again whether an operation should have run.
- Keep simple checkpoints, such as a deployment confirmation, as steps in the owning workflow. Do not introduce a separate file, abstraction, or additional branch merely to package a few lines of instructions.
- For a scoped workflow change, compare against the repository baseline and preserve unrelated behavior. Changing authentication timing must not silently change authoring steps, default publication, delivery links, or confirmation requirements in other workflows. Update only the relevant callers and their necessary integration and regression checks.
