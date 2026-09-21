# Platform Authentication

## Required References

- `language-policy.md`
- `cli/cli-reference.md#authentication`

## Conditional References

- When opening a browser authorization link: `open-in-app-browser.md`

## Select Site Before Connecting

When the user explicitly requests a service by URL or by “domestic” / “international,” inspect `profile list` before checking `site` and match the configured service address, not the profile name. A unique match is an explicit selection for this task; multiple matches require the user to choose the account/profile. If profiles exist but none matches, ask for the new profile's name and configure it with `profile set <name> --base-url <address>`; do not repoint the default. With no profiles, use the initial setup below. `cn` and `com` are address shortcuts only. For a user-requested profile setup, honor arbitrary names, including Chinese and spaces, and do not ask a region question when the URL is already known.

1. Resolve the task's execution context with `python3 scripts/shifu-cli.py site`, adding `--profile <name>` when the user explicitly selects one. Its output is configuration control data, not user-facing content. Profile names have no region meaning; never choose one by its name, recent use, a course directory, or login status.
2. If `status=configured`, silently reuse the returned address and profile without asking again. Without an explicit profile, the CLI uses complete temporary environment configuration when present, otherwise the default profile. Selection and credential precedence are defined in `cli/cli-reference.md#profiles`. Keep the resulting context fixed for this task: pass `--profile <name>` on every later platform command for a named profile, including verification, login continuation, uploads, course operations, and handoff lookups. Using another profile does not change the default.
3. If `status=selection_required`, ask the user to select their current region, in the resolved conversation language. In Chinese, use “请选择你所在的地区：” with exactly two options: “中国” and “其他国家或地区”. In English, use “Please select your current region:” with exactly two options: “China” and “Other countries or regions”. Do not display domains, CN/COM codes, CLI commands, configuration fields, or a site-selection explanation. Do not offer custom deployment as a default third choice. Do not infer the answer from conversation language or IP. An explicit answer already provided in the conversation does not need to be asked again; otherwise wait for the answer before connecting.
4. Map “中国” / “China” to `site --set cn` and “其他国家或地区” / “Other countries or regions” to `site --set com` internally. If the user explicitly requests a custom deployment, use `site --url <user-supplied-URL>` instead; ask for its service URL only if it is missing. An explicitly requested service or existing configuration takes precedence over regional defaults.
5. Initial `site` setup creates an ordinary profile named `default`; the user need not choose a profile name during first use. Require `status=configured` with the intended address internally, fix the returned profile for the task, then continue verification or the original task immediately. Do not announce the selected address, echo configuration output, or ask for another confirmation. If saving fails, explain the impact in plain language and keep platform operations paused; do not silently use another site. The selection persists across sessions and Skill upgrades and does not select the conversation or course language.

The hidden information is initialization machinery, not links the user needs to act on: browser authorization links, course links, and eligible official contact links still follow their normal display rules. Only show configuration details when the user explicitly requests them for inspection or troubleshooting; do not add them to normal progress, success, or error messages.

An unknown profile, incomplete temporary configuration, or mismatched credential source is a configuration error, not an invitation to try another profile. If changing a profile's URL is blocked by its authorization state, explain that the user must log out of that profile first or create a separate profile; never delete credentials or change the destination to bypass the error. Temporary configuration cannot start or resume browser authorization: select or configure a named profile explicitly for that flow, preserving the user's intended service.

## Verify Before Login

Use `scripts/shifu-cli.py`; never read tokens directly, construct authentication headers, or make raw platform API calls. Write every user-facing login prompt and failure explanation according to `language-policy.md`.

Run `verify` with the task's selected context before deciding whether login is needed:

- Exit `0`: continue the requested platform operation without logging in.
- Exit `1`: run one browser authorization session.
- Exit `2`: report a network or service problem and retry `verify` later; do not start an authorization session.
- Exit `4`: resolve the site using Select Site Before Connecting; do not treat it as an expired login.

If any authenticated command returns token error `1001`, `1004`, or `1005`, run `verify` and apply the same decision again. After a successful login, run `verify` once before continuing.

## Agent Browser Authorization Flow

1. Run `login --profile <name>` exactly once for the task's selected profile.
2. Open the verification link exactly as printed using the shared browser reference. If opening is unavailable, failed, queued, or skipped at the user's request, keep the same pending authorization request and continue with the original clickable link; do not run `login` again for a browser outcome.
3. In one short turn, give the user the verification link exactly as printed and explain that approving it signs this device in, that the page shows which device is asking, and that they must press the approve button there themselves. Never click approve for the user. The CLI prefers `verification_uri_complete`, which carries the pairing code, but can fall back to `verification_uri`, which may require manual code entry. Include the separately printed pairing code and tell the user to enter it if the page asks; do not claim every link already carries it or modify the returned URL. Mention that an account is created on first use and that a browser session already signed in will not have to sign in again.
4. Run `login --wait --profile <name>` with the same name. Keep that name in any continuation command shown to the user.
5. Act on the exit code:
   - `0`: authorized and stored. Run `verify` once, then continue the original operation.
   - `3`: still waiting. Ask the user to finish approving, then run `login --wait` again.
   - `1`: denied, expired, or never started. Explain what happened, and start over with `login` only if the user wants to retry.

Do not insert readiness checks, account-status questions, acknowledgements, recaps, or other pauses between these steps.

## Failure Handling

| Result | Agent action |
| --- | --- |
| `login` printed a link | Use the shared browser reference, hand the link to the user unchanged, and wait. Do not start a second request. |
| Browser opening did not complete | Follow the shared browser result handling and wait on the same authorization request. Do not run `login` again. |
| `login --wait` exits `3` | Ask the user to approve in the browser, then run `login --wait` again. |
| User says the page reports an invalid or expired code | Run `login` once more to issue a fresh link. |
| User denied the request by mistake | Run `login` once more to issue a fresh link. |
| Network failure during `login` or `login --wait` | Stop and retry `verify` later; do not open repeated authorization requests. |

Never run `login` again for the same profile while the user is still looking at its earlier link: a new request replaces that profile's pending one on disk, so approving the older link would leave nothing to collect. Other profiles have independent authorization sessions.

## Never Do

- Never print, echo, or repeat the contents of the credentials file.
- Never ask the user for a phone number, verification code, or password. The CLI does not collect any of them, and no agent-driven flow needs them.
