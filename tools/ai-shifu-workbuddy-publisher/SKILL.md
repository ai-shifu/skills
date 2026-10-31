---
name: ai-shifu-workbuddy-publisher
description: Download the latest stable or specified ai-shifu/skills WorkBuddy Release package, update the existing AI-Shifu expert on open.workbuddy.cn, and verify its review submission. Use when asked to update the WorkBuddy edition or download and upload its latest package.
---

# AI-Shifu WorkBuddy Publisher

Download the WorkBuddy expert ZIP from a published GitHub Release, then use **Computer Use** in an authenticated browser to update the existing expert and verify submission for review. For download-only requests, deliver the verified local package. Upload or update requests include submission for review unless the user specifies an earlier stop point.

## Inputs and Tools

- Repository: `ai-shifu/skills`. Default version: the latest stable, non-draft Release at execution time. Use the requested Release when the user specifies a version.
- Target: the existing expert titled `AI师傅课程制作专家`, with nickname `AI师傅`. Read its expert ID, published version, pending version, and review status from the current account; do not reuse an ID from a previous recording.
- Download directory: the user's chosen directory, or a separate temporary directory for this task. Retain the absolute ZIP path for the browser file picker.
- Prefer an available GitHub connector for Release metadata. Download binary assets with `gh release download` or a download tool. Without a suitable connector, use `gh api repos/ai-shifu/skills/releases/latest`.
- For unsupported WorkBuddy upload operations, use Computer Use with current accessibility or DOM control names. Reuse the authenticated WorkBuddy tab where possible. Do not replay recorded coordinates, element numbers, or window IDs.
- Existing release-tool commands such as `manual-plan` and `record-manual` prepare packages or record outcomes; they do not perform an upload.

## 1. Download and Verify the Package

1. Read `https://api.github.com/repos/ai-shifu/skills/releases/latest`, or the Release for the requested tag. Record the tag, Release URL, asset name, size, and available SHA-256 digest. Confirm that the Release is published and stable.
2. Select exactly `workbuddy-ai-shifu-VERSION.zip` from its assets. Do not select a source archive or another channel's package. Pin this task to the observed tag instead of resolving latest again during download.
3. Create a separate download directory. Substitute the confirmed tag, asset name, and absolute directory as safely quoted ordinary arguments:

   ```text
   gh release download TAG --repo ai-shifu/skills --pattern ASSET_NAME --dir ABSOLUTE_DIRECTORY
   ```

4. Check the file size and ZIP integrity. Verify its SHA-256 against the Release digest, or the same Release's `SHA256SUMS` when the digest is unavailable. If neither is provided, record that upstream supplied no digest and continue with the ZIP checks; do not claim checksum verification.
5. Read `workbuddy-ai-shifu-VERSION/.codebuddy-plugin/plugin.json` inside the ZIP. Confirm plugin name `ai-shifu`, the target version, and Chinese profession `AI师傅课程制作专家`. Upload the original ZIP without repacking it or editing its version.
6. Read the current upload control's file-size limit; the demonstrated limit was ZIP files up to 20 MB. Stop on a missing asset, corrupt archive, digest mismatch, or mismatched package identity/version.

## 2. Find the Existing Expert and Read Its Status

1. Open `https://open.workbuddy.cn/expert/all` in the authenticated browser, under `发布管理` → `专家`. If login is needed, let the user complete it; never store credentials in this skill or its outputs.
2. Within the matching expert's card, read its expert ID, published version, and any separately displayed pending version/status. An older published version is not evidence of the pending version. Clarify an ambiguous account or multiple matching experts; do not create another expert in place of an update.
3. If the target version is already published or under review, report that state and finish the upload workflow. Do not downgrade below a published or pending version by default.
4. Before withdrawing a review request or uploading a ZIP, open the existing expert's details/settings without saving changes. For a published expert, use its published listing rather than a pending replacement. Capture its current price, market categories, avatar, introduction, sample questions, expertise tags, and service category as the pre-upload baseline in task notes or screenshots. Demonstrated matching values were market categories `内容创作` and `教育学习`, and service category `工具 - 办公`; these are recognition clues, not values to overwrite. If any baseline value cannot be established, stop before withdrawal/upload and report what is missing; parsed package values cannot substitute for the original settings.
5. If a confirmed older review request blocks the requested replacement, click `撤回` on that asset. Verify that the `确认撤回` dialog identifies AI-Shifu, then click `确认`. Wait for the asset list before selecting `更新版本`. Withdrawal is conditional, not a routine prerequisite; establish the pending version before withdrawing it.
6. When the asset can be updated directly, click `更新版本` within its card to enter `发布专家`. Do not select `下架`.

## 3. Upload, Check the Details, and Submit

1. In step 1, `配置专家`, click `点击或拖拽上传代码包`. Select the verified ZIP in the native file picker, using its absolute path when useful. Click Open or double-click the file. Do not guess among similar filenames in Downloads.
2. Wait for `上传中…` to finish and inspect the parsed result. Click `继续` only after successful upload/parsing and when the control is enabled. Preserve an upload error instead of repeatedly retrying the same failed operation.
3. In step 2, `确认信息` / `完善信息`, confirm that `识别信息` contains the target expert ID, and that the title, nickname, and version match the package. Stop immediately on an identity or version mismatch; do not advance to submission.
4. Compare the parsed settings with the pre-upload baseline from section 2, allowing only changes explicitly requested by the user. Restore unrequested metadata changes from that baseline when editable; stop if they cannot be restored. Fill only genuinely missing required fields, asking for any necessary unknown value.
5. Click `继续` to step 3, `提交审核`. Recheck the final expert ID and version, and compare the final price and settings with the same pre-upload baseline. Stop if the target/version differs, the price changes without authorization, or any unrequested settings change remains. Do not edit a form version to bypass validation.
6. For an authorized upload/update request, click `提交` once. If the result times out or is unclear, inspect the success page or the same expert's pending status before considering another attempt. Retry only after confirming the first submission did not succeed.

## 4. Verify and Report

- Success requires an `已提交审核` confirmation or an asset-list state explicitly showing the target version under review. A button click, upload progress, successful parsing, or a ledger entry is insufficient.
- The demonstrated success page said `已提交审核，预计 7 个工作日内出结果` and stated that results would arrive through notifications. Use the current page's wording and timing; a submitted request does not establish approval or marketplace availability.
- When possible, return to the asset list and verify the expert ID, target version, and pending status. If it displays only the old published version, retain the success-page evidence and report that limitation instead of uploading again.
- Report the actual Release/version, absolute package path, target expert, final observed status, and available platform URL. For a blocker, identify the exact stage. Status checks and skill maintenance must not trigger a fresh withdrawal, upload, or submission.

This workflow is based on a user demonstration of withdrawal, version update, ZIP selection, information checks, submission, and its success confirmation. The download stage is supplemented by the repository's published Release asset format. The Chinese strings above are exact platform labels and identity-matching values.
