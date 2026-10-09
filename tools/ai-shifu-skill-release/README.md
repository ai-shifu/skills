## Purpose and Location

Build and publish the AI-Shifu Course Creator across four channels from one canonical source. This tool is maintained in `ai-shifu/skills`, under `tools/ai-shifu-skill-release/`. It was migrated from `ai-shifu/ai-shifu-skill-release`, also known locally as `ai-shifu-skill-build`. The old project is retained for historical reference.

Moving the implementation does not change the release source: GitHub `ai-shifu/skills` remote `main` remains authoritative. Build, verification, preflight, and publication are separate operations.

## Quick Start

Python 3.11+ and Git are required for building and testing. The implementation uses the Python standard library. Authoritative GitHub release-note collection also requires `gh` with read access to the source repository's contents, Releases, and pull requests. Publication has additional CLI and authentication requirements; see [Publishing Environment](references/publishing.md).

`scripts/release.py` is the only command entrypoint. It delegates to the internal `scripts/ai_shifu_release/` package: `build` and `verify` own orchestration, `config` owns release configuration, while `source`, `skill_metadata`, and `artifacts` own shared operations, and the package's `channels/` owns each channel's package format through `clawhub_skillhub`, `workbuddy`, and `doubao`. Publication state, channel submission, GitHub Releases, version changes, and manifest activation have separate modules. Copy the complete `scripts/` directory with the tool.

The former standalone `github_release.py`, `platform_publish.py`, and `download_release.py` commands are removed. Use `github-release` and `submit-channel` below. Download and verification are internal steps of channel submission; there is no standalone `download` subcommand.

## Tagged GitHub Release

The repository workflow `.github/workflows/release.yml` runs for `vX.Y.Z` tags. It builds the tagged commit, verifies all four ZIP files, creates a draft GitHub Release, uploads four ZIPs plus `release.json` and `SHA256SUMS`, then publishes it after checking the complete asset set. A rerun fills missing draft assets. Existing assets must have identical bytes; a published Release is never changed. Only after the Release is public do independent ClawHub and SkillHub jobs read and verify those six attachments. The channel jobs never rebuild an old version from the current `main` branch.

Every PR also runs a trial build from its checked-out commit and saves six preview attachments for seven days. The PR artifact is only for review and must not be published. **Actions → Release Skills → Run workflow** offers two preview types after this workflow has been merged into `main`: `artifact` saves the same six attachments as a seven-day Actions artifact, while `draft` creates and verifies a test Draft Release from a selected development branch. Enter the branch's existing `X.Y.Z` version for either type. Both run the tests, pinned build, and package verification. Neither submits to a platform. All previews save release-note JSON and Markdown in a separate Actions artifact and show the Markdown in the job summary; unmerged branch changes are explicitly identified in the preview. The WorkBuddy ZIP uses the author in the `release.toml` committed with the selected source revision. A failed preview should be fixed and rerun.

The `draft` preview is for a future version PR before an administrator merges it. Select that PR's development branch, set `preview_type` to `draft`, and enter the version in its `SKILL.md`. Each run uses a distinct `preview-vX.Y.Z-<commit>-<run>-<attempt>` test tag that does not match the formal `v*` release trigger. The job creates a Draft Release, uploads all six attachments, downloads them to verify their hashes, and leaves the Release unpublished. Review its URL in the job summary. Re-run the preview after changing the branch; do not publish a test draft or use its tag as the formal version tag. After review, remove obsolete test drafts and their tags with `gh release delete <preview-tag> --repo ai-shifu/skills --cleanup-tag --yes`. The `draft` job uses GitHub's repository write token, not ClawHub or SkillHub credentials. GitHub currently requires extra workflow-write permission when a draft targets an unmerged commit that changes `.github/workflows/`; the built-in Actions token cannot provide that permission. In that exceptional case, use the `artifact` preview and review the workflow change separately rather than granting a broad token to the PR job.

The numbered steps below apply when a new skill version is actually ready for release. They are not required for an automation-only acceptance run.

