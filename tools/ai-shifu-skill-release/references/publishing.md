## Publishing Environment and Configuration

This release tool is self-contained: keep `SKILL.md`, `scripts/`, and `channels/` together. Its maintained location is `tools/ai-shifu-skill-release/` in `ai-shifu/skills`, but a standalone copy also works without a Git repository. Exclude `dist/`, caches, `.git/`, and private `publisher.toml` when distributing the tool.

The tool directory is not the Git repository root. Run documented commands from the directory containing this tool's `SKILL.md`. The local publisher file and channel templates are resolved relative to the tool; relative output paths are resolved against the caller's working directory.

## Requirements

| Dependency | Purpose | Resolution |
| --- | --- | --- |
| Python 3.11+ | All scripts, using the standard library | `python3` |
| Git | Fetch source; push branches for bump and manifest PRs | PATH |
| Node 22 and npx | ClawHub CLI | `CLAWHUB_NPX` or `--clawhub-npx`, then PATH, then the nvm Node 22 fallback |
| SkillHub CLI | SkillHub publication | PATH, overridden by `SKILLHUB_CLI` or `--skillhub-cli`; see the [installation guide](https://skillhub.cn/install/skillhub.md) |
| GitHub CLI (`gh`) | Open bump and manifest PRs | PATH; if missing, the branch is still pushed and the PR must be created manually |
| SSH write access | Push branches to `ai-shifu/skills` and `ai-shifu-website` | Local SSH configuration |

Authentication stays in each CLI's own local session:

```bash
skillhub login --key <API_TOKEN>
npx --yes clawhub@latest login
gh auth login
```

Run ClawHub with Node 22. This tool does not store or request tokens; the user completes authentication locally. Never print credentials or copy authentication state into a release package.

## Build-Time Fields

The WorkBuddy `plugin.json` template uses placeholders for two fields:

- **`version`** comes from the primary source skill's `SKILL.md` version, replacing `__SKILL_VERSION__`. QClaw and Doubao versions derive from the same value. There is no independent version maintained under this tool directory.
- **`author`** comes from `AISHIFU_PUBLISHER_NAME` / `AISHIFU_PUBLISHER_EMAIL`, or from `publisher.toml` alongside this tool's `SKILL.md`. Create the ignored local file from `publisher.toml.example`. Environment values take precedence. Without an identity, build keeps `__PUBLISHER_NAME__` and emits a warning for review before uploading.

## Human Release Gates

The [release skill](../SKILL.md) owns the workflow and its authorization checks. Environment readiness does not authorize the next external action. The workflow stops for:

1. Human review and merge of the source version-bump PR.
2. Explicit authorization before `publish --execute` for the reviewed candidate and selected channels.
3. Manual WorkBuddy, QClaw, and Doubao uploads and platform validation; record evidence with `record-manual`.
4. Human review and merge of the website manifest PR, followed by image rebuild and production deployment; use `--check-online` afterward to confirm activation.

Doubao is recorded separately and does not participate in the website manifest gate. Neither a successful dry run nor a merged manifest PR proves that a release is live.
