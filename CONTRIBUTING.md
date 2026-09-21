# Contributing to ai-shifu-skills

## Scope

This repository hosts reusable AI-Shifu skills for MarkdownFlow course production and the tools used to build and publish their channel packages.

Business skills live under `skills/`. Maintainer tools live under `tools/`; the release workflow is in `tools/ai-shifu-skill-release/` and is not a bundled business skill. See its [README](tools/ai-shifu-skill-release/README.md) for build and release instructions.

Use English for tool code, comments, CLI messages, maintainer documentation, and release skill metadata. Preserve localized channel prompts, display copy, platform-required values, matching rules, and corresponding test data. Do not translate package content as part of engineering-only maintenance.

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
python3 -m unittest discover -s tests -p "test_*.py"
```

Run the release tool suite separately from its own directory so its `scripts` imports do not collide with repository-level modules. The tool requires Python 3.11+ and Git; its tests use temporary repositories and mocked publication commands, with no live uploads:

```bash
cd tools/ai-shifu-skill-release
python3 -m unittest discover -s tests -p "test_*.py"
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
