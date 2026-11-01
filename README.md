# AI-Shifu CLI and Skills

[中文 README](./README.zh-CN.md)

Install the `shifu` CLI to get AI-Shifu course operations and the matching agent skills, from topic selection and deployment to privacy-safe learning analysis.

## Install and Update

Requires Node.js 22.20.0+, Python 3.11+ with `venv`, and network access for npm and Python dependencies. The installation entrypoint follows the [lark-cli installer](https://github.com/larksuite/cli): install the CLI first, then synchronize its skills.

```bash
npx @ai-shifu/cli@latest install
shifu --version
shifu skills list
```

Installation adds the global `shifu` command, prepares an isolated Python runtime, and installs all three bundled business skills in the shared `~/.agents/skills` directory and for detected common agents. The skills come from the same npm package as the CLI. The recommended `npx … install` entrypoint runs setup explicitly. A direct `npm install --global @ai-shifu/cli` also runs setup when lifecycle scripts are enabled; if the package manager skips them, run `shifu setup`. Restart or refresh the agent to load newly installed skills.

```bash
shifu update
shifu setup
shifu skills install
shifu skills install --agent codex
```

`update` upgrades the CLI and synchronizes its skills together. `setup` prepares both the runtime and skills; use `skills install` for skill-only repair or an agent added later. Omit `--agent` to use the shared directory and detected common agents. Installing skills does not sign in to an AI-Shifu account.

The npm package has not been published yet; the `npx` entrypoint becomes available after its first publication. Maintainers can test the package from this checkout:

```bash
npm install --ignore-scripts
npm test
npm pack
npm install --global ./ai-shifu-cli-VERSION.tgz
shifu setup --agent codex
```

Replace `VERSION` with the version in the tarball filename printed by `npm pack`. Local dependency installation does not install user skills; the explicit setup also works when npm skips installation scripts. The [CLI publication workflow](.github/workflows/cli-publish.yml) publishes a verified release tag to npm when explicitly dispatched with the required npm publishing credential.

## Start Using the CLI

```bash
shifu --help
shifu site --set cn
shifu login
shifu verify
shifu list
```

Choose `cn`, `com`, or your own service URL for the account you intend to use; see the [CLI reference](skills/ai-shifu-course-creator/references/cli/cli-reference.md) for profiles, installation-specific command selection, and command details. Configuration and browser credentials use the existing AI-Shifu user configuration directory. The npm entrypoint and its synchronized skills' Python fallback read optional environment settings from `cli.env` there; channel-managed and older skill installations retain their own `.env` compatibility.

Setup preserves legacy configuration. Migration conflicts and credential cleanup are described in the [installation reference](skills/ai-shifu-course-creator/references/cli/cli-reference.md#cli-and-skill-installation).

## Included Skills

- **AI-Shifu Course Creator（AI 师傅课程创作器）**: teaching design, MarkdownFlow expression, and CLI operations for creating, editing, reviewing, publishing, managing, and analyzing AI-Shifu courses. The using agent selects and combines capabilities for the task.
- **AI-Shifu Learning Report（AI 师傅学习报告）**: analyze one AI-Shifu course and produce a privacy-safe `course-learning-report.json` plus a polished, self-contained, printable `course-learning-report.html` for teaching managers and teachers.
- **Course Direction Advisor（课程选题顾问）**: turn source materials into evidence-bound, market-fit course-topic decisions with competitor analysis, pricing guidance, and GO/HOLD/REWORK/NO-GO recommendations.

## Repository Layout

```text
cli/
skills/
  ai-shifu-course-creator/
  ai-shifu-learning-report/
  course-direction-advisor/
tools/
  ai-shifu-skill-release/
  ai-shifu-workbuddy-publisher/
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

The [WorkBuddy Publisher skill](tools/ai-shifu-workbuddy-publisher/SKILL.md) downloads and checks a published WorkBuddy package, updates the existing AI-Shifu expert through an authenticated browser, and verifies submission for review. It defaults to the latest stable Release and skips duplicate submissions when that version is already published or under review.

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
| Create a complete course | Agent-selected design and expression capabilities, plus CLI build, import, and publication | A verified published course by default, uploaded automatically |
| Deploy an existing course directory | CLI build, payload inspection, import, and requested publication | The requested verified platform result |
| Modify or manage an existing course | CLI synchronization or the selected management operation | Verified changes to the existing course |
| Analyze learning, orders, or credits | CLI analytics and privacy-aware interpretation | Answers grounded in observed course data |

Return the artifacts needed for the request. Segmentation records, a course index, a global variable table, and a fixed risk report are not universal deliverables. A complete authored course contains its lesson content, Course Prompt, description, and structure. Focused requests stay within their requested artifacts; changes to a new or existing platform course still synchronize automatically.

New courses and changes to existing courses follow [automatic platform updates](skills/ai-shifu-course-creator/SKILL.md#automatic-platform-updates), without local confirmation or a separate upload request. Full-course creation retains [default publication](skills/ai-shifu-course-creator/SKILL.md#full-course-creation-outcome). Explicit local-only or unpublished-draft requests determine that narrower result. For existing artifacts, use the relevant [build and import](skills/ai-shifu-course-creator/references/build-and-import.md), [synchronization](skills/ai-shifu-course-creator/references/course-sync.md), or [management](skills/ai-shifu-course-creator/references/course-management.md) guidance directly.

Course Creator CLI usage metadata may be linked to your account. Set `SHIFU_DISABLE_ANALYTICS=1` to opt out; see the [configuration](skills/ai-shifu-course-creator/.env.example).

## Validate

```bash
python3 scripts/validate_skill_quality.py
npm test
npm run check-version
```

## AI-Shifu

This suite is part of AI-Shifu's course authoring workflow: <https://ai-shifu.com>
