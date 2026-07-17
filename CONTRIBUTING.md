# Contributing to ai-shifu-skills

## Scope

This repository hosts reusable AI-Shifu skills for MarkdownFlow course production.

## Before You Open a PR

1. Keep each skill under `skills/<skill-slug>/`.
2. Ensure the skill contains:
   - `SKILL.md`
   - `agents/openai.yaml`
   - `skill.yaml`
3. Keep metadata and docs aligned:
   - `SKILL.md` describes capability and trigger context.
   - `agents/openai.yaml` provides UI-facing metadata.
   - `skill.yaml` defines machine-readable skill contracts.
4. Use international English across all skill artifacts:
   - `SKILL.md`, `agents/openai.yaml`, `skill.yaml`, `examples/`, and `references/`.
   - Do not introduce Han-script content into skill artifacts.
5. Run local checks:

```bash
python3 scripts/validate_skill_quality.py
```

## PR Quality Bar

1. Prefer small, focused PRs.
2. Explain why the change is needed and which skill(s) are affected.
3. Include sample input/output when skill behavior changes.
4. Avoid breaking existing skill slugs unless migration notes are included.

## Reporting Issues

Open a GitHub Issue with:

1. skill slug
2. expected behavior
3. actual behavior
4. reproducible input