1. Change `skills/ai-shifu-course-creator/SKILL.md` metadata version in a development branch and open a version PR. A version-bump PR can also be made with `python3 scripts/release.py bump --skill-version X.Y.Z`.
2. Check that `tools/ai-shifu-skill-release/release.toml` has the intended public author name, email, and channel settings. Update it in the version PR if needed. The build rejects missing or placeholder values. No platform token is needed for the preview.
3. Before the version PR is merged, run **Actions → Release Skills → Run workflow** on its development branch with `preview_type=draft` and the intended version. Inspect the test Draft Release and its six verified attachments. After any fix, run a new preview. The administrator reviews and merges the version PR only after the branch preview passes.
4. On the final merged `main` commit, create and push the matching formal tag. A Draft Release from the development branch is test evidence, not the Release for this merged commit:

   ```bash
   git checkout main
   git pull --ff-only
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

5. Open the **Release Skills** Actions run to inspect a failure. The GitHub Release build and upload can be rerun after a transient failure; retry SkillHub through a fresh **Publish Skill Channel** manual run after checking the platform, not by rerunning the old job. If the tagged source or package contents need changing, merge the fix and use a new version and tag. Check the completed Release page for four ZIPs, `release.json`, and `SHA256SUMS`. Remove the test Draft Release and test tag after acceptance.

For a local PR trial build, use a full commit SHA with `build --source-repo-url <checkout-path> --source-ref <SHA> --expected-version X.Y.Z`; it does not create a Release. The workflow also checks that the tag commit is already in `main`. Ordinary PRs and pushes to `main` do not publish.

To accept the release automation without publishing a new skill version, leave the existing skill version unchanged and open a PR containing only the automation changes. The administrator reviews and merges it, including the committed publisher identity, then runs **Release Skills → Run workflow** on the merged `main` commit with the existing version and `preview_type=artifact`. Review the successful job and all six temporary preview attachments. Do not create or push a version tag for this acceptance run: the artifact preview has read-only repository permission and creates neither a GitHub Release nor a platform submission. If the preview fails, fix the code in another PR and repeat it. Record the PR, merge commit, Actions run, and attachment checks as the automation acceptance evidence; the tag-triggered Release and platform submission paths remain pending until a later, genuine skill release.

## Channel Submission from the Release

The two registry jobs use `.github/workflows/platform-publish.yml`. Each downloads the exact published Release attachments, checks `SHA256SUMS`, confirms that the tag, version, and source commit agree, reconstructs the release directory from the ZIP files, and runs the full package verifier. It then independently fetches the requested GitHub repository at the tag's full commit SHA and rebuilds all four packages in a temporary directory. All four ZIPs and the package metadata must match this trusted-source build before submission; builder provenance may differ. A source-fetch failure or mismatch aborts the job before any channel submission. One registry failure does not stop the other. The job summary and a `platform-result.json` Actions artifact distinguish `submitted`, `pending_review`, `already_verified`, `needs_review`, and `failed`; successful submission is not recorded as platform listing or installation verification.

The jobs use the same command entrypoint as local operations:

```bash
python3 scripts/release.py submit-channel \
  --tag vX.Y.Z --repo ai-shifu/skills --target clawhub \
  --output channel-work --execute
