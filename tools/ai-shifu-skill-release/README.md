## Purpose and Location

Build and publish the AI-Shifu Course Creator across five channels from one canonical source. This tool is maintained in `ai-shifu/skills`, under `tools/ai-shifu-skill-release/`. It was migrated from `ai-shifu/ai-shifu-skill-release`, also known locally as `ai-shifu-skill-build`. The old project is retained for historical reference.

Moving the implementation does not change the release source: GitHub `ai-shifu/skills` remote `main` remains authoritative. Build, verification, preflight, and publication are separate operations.

## Quick Start

Python 3.11+ and Git are required for building and testing. The implementation uses the Python standard library. Publication has additional CLI and authentication requirements; see [Publishing Environment](references/publishing.md).

From the repository root:

```bash
cd tools/ai-shifu-skill-release
python3 scripts/release.py --help
python3 scripts/release.py build --skill-name ai-shifu-course-creator
python3 scripts/release.py verify dist/<release-id>
```

Use the exact release directory printed by `build`, not a guessed latest directory. These commands do not upload packages. The standard working directory is the tool directory, so the default output is `tools/ai-shifu-skill-release/dist/` within the repository. `--output` remains relative to the caller's working directory; when invoking the script from the repository root, use `--output tools/ai-shifu-skill-release/dist` for the same location.

The two channel entrypoints, `channels/workbuddy/build-zip.sh` and `channels/qclaw/build.sh`, invoke the same all-channel builder. Their default output is the tool's `dist/`; `DIST_DIR` overrides it. They do not implement separate packaging logic.

## Build and Verification Contract

The release trust chain is: a commit anchors the source, deterministic builds make package contents reproducible, a hash ledger detects changes, and publication preflight rejects stale candidates.

1. **Pin the source.** Shallow-fetch remote `main` into a temporary repository, resolve its commit, and export skills with `git archive`. Local skill branches, uncommitted edits, runtime `.env` files, and update caches are not build inputs. Committed `.env.example` templates are included.
2. **Render channel variants.** Generate the five packages from that export. Only allowlisted frontmatter changes are permitted. WorkBuddy and QClaw wrap the primary skill in plugin shells. Doubao wraps the course creator, learning report, and course direction advisor from the same source commit.
3. **Write deterministic archives.** ZIP entries are sorted and use fixed timestamps. Identical inputs produce identical archive bytes.
4. **Record hashes.** Hash all eight artifact digests in the fixed channel order to derive `release_sha256`. The release directory is `dist/<skill>-<version>-<commit-prefix>-<artifact-prefix>/`.

`verify` independently recalculates directory and ZIP hashes, verifies the canonical ClawHub `SKILL.md` against its source hash, compares channel contents byte for byte against their permitted variants, and checks the combined release hash and directory name. Directory hashes include paths, modes, and contents. Secret-pattern scanning and ZIP path checks also apply.

Doubao verification additionally checks its single archive root, required files, three scenarios, three recommended instructions, three skill entries, embedded source manifests, avatar, and local-path leakage. Its embedded skills may only change an existing `version_management: standalone` to `plugin` and add `label` and an empty `icon`. Other source files and skill bodies must remain unchanged.

The current `release.json` contract is **schema 4**. Schema 3 and older candidates lack the required embedded-source evidence and must be rebuilt. Loading a release for publication always runs verification first.

`check` and `publish` use `git ls-remote` to compare the current remote `main` commit with the candidate's recorded source commit. If remote `main` has advanced, rebuild. This still applies when a commit only changes tools in the shared repository.

Builder provenance now records the enclosing `ai-shifu/skills` repository, commit, and worktree status. Those fields are informational and do not feed the artifact hash. The tool also works outside Git, with unavailable provenance recorded as null.

## Version Changes

The primary skill's `skills/ai-shifu-course-creator/SKILL.md` version is the only version source. All five channel versions derive from it. The tool has no independent release version. Companion skills without their own versions are traced by the source commit and content hashes.

```bash
python3 scripts/release.py bump --skill-name ai-shifu-course-creator \
  --skill-version <X.Y.Z>
```

`bump` creates a source-repository branch in a temporary clone, changes the frontmatter version without changing the skill body, pushes the branch, and opens a PR with `gh`. It does not edit the current checkout or merge the PR. A human must merge before `build` can read the new version from remote `main`.

Options include `--level major|minor|patch`, `--changelog <text>`, `--draft`, and `--no-pr`. The optional changelog text also adds a CHANGELOG entry. With `--no-pr`, or when `gh` is missing, the branch is still pushed but PR creation is left to the operator. A channel-shell-only update still uses the primary skill version; there is no independent plugin version override.

## Release Outputs

