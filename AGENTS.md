# Repository Instructions

## Git Commit Message Requirements

- Subject: use English Conventional Commits without scope parentheses, such as
  `type: summary`; do not use `type(scope): summary`.
- Body: include exactly two sections, `Changed:` and `Benefit:`.
- Classification: use `chore` for repository-maintenance-only instruction or
  generated guidance updates like this file.
- Skill content changes affect skill behavior and capability: inside a skill
  directory, only `README*` files count as documentation-only surfaces. Changes
  to `SKILL.md`, frontmatter other than README metadata, references, prompts,
  templates, examples, scripts, or other skill assets must use `feat` when
  adding capability and `fix` when correcting behavior; do not use `docs`.

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