```

Use `--target skillhub` for SkillHub. `submit-channel` uses verified attachments from the existing Release and does not require its source commit to remain the current `main` tip. Channel jobs check out the tool from the workflow revision, so retrying an older Release uses the command interface expected by that workflow while the requested tag still pins the verified attachments. Local `publish <release-dir>` retains its current-`main` check. The existing `platform-result.json` filename is retained for artifact consumers.

For the first coordinated release, configure `CLAWHUB_TOKEN` and `SKILLHUB_TOKEN` as repository Secrets. Both are API tokens used to authenticate publishing. The ClawHub publisher handle comes from `[channels.clawhub].owner` in the source revision's `release.toml`; no `CLAWHUB_OWNER` repository Variable is needed. There are no separate platform approval Variables: a formal version tag starts both platform jobs, and configured publisher credentials allow each job to submit. A missing token or ClawHub owner fails that platform job; it does not silently disable publication. ClawHub follows the existing listing's MIT-0 publication method. The repository's `LICENSE` reserves distribution rights, so report this inherited platform publication method to the administrator as part of release review. Confirm SkillHub's publisher identity and publication terms before configuring its token. The workflow reads the official SkillHub CLI version, archive URL, and checksum from that same source configuration and verifies the archive before installation.

The official SkillHub CLI archive was checked on 2026-10-07: version `2026.8.5` includes `login`, `publish`, and `verify`, and `release.toml` pins its SHA-256 digest. The platform's publication guide says `slug`, top-level `version`, and `displayName` are required, while `license` is recommended rather than mandatory. The SkillHub ZIP contains the required top-level version. The workflow checks the three commands before trying to authenticate.

To retry one platform from an existing Release, open **Actions → Publish Skill Channel → Run workflow**, enter the existing `vX.Y.Z` tag and select only the failed platform. The selected job compares the Release's four ZIPs with a temporary trusted-source build and submits only the selected channel. If an exact ClawHub version already exists, the job stops for content review instead of overwriting it. SkillHub runs its documented exact-version ZIP verification first; a signed matching version is recorded as `already_verified`, and any uncertain result stops. Before a SkillHub retry, also check its dashboard for an existing or pending submission and select the confirmation checkbox only when none exists; the workflow refuses a SkillHub retry without it. Do not use **Re-run jobs** for SkillHub: a rerun is rejected because it reuses the old confirmation. Start a new manual run after checking the platform again. WorkBuddy and Doubao remain manual downloads from the Release. No documented official WorkBuddy expert-package submission API has been confirmed for this integration.

Before website manifest activation, import each channel's Actions receipt into the matching verified local release directory. Download the result artifact from that channel's Actions run, keeping the two channels in separate directories:

```bash
gh run download <clawhub-run-id> --repo ai-shifu/skills \
  --name platform-result-<tag>-clawhub --dir "$RELEASE_DIR/receipts/clawhub"
python3 scripts/release.py record-channel "$RELEASE_DIR" \
  --result "$RELEASE_DIR/receipts/clawhub/platform-result.json"
gh run download <skillhub-run-id> --repo ai-shifu/skills \
  --name platform-result-<tag>-skillhub --dir "$RELEASE_DIR/receipts/skillhub"
python3 scripts/release.py record-channel "$RELEASE_DIR" \
  --result "$RELEASE_DIR/receipts/skillhub/platform-result.json"
```

Use the published `vX.Y.Z` tag for `<tag>`. `record-channel` checks the receipt's channel, source commit, version, tag, and archive hash against the candidate before updating `release-report.json`. It never submits again. `submitted` and `pending_review` become `published`, retaining `submission_status`; this records accepted upload rather than independent listing or fresh-install verification. `already_verified` becomes `verified` only for the remote exact version that matched the Release ZIP. Failed or uncertain receipts leave the activation gates unsatisfied. Then complete the manual WorkBuddy gate and run `activate-manifest` as described below.

From the repository root:

```bash
cd tools/ai-shifu-skill-release
python3 scripts/release.py --help
python3 scripts/release.py build --skill-name ai-shifu-course-creator
python3 scripts/release.py verify dist/<release-id>
```

Use the exact release directory printed by `build`, not a guessed latest directory. These commands do not upload packages. The standard working directory is the tool directory, so the default output is `tools/ai-shifu-skill-release/dist/` within the repository. `--output` remains relative to the caller's working directory; when invoking the script from the repository root, use `--output tools/ai-shifu-skill-release/dist` for the same location.

The WorkBuddy entrypoint, `channels/workbuddy/build-zip.sh`, invokes the same all-channel builder. Its default output is the tool's `dist/`; `DIST_DIR` overrides it. It does not implement separate packaging logic.

To prepare the six GitHub Release attachments from a candidate built with an exact source commit, without creating a Release:

```bash
python3 scripts/release.py github-release dist/<release-id> \
  --tag vX.Y.Z --commit <full-source-commit-sha> \
  --prepare-only --output preview-assets
