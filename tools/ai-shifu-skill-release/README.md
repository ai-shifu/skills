## Purpose and Location

Build and publish the AI-Shifu Course Creator across five channels from one canonical source. This tool is maintained in `ai-shifu/skills`, under `tools/ai-shifu-skill-release/`. It was migrated from `ai-shifu/ai-shifu-skill-release`, also known locally as `ai-shifu-skill-build`. The old project is retained for historical reference.

Moving the implementation does not change the release source: GitHub `ai-shifu/skills` remote `main` remains authoritative. Build, verification, preflight, and publication are separate operations.

## Quick Start

Python 3.11+ and Git are required for building and testing. The implementation uses the Python standard library. Publication has additional CLI and authentication requirements; see [Publishing Environment](references/publishing.md).

## Tagged GitHub Release

The repository workflow `.github/workflows/release.yml` runs for `skills-vX.Y.Z` tags. It builds the tagged commit, verifies all five ZIP files, creates a draft GitHub Release, uploads five ZIPs plus `release.json` and `SHA256SUMS`, then publishes it after checking the complete asset set. A rerun fills missing draft assets. Existing assets must have identical bytes; a published Release is never changed. Only after the Release is public do independent ClawHub and SkillHub jobs read and verify those seven attachments. The platform jobs never rebuild an old version from the current `main` branch.

Every PR also runs a trial build from its checked-out commit and saves seven preview attachments for seven days. This PR artifact uses a test publisher identity and must not be published. To test the final package before tagging, or to accept automation changes without releasing a new version, open **Actions → Release Skills → Run workflow**, select the branch or merged `main` commit to preview, and enter its existing `X.Y.Z` version. The manual run performs the same tests, pinned build, package verification, and attachment preparation, then saves a seven-day Actions artifact. It does **not** create a Release or submit to a platform. WorkBuddy reads the `author` object in the packaged `.codebuddy-plugin/plugin.json`; the repository variables are this GitHub Actions workflow's inputs for filling that object. Configure them with the intended identity before the manual preview. A failed preview should be fixed and rerun.

The numbered steps below apply when a new skill version is actually ready for release. They are not required for an automation-only acceptance run.

1. Change `skills/ai-shifu-course-creator/SKILL.md` metadata version in a PR, run the normal checks, and merge to `main`. A version-bump PR can also be made with `python3 scripts/release.py bump --skill-version X.Y.Z`.
2. Set repository variables `AISHIFU_PUBLISHER_NAME` and `AISHIFU_PUBLISHER_EMAIL` to the real publisher identity. The build rejects missing or placeholder values. No platform token is needed for this workflow.
3. Run **Actions → Release Skills → Run workflow** on the merged `main` branch with the intended version. Inspect the seven preview attachments and confirm the job passed.
4. On that same merged `main` commit, create and push the matching tag:

   ```bash
   git checkout main
   git pull --ff-only
   git tag skills-vX.Y.Z
   git push origin skills-vX.Y.Z
   ```

5. Open the **Release Skills** Actions run to inspect a failure and choose **Re-run jobs** after fixing a transient issue. If the tagged source or package contents need changing, merge the fix and use a new version and tag. Check the completed Release page for five ZIPs, `release.json`, and `SHA256SUMS`.

For a local PR trial build, use a full commit SHA with `build --source-repo-url <checkout-path> --source-ref <SHA> --expected-version X.Y.Z`; it does not create a Release. The workflow also checks that the tag commit is already in `main`. Ordinary PRs and pushes to `main` do not publish.

To accept the release automation without publishing a new skill version, leave the existing skill version unchanged and open a PR containing only the automation changes. The administrator reviews and merges it, sets the two real publisher repository variables, then runs **Release Skills → Run workflow** on the merged `main` commit with the existing version. Review the successful job and all seven temporary preview attachments. Do not create or push a version tag for this acceptance run: the manual preview has read-only repository permission and creates neither a GitHub Release nor a platform submission. If the preview fails, fix the code in another PR and repeat it. Record the PR, merge commit, Actions run, and attachment checks as the automation acceptance evidence; the tag-triggered Release and platform submission paths remain pending until a later, genuine skill release.

## Platform Submission from the Release

The two registry jobs use `.github/workflows/platform-publish.yml`. Each downloads the exact published Release attachments, checks `SHA256SUMS`, confirms that the tag, version, and source commit agree, reconstructs the release directory from the ZIP files, and runs the full package verifier before submitting its own channel. One registry failure does not stop the other. The job summary and a `platform-result.json` Actions artifact distinguish `submitted`, `pending_review`, `already_verified`, `disabled`, `needs_review`, and `failed`; successful submission is not recorded as platform listing or installation verification.