| Output | Purpose |
| --- | --- |
| `artifacts/clawhub/ai-shifu-course-creator/` | ClawHub upload input |
| `artifacts/clawhub/*.zip` | ClawHub archive for review and retention |
| `artifacts/skillhub/ai-shifu-course-creator/` | SkillHub upload input |
| `artifacts/skillhub/*.zip` | SkillHub archive for review and retention |
| `artifacts/workbuddy/workbuddy-ai-shifu-<version>/` | Expanded WorkBuddy package for review |
| `artifacts/workbuddy/*.zip` | WorkBuddy plugin upload |
| `artifacts/qclaw/qclaw-ai-shifu-<version>/` | Expanded QClaw package for review |
| `artifacts/qclaw/*.zip` | QClaw plugin upload |
| `artifacts/doubao/doubao-ai-shifu-<version>/` | Expanded Doubao Work partner package |
| `artifacts/doubao/*.zip` | Doubao submission ZIP |
| `release.json` | Source commit, versions, builder provenance, and SHA-256 ledger |
| `release-report.json` | Channel preflight, publication, and failure status |

A change to a plugin shell changes the release hash even if the source commit stays the same, preventing accidental reuse of a different candidate's directory.

## Automated Publication

First verify and run preflight against the exact candidate:

```bash
python3 scripts/release.py verify dist/<release-id>
python3 scripts/release.py check dist/<release-id> --target all
```

`check` checks authentication, source freshness, and registry dry runs without uploading. It writes `release-report.json`. Automated targets are `clawhub`, `skillhub`, or `all`. GitHub is the source host, not a publication target.

After reviewing the candidate and obtaining explicit publication authorization:

```bash
python3 scripts/release.py publish dist/<release-id> --target all --execute
```

Publication repeats authentication and dry runs. If any selected target fails preflight, no selected target is uploaded. Upload results are recorded independently. After a partial upload failure, use the same immutable release directory to retry failed targets; do not rebuild unless the source has advanced. `published` means the upload was accepted, not that platform review or a fresh installation was independently verified.

## Manual Channels

WorkBuddy, QClaw, and Doubao require manual uploads:

```bash
python3 scripts/release.py manual-plan dist/<release-id> --target all
python3 scripts/release.py record-manual dist/<release-id> \
  --target workbuddy --status submitted --url <platform-page-url>
```

Use `qclaw` or `doubao` for the other manual targets. Valid states are `submitted`, `verified`, and `failed`. `submitted` and `verified` require a platform URL; only a failure without a platform page can omit it. Do not label a submission as independently verified without supporting evidence.

The Doubao plan lists every embedded skill, the recommended instructions, and runtime checks. Platform testing should cover starting a course from scratch, choosing a course direction, and converting uploaded material into a course, plus the retained learning-report capability. Record the result after the platform checks.

## Website Manifest Activation

The website gate requires ClawHub and SkillHub to be `published` and WorkBuddy and QClaw to be `submitted` or `verified`. Doubao is tracked independently and does not block activation.

```bash
python3 scripts/release.py activate-manifest dist/<release-id> --notes <release-notes>
```

The command opens a `codex/` branch PR in `ai-shifu-website`, updating `zh/skill-manifests/<skill_name>.json`. It never merges. See the [release skill](SKILL.md) for notes options and explicit manual-channel waivers.

Merging the PR is not deployment: the website embeds the manifest in its Docker image, which must be rebuilt and deployed. After deployment:

```bash
python3 scripts/release.py activate-manifest dist/<release-id> --check-online
```

Edge caching may delay the visible update by about five minutes.

## Configuration and Channel Assets

- Copy `publisher.toml.example` to `publisher.toml` **in this tool directory**, or use `AISHIFU_PUBLISHER_NAME` and `AISHIFU_PUBLISHER_EMAIL`. Environment variables take precedence. The local file is ignored by Git. Without an identity, WorkBuddy retains its publisher placeholder and build emits a warning.
- `channels/workbuddy/.codebuddy-plugin/plugin.json` stores the `__SKILL_VERSION__` placeholder; build injects the canonical version and publisher identity.
- ClawHub preserves the exported `SKILL.md` unchanged. Its slug and display name are CLI arguments. SkillHub only adds or replaces `slug` and `displayName` in frontmatter.
- WorkBuddy and QClaw only change the embedded primary skill's version management to `plugin`. Their shells remain under `channels/`.
- `channels/doubao/profile.json` owns the stable identity, display labels, and recommended instructions. Skill names and descriptions come from source frontmatter; icons remain empty for platform matching. The first two scenarios do not require uploaded material. The third scenario uses supplied material. The learning-report skill remains embedded even though it is not one of the three displayed scenarios.
- `channels/avatars/expert.png` is the shared 512×512 avatar. WorkBuddy includes it through the build; QClaw requires a manual upload. Preserve the relative `channels/workbuddy/avatars` symlink.

Engineering prose is English. Chinese channel prompts, display copy, platform enums, matching rules, and their test fixtures are intentional and must retain their behavior.

## Tests and Maintenance

From this tool directory:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The repository CI runs these tests separately from the business-skill tests, avoiding collisions between their `scripts` modules. Tests use temporary Git repositories and mocked external publication commands. Do not run live `bump`, `publish`, or `activate-manifest` operations to validate a code migration.

Maintain the executable code, channel assets, and [release skill](SKILL.md) here. Root README files provide the repository-level entrypoint; this README owns the detailed tool guide. Existing release artifacts, credentials, local agent state, and the old project's Git history are not part of the migration.