```

Without `--prepare-only`, `github-release` uses the existing draft/upload/verify/publish flow. `--draft-preview-tag` instead keeps a test Release unpublished. Run `github-release --help` for these options.

## Release Notes and Changelog

Generate release notes for a verified, pinned release directory without creating a Release, opening a PR, or activating the website manifest:

```bash
python3 scripts/release.py notes dist/<release-id> --output release-notes
```

Use `--preview` for an unmerged development commit, `--base-ref <tag-or-commit>` to select an explicit ancestor, and `--github-repo owner/name` when the source URL is a local checkout. Source history comes from the repository and full commit SHA recorded in `release.json`, independently of the caller's working directory. The default range starts after the previous published formal Release in that commit's history; the first release includes the initial history. Preview tags, drafts, prereleases, and unrelated branches do not become the default base. The command fetches complete history and follows GitHub API pagination. A missing history or API result fails collection rather than silently shortening the changelog.

A local Git source without `--github-repo` supports an offline preview using local version tags and commit subjects. Its snapshot records `metadata_source: git-subjects` and `pr_metadata_verified: false`, and the Markdown identifies the unverified metadata. Supply the actual GitHub repository to collect authoritative PR titles, authors, and merge times for publication.

The complete changelog includes every merged PR in the range once, grouped in this fixed order:

`feat → fix → perf → refactor → docs → test → build → ci → chore → revert → other`

Groups appear only when nonempty. Within a group, PRs appear by merge time descending, then PR number descending. Historical scope prefixes and breaking-change markers are supported, `feature` is treated as `feat`, and unknown or absent types appear in Other Changes. Direct commits and unmerged preview changes appear separately. PR trial builds and notes retain Actions' synthetic merge commit as their source pin; the preview also includes the unmerged branch commits reachable through that merge, so reviewers see the proposed changes. Formal release notes continue to follow first-parent integration history. Sorting does not call a model or remove maintenance PRs.

The output directory contains `release-notes.json`, with the pinned range, PR facts, collection status, and reproducibility fingerprint, and `release-notes.md`, with the rendered Release body. Inspect both before publication. `github-release --prepare-only --output preview-assets` saves the same files under `preview-assets/notes/`; they are excluded from the six package attachments. To save the notes while creating a Draft or formal Release, pass `--notes-output release-notes`. The release workflows upload that directory as a separate Actions artifact and display the body in the job summary.

Draft reruns compare the expected generated body with the saved Draft. A mismatch requires `--refresh-notes`; refreshing replaces only the marked generated section and preserves text outside it. A legacy Draft without generated-section markers also requires an explicit refresh. Published Releases are checked without rewriting their body. Collection and body verification must pass before a formal Release can be published.

Website activation keeps its own range: the website's current skill version to the pinned source commit, filtered to the primary skill's path. Its automatic summary reuses the same PR collection and type order, preserves the complete `changes` list, and fits whole entries into the 500-character limit with an omitted-item count. Reviewed `--notes` text and the default `Release <version>` behavior remain available; see [the release skill](SKILL.md#activate-the-website-manifest).

## Build and Verification Contract

The release trust chain is: a commit anchors the source, deterministic builds make package contents reproducible, a hash ledger detects changes, and publication preflight rejects stale candidates.

1. **Pin the source.** Shallow-fetch remote `main` or the explicitly requested full commit SHA into a temporary repository and export the skills, channel templates, and `release.toml` from that same commit. Local skill branches, uncommitted edits, runtime `.env` files, and update caches are not build inputs. Committed `.env.example` templates are included.
2. **Render channel variants.** Generate the four packages from that export. Only allowlisted frontmatter changes are permitted. WorkBuddy wraps the primary skill in a plugin shell. Doubao wraps the course creator, learning report, and course direction advisor from the same source commit.
3. **Write deterministic archives.** ZIP entries are sorted and use fixed timestamps. Identical inputs produce identical archive bytes.
4. **Record hashes.** Derive `release_sha256` from seven artifact digests in the fixed channel order: ClawHub directory and ZIP, SkillHub directory and ZIP, WorkBuddy ZIP, then Doubao directory and ZIP. The release directory is `dist/<skill>-<version>-<commit-prefix>-<artifact-prefix>/`.

`verify` independently recalculates directory and ZIP hashes, verifies the canonical ClawHub `SKILL.md` against its source hash, compares channel contents byte for byte against their permitted variants, and checks the combined release hash and directory name. Directory hashes include paths, modes, and contents. Secret-pattern scanning and ZIP path checks also apply.

Doubao verification additionally checks its single archive root, required files, three scenarios, three recommended instructions, three skill entries, embedded source manifests, avatar, and local-path leakage. It uses the source profile recorded in `release.json`, so later changes to the local profile cannot invalidate an older package. Its embedded skills may only change an existing `version_management: standalone` to `plugin` and add `label` and an empty `icon`. Other source files and skill bodies must remain unchanged.

The current `release.json` contract is **schema 6**. Schema 5 and older candidates must be rebuilt for this automation workflow. Loading a release for publication always runs verification first.

`check` and `publish` use `git ls-remote` to compare the current remote `main` commit with the candidate's recorded source commit. If remote `main` has advanced, rebuild. This still applies when a commit only changes tools in the shared repository.

Builder provenance now records the enclosing `ai-shifu/skills` repository, commit, and worktree status. Those fields are informational and do not feed the artifact hash. The tool also works outside Git, with unavailable provenance recorded as null.

## Version Changes

The primary skill's `skills/ai-shifu-course-creator/SKILL.md` version is the only version source. All four channel versions derive from it. The tool has no independent release version. Companion skills without their own versions are traced by the source commit and content hashes.

```bash
python3 scripts/release.py bump --skill-name ai-shifu-course-creator \
  --skill-version <X.Y.Z>
