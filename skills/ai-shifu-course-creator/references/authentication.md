# Platform Authentication

## Required References

- `language-policy.md`
- `cli/cli-reference.md#authentication`

## Select Site Before Connecting

Only apply this step when the active route needs platform access. Local/artifact-only authoring does not ask for a site.

1. Run `python3 scripts/shifu-cli.py site` internally. Its output is configuration control data, not user-facing content.
2. If `status=configured`, silently reuse the returned address without asking again. An existing explicit `SHIFU_BASE_URL` takes precedence over the remembered selection.
3. If `status=selection_required`, ask the user to select their current region, in the resolved conversation language. In Chinese, use “请选择你所在的地区：” with exactly two options: “中国” and “其他国家或地区”. In English, use “Please select your current region:” with exactly two options: “China” and “Other countries or regions”. Do not display domains, CN/COM codes, CLI commands, configuration fields, or a site-selection explanation. Do not offer custom deployment as a default third choice. Do not infer the answer from conversation language or IP. An explicit answer already provided in the conversation does not need to be asked again; otherwise wait for the answer before connecting.
4. Map “中国” / “China” to `site --set cn` and “其他国家或地区” / “Other countries or regions” to `site --set com` internally. If the user explicitly requests a custom deployment, use `site --url <user-supplied-URL>` instead; ask for its service URL only if it is missing. An explicitly requested service or existing configuration takes precedence over regional defaults.
5. Require `status=configured` with the intended address internally, then continue verification or the original task immediately. Do not announce the selected address, echo configuration output, or ask for another confirmation. If saving fails, explain the impact in plain language and keep platform operations paused; do not silently use another site. The selection persists across sessions and Skill upgrades and does not select the conversation or course language.

The hidden information is initialization machinery, not links the user needs to act on: browser authorization links, course links, and eligible official contact links still follow their normal display rules. Only show configuration details when the user explicitly requests them for inspection or troubleshooting; do not add them to normal progress, success, or error messages.

These commands handle initial setup, not migration of a signed-in account between sites. If existing credentials block setup, restore their original explicit service configuration; never delete credentials or change the destination to bypass the error.

## Verify Before Login

Use `scripts/shifu-cli.py`; never read tokens directly, construct authentication headers, or make raw platform API calls. Write every user-facing login prompt and failure explanation according to `language-policy.md`.

Run `verify` before deciding whether login is needed:

- Exit `0`: continue the requested platform operation without logging in.
- Exit `1`: run one browser authorization session.
- Exit `2`: report a network or service problem and retry `verify` later; do not start an authorization session.
- Exit `4`: resolve the site using Select Site Before Connecting; do not treat it as an expired login.

If any authenticated command returns token error `1001`, `1004`, or `1005`, run `verify` and apply the same decision again. After a successful login, run `verify` once before continuing.

## Agent Browser Authorization Flow

1. Run `login` exactly once.
2. In one short turn, give the user the verification link exactly as printed and explain that opening it signs this device in, that the page shows which device is asking, and that they must press the approve button there. Mention that the link already carries the pairing code, that an account is created on first use, and that a browser session already signed in will not have to sign in again.
3. Run `login --wait`.
4. Act on the exit code:
   - `0`: authorized and stored. Run `verify` once, then continue the original operation.
   - `3`: still waiting. Ask the user to finish approving, then run `login --wait` again.
   - `1`: denied, expired, or never started. Explain what happened, and start over with `login` only if the user wants to retry.

Do not insert readiness checks, account-status questions, acknowledgements, recaps, or other pauses between these steps.

## Failure Handling

| Result | Agent action |
| --- | --- |
| `login` printed a link | Hand the link to the user unchanged and wait. Do not start a second request. |
| `login --wait` exits `3` | Ask the user to approve in the browser, then run `login --wait` again. |
| User says the page reports an invalid or expired code | Run `login` once more to issue a fresh link. |
| User denied the request by mistake | Run `login` once more to issue a fresh link. |
| Network failure during `login` or `login --wait` | Stop and retry `verify` later; do not open repeated authorization requests. |

Never run `login` again while the user is still looking at an earlier link: a new request replaces the pending one on disk, so approving the older link would leave nothing to collect.

## Never Do

- Never print, echo, or repeat the contents of the credentials file.
- Never ask the user for a phone number, verification code, or password. The CLI does not collect any of them, and no agent-driven flow needs them.
