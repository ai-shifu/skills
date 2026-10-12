# AI-Shifu Skills

[中文 README](./README.zh-CN.md)

Reusable AI-Shifu skills for course production and improvement, from topic selection and deployment to privacy-safe learning analysis.

## Included Skills

- **AI-Shifu Course Creator（AI 师傅课程创作器）**: teaching design, MarkdownFlow expression, and CLI operations for creating, editing, reviewing, publishing, managing, and analyzing AI-Shifu courses. The using agent selects and combines capabilities for the task.
- **AI-Shifu Learning Report（AI 师傅学习报告）**: analyze one AI-Shifu course and produce a privacy-safe `course-learning-report.json` plus a polished, self-contained, printable `course-learning-report.html` for teaching managers and teachers.
- **Course Direction Advisor（课程选题顾问）**: turn source materials into evidence-bound, market-fit course-topic decisions with competitor analysis, pricing guidance, and GO/HOLD/REWORK/NO-GO recommendations.

## Repository Layout

```text
skills/
  ai-shifu-course-creator/
  ai-shifu-learning-report/
  course-direction-advisor/
tools/
  ai-shifu-skill-release/
```

## Build and Release Tools

The [AI-Shifu Skill Release tool](tools/ai-shifu-skill-release/README.md) builds and verifies packages for ClawHub, SkillHub, WorkBuddy, and Doubao, and supports the existing publication workflow. Its implementation now lives in this repository, migrated from `ai-shifu/ai-shifu-skill-release` (the local `ai-shifu-skill-build` project).

Builds require Python 3.11+ and Git. They still fetch the committed skills from GitHub `ai-shifu/skills` remote `main`; local skill edits are never build inputs. From the repository root:

```bash
cd tools/ai-shifu-skill-release
python3 scripts/release.py build --skill-name ai-shifu-course-creator
python3 scripts/release.py verify dist/<release-id>
```

Use the exact release directory printed by `build`. Building and verifying do not upload packages. See the tool README for `release.toml` configuration, channel-specific dependencies, and publication commands. Maintainer agents can read the tool's [release skill](tools/ai-shifu-skill-release/SKILL.md); it is separate from the three business skills above.

## Learning Report Path

Use **AI-Shifu Learning Report** after a course has learning activity and you need an actionable single-course review. It reuses the course creator's authenticated analytics capabilities, then turns aggregate progress, lesson health, engagement, audience, and audited follow-up signals into:

- a versioned, privacy-safe JSON data artifact with metric definitions and data-quality notes;
- an executive-first HTML report that works without external assets and prints cleanly to PDF;
- three to five evidence-linked teaching recommendations with confidence and a verification method.

The report does not expose learner identities, raw course identifiers, or raw follow-up text. Business and credit data stay out of the report unless the user explicitly asks for the optional operations appendix. Reports default to Simplified Chinese; English is used only when explicitly requested.

## Usage

Each skill keeps `SKILL.md` as the behavior source of truth. The `name` frontmatter field must match the directory name, using lowercase letters, digits, and hyphens only, as required by the [Agent Skills](https://agentskills.io/specification) standard. That format was originally developed by Anthropic and released as an open standard, and the [Claude Code documentation](https://code.claude.com/docs/en/skills) states that its skills follow it. Claude Code itself is more permissive and treats `name` as an optional display label, but this repository follows the stricter standard rule so the skills stay portable across every skills-compatible agent. Human-readable display names live in the skill list above.

## Course Capabilities and Example Requests

The [Course Creator](skills/ai-shifu-course-creator/SKILL.md#capabilities) groups independently usable capabilities into teaching design, MarkdownFlow expression, and CLI operations. The agent chooses the useful combination and order from the request and available materials; a topic, existing Prompt, or course directory is enough to start relevant work.

| Request | Useful capabilities | Result |
| --- | --- | --- |
| Design a lesson or plan a course structure | Teaching design and source analysis | A teaching plan or chapter and lesson structure |
| Write one lesson from supplied material | MarkdownFlow expression, with teaching choices resolved as needed | A runnable Teaching Prompt |
| Write the course description first | Course positioning and listing copy | A learner-facing description |
| Review an existing Prompt | Teaching-quality or MarkdownFlow checks in the requested scope | Findings and requested repairs |
| Create a complete course | Agent-selected design and expression capabilities, plus CLI build, import, and publication | A verified published course by default, after completed-content confirmation |
| Deploy an existing course directory | CLI build, payload inspection, import, and requested publication | The requested verified platform result |
| Modify or manage an existing course | CLI synchronization or the selected management operation | Verified changes to the existing course |
| Analyze learning, orders, or credits | CLI analytics and privacy-aware interpretation | Answers grounded in observed course data |

Return the artifacts needed for the request. Segmentation records, a course index, a global variable table, and a fixed risk report are not universal deliverables. A complete authored course contains its lesson content, Course Prompt, description, and structure; a focused request can end with only its requested artifact.

Full-course creation follows the [default publication and completed-content confirmation policy](skills/ai-shifu-course-creator/SKILL.md#full-course-creation-outcome). Explicit local-only or unpublished-draft requests determine that narrower result. For existing artifacts, use the relevant [build and import](skills/ai-shifu-course-creator/references/deployment-workflow.md), [synchronization](skills/ai-shifu-course-creator/references/course-sync.md), or [management](skills/ai-shifu-course-creator/references/course-management.md) guidance directly.

## Validate Metadata

```bash
python3 scripts/validate_skill_quality.py
```

## AI-Shifu

This suite is part of AI-Shifu's course authoring workflow: <https://ai-shifu.com>