```

`bump` creates a source-repository branch in a temporary clone, changes the frontmatter version without changing the skill body, pushes the branch, and opens a PR with `gh`. Release PRs follow the [version-bump title requirement](SKILL.md#upgrade-the-skill-version). It does not edit the current checkout or merge the PR. A human must merge before `build` can read the new version from remote `main`.

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

WorkBuddy and Doubao require manual uploads:

```bash
python3 scripts/release.py manual-plan dist/<release-id> --target all
python3 scripts/release.py record-manual dist/<release-id> \
  --target workbuddy --status submitted --url <platform-page-url>
```

Use `doubao` for the other manual targets. Valid states are `submitted`, `verified`, and `failed`. `submitted` and `verified` require a platform URL; only a failure without a platform page can omit it. Do not label a submission as independently verified without supporting evidence.

The Doubao plan lists every embedded skill, the recommended instructions, and runtime checks. Platform testing should cover starting a course from scratch, choosing a course direction, and converting uploaded material into a course, plus the retained learning-report capability. Record the result after the platform checks.

## Website Manifest Activation

The website gate requires ClawHub and SkillHub to be `published` and WorkBuddy to be `submitted` or `verified`. Doubao is tracked independently and does not block activation.

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

`release.toml` owns publisher identity and non-secret channel settings. Builds and channel submissions read the configuration committed with the release source, including when an older release is retried with newer runtime code. Channel profiles and templates retain their native formats and are referenced by the configuration. See [Publishing Environment](references/publishing.md) for fields, local overrides, and legacy-source compatibility.

- WorkBuddy reads `author.name` and `author.email` from the packaged `.codebuddy-plugin/plugin.json`. The build fills the source template's placeholders from the committed `release.toml` at the same source revision. GitHub Actions and local builds use that one file; no publisher repository variables are needed. The name and email are public in the package, so review changes to this file in a PR. The build fails if either value is missing or is a placeholder.
- ClawHub preserves the exported `SKILL.md` unchanged. Its slug and display name are CLI arguments. SkillHub only adds or replaces `slug` and `displayName` in frontmatter.
- WorkBuddy only changes the embedded primary skill's version management to `plugin`. Its shell remains under `channels/`.
- `channels/doubao/profile.json` owns the stable identity, display labels, and recommended instructions. Skill names and descriptions come from source frontmatter; icons remain empty for platform matching. The first two scenarios do not require uploaded material. The third scenario uses supplied material. The learning-report skill remains embedded even though it is not one of the three displayed scenarios.
- `channels/avatars/expert.png` is the shared 512×512 avatar. WorkBuddy includes it through the build. Preserve the relative `channels/workbuddy/avatars` symlink.

Engineering prose is English. Chinese channel prompts, display copy, platform enums, matching rules, and their test fixtures are intentional and must retain their behavior.

## Tests and Maintenance

From this tool directory:

```bash
PYTHONPATH=scripts python3 -m unittest discover -s tests -p 'test_*.py'
```

The repository CI runs these tests separately from the business-skill tests. Release tests import the dedicated `ai_shifu_release` package. Tests use temporary Git repositories and mocked external publication commands, including offline GitHub fixtures for release-note collection. Do not run live `bump`, `publish`, or `activate-manifest` operations to validate a code migration.

Maintain the executable code, channel assets, and [release skill](SKILL.md) here. Root README files provide the repository-level entrypoint; this README owns the detailed tool guide. Existing release artifacts, credentials, local agent state, and the old project's Git history are not part of the migration.
