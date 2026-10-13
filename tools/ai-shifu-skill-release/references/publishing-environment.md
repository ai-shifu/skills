## Publishing Environment and Configuration

This release tool is self-contained: keep `SKILL.md`, `scripts/`, `channels/`, and `release.toml` together. The `scripts/` directory contains both the command entrypoint and its internal `ai_shifu_release/` package. Its maintained location is `tools/ai-shifu-skill-release/` in `ai-shifu/skills`, but a standalone copy also works without a Git repository. Exclude `dist/`, caches, and `.git/` when distributing the tool.

The tool directory is not the Git repository root. Run documented commands from the directory containing this tool's `SKILL.md`. `release.toml` and channel templates are read from the selected source revision; relative output paths are resolved against the caller's working directory.

## Release Configuration

`release.toml` is the canonical configuration file for publisher identity and non-secret channel settings:

| Section | Fields |
| --- | --- |
| `publisher` | Public `name` and `email` used in the WorkBuddy package |
| `channels.clawhub` | `owner`, `endpoint`, CLI `package`, and `node_version` |
| `channels.skillhub` | `endpoint`, `cli_version`, `cli_url`, and `cli_sha256` |
| `channels.workbuddy` | Native asset `template_dir` |
| `channels.doubao` | Native asset `profile` and `workspace_dir` |

Channel assets remain in their existing native files. Configuration asset paths are relative to the tool directory and must stay inside `channels/`. Unknown fields, missing values, credential-bearing URLs, invalid installer hashes, and escaping asset paths are rejected. Credentials do not belong in this file.

`config.py` reads this file from the selected source commit for builds and from the verified release's recorded source commit for channel submissions. New runtime code can therefore retry older releases using their original settings. For source revisions that predate `release.toml`, the loader centrally reads the old `publisher.toml` and applies the original fixed channel settings. A present but malformed `release.toml` fails instead of using that compatibility path.

Local operators may use a non-empty `CLAWHUB_OWNER` environment value to override the committed owner for that invocation. GitHub Actions uses the committed owner; configure publication tokens as repository Secrets only. CLI executable overrides and local authentication continue to work as described below.

## Requirements

| Dependency | Purpose | Resolution |
| --- | --- | --- |
| Python 3.11+ | All scripts, using the standard library | `python3` |
| Git | Fetch source; push branches for bump and manifest PRs | PATH |
| Configured Node version and npx (default: Node 22) | ClawHub CLI | `CLAWHUB_NPX` or `--clawhub-npx`, then PATH, then nvm for the configured Node version |
| SkillHub CLI | SkillHub publication | PATH, overridden by `SKILLHUB_CLI` or `--skillhub-cli`; see the [installation guide](https://skillhub.cn/install/skillhub.md) |
| GitHub CLI (`gh`) | Open bump and manifest PRs | PATH; if missing, the branch is still pushed and the PR must be created manually |
| SSH write access | Push branches to `ai-shifu/skills` and `ai-shifu-website` | Local SSH configuration |

Authentication stays in each CLI's own local session:

```bash
skillhub login --key <API_TOKEN>
npx --yes clawhub@latest login
gh auth login
```

Run ClawHub with the Node version configured in the release source (default: 22). This tool does not store or request tokens; the user completes authentication locally. Never print credentials or copy authentication state into a release package.

## Build-Time Fields

The WorkBuddy `plugin.json` template uses placeholders for two fields:

- **`author`** comes from the committed `release.toml` in the selected source revision. The build writes those values to the packaged WorkBuddy `plugin.json` and rejects missing or placeholder information. Review publisher changes in a PR because the name and email are public in the package.
- **`version`** comes from the primary source skill's `SKILL.md` version, replacing `__SKILL_VERSION__`. Doubao versions derive from the same value. There is no independent version maintained under this tool directory.

## Human Release Gates

The [release skill](../SKILL.md) owns the workflow and its authorization checks. Environment readiness does not authorize the next external action. The workflow stops for:

1. Human review and merge of the source version-bump PR.
2. Explicit authorization before `publish --execute` for the reviewed candidate and selected channels.
3. Manual WorkBuddy and Doubao uploads and platform validation; record evidence with `record-manual`.
4. Human review and merge of the website manifest PR, followed by image rebuild and production deployment; use `--check-online` afterward to confirm activation.

Doubao is recorded separately and does not participate in the website manifest gate. Neither a successful dry run nor a merged manifest PR proves that a release is live.

For the GitHub Actions path, configure `CLAWHUB_TOKEN` and `SKILLHUB_TOKEN` as repository Secrets; both are publishing API tokens. The ClawHub publisher handle comes from `[channels.clawhub].owner` in the release source's `release.toml`; no `CLAWHUB_OWNER` repository Variable is required. There are no separate platform approval Variables: pushing a formal version tag starts both platform jobs, and configured publisher credentials allow each job to submit. Missing credentials fail the corresponding job. ClawHub follows the existing listing's MIT-0 publication method; report this choice to the administrator during release review. Confirm SkillHub's publisher identity and publication terms before configuring its token. The workflow reads the SkillHub CLI version, archive URL, and digest from the same pinned source configuration and verifies the archive before installing it. The channel workflow reads and verifies published GitHub Release attachments and submits ClawHub and SkillHub independently. WorkBuddy and Doubao use the verified Release ZIPs for manual submission. See the tool [README](../README.md#channel-submission-from-the-release) for retry and result handling.