For the first coordinated release, configure `SKILLHUB_TOKEN` and `CLAWHUB_TOKEN` as repository Secrets. ClawHub needs repository variables `AISHIFU_CLAWHUB_OWNER` (the existing publisher handle) and `AISHIFU_CLAWHUB_MIT0_APPROVED=true`. SkillHub needs `AISHIFU_SKILLHUB_PUBLICATION_APPROVED=true`. The workflow pins and checks the official SkillHub CLI archive in code; administrators do not configure an installer URL or checksum. Both approval variables default to off. Set them only after the team has confirmed publication rights and the corresponding platform identity; the repository's current `LICENSE` reserves distribution rights, while ClawHub distributes published skills under MIT-0. An unset gate leaves the Release intact and records that platform as `disabled`.

The official SkillHub CLI archive was checked on 2026-10-07: version `2026.8.5` includes `login`, `publish`, and `verify`, and the workflow pins its SHA-256 digest. The platform's publication guide says `slug`, top-level `version`, and `displayName` are required, while `license` is recommended rather than mandatory. The SkillHub ZIP contains the required top-level version. Keep automatic submission disabled until the team confirms the existing listing's publisher identity and publication terms and provides its token. The workflow checks the three commands before trying to authenticate.

To retry one platform from an existing Release, open **Actions → Publish Skill Platform → Run workflow**, enter the existing `skills-vX.Y.Z` tag and select only the failed platform. This reads the same Release ZIP; it does not rebuild or resubmit the other platform. If an exact ClawHub version already exists, the job stops for content review instead of overwriting it. SkillHub runs its documented exact-version ZIP verification first; a signed matching version is recorded as `already_verified`, and any uncertain result stops. Before a SkillHub retry, also check its dashboard for an existing or pending submission and select the confirmation checkbox only when none exists; the workflow refuses a SkillHub retry without it. WorkBuddy, QClaw, and Doubao remain manual downloads from the Release. No documented official WorkBuddy expert-package submission API has been confirmed for this integration.

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

1. **Pin the source.** Shallow-fetch remote `main` or the explicitly requested full commit SHA into a temporary repository and export the skills and channel templates from that same commit with `git archive`. Local skill branches, uncommitted edits, runtime `.env` files, and update caches are not build inputs. Committed `.env.example` templates are included.
2. **Render channel variants.** Generate the five packages from that export. Only allowlisted frontmatter changes are permitted. WorkBuddy and QClaw wrap the primary skill in plugin shells. Doubao wraps the course creator, learning report, and course direction advisor from the same source commit.
3. **Write deterministic archives.** ZIP entries are sorted and use fixed timestamps. Identical inputs produce identical archive bytes.
4. **Record hashes.** Hash all eight artifact digests in the fixed channel order to derive `release_sha256`. The release directory is `dist/<skill>-<version>-<commit-prefix>-<artifact-prefix>/`.

`verify` independently recalculates directory and ZIP hashes, verifies the canonical ClawHub `SKILL.md` against its source hash, compares channel contents byte for byte against their permitted variants, and checks the combined release hash and directory name. Directory hashes include paths, modes, and contents. Secret-pattern scanning and ZIP path checks also apply.

Doubao verification additionally checks its single archive root, required files, three scenarios, three recommended instructions, three skill entries, embedded source manifests, avatar, and local-path leakage. Its embedded skills may only change an existing `version_management: standalone` to `plugin` and add `label` and an empty `icon`. Other source files and skill bodies must remain unchanged.

The current `release.json` contract is **schema 5**. Schema 4 and older candidates use a different channel set and must be rebuilt. Loading a release for publication always runs verification first.

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

`check` checks authentication, source freshness, and registry dry runs without uploading. It writes `release-report.json`. Automated targets are `clawhub`, `skillhub`, or `all`. GitHub Release delivery is separate from registry publication.

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

- WorkBuddy reads `author.name` and `author.email` from the packaged `.codebuddy-plugin/plugin.json`. The source template at `channels/workbuddy/.codebuddy-plugin/plugin.json` has placeholders; the build fills them before packaging. WorkBuddy does not read the repository variables or `publisher.toml`.
- For a local build, copy `publisher.toml.example` to `publisher.toml` **in this tool directory**, or use `AISHIFU_PUBLISHER_NAME` and `AISHIFU_PUBLISHER_EMAIL`. Environment variables take precedence. The local file is ignored by Git. GitHub Actions uses repository variables because that local file is not present on its runner. A complete identity is required; the build fails if it is missing or contains placeholders.
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
