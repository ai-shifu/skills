# Platform Authentication

## Required References

- `language-policy.md`
- `cli/cli-reference.md#authentication`

## Verify Before Login

Use `scripts/shifu-cli.py`; never read tokens directly, construct authentication headers, or make raw platform API calls. Write every user-facing login prompt and failure explanation according to `language-policy.md`.

Run `verify` before deciding whether login is needed:

- Exit `0`: continue the requested platform operation without logging in.
- Exit `1`: run one browser authorization session.
- Exit `2`: report a network or service problem and retry `verify` later; do not start an authorization session.

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
