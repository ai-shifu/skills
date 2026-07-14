# Platform Authentication

Read this file before any CLI-backed course-target, deployment, management, or analytics task.

## Verify First

Always use `scripts/shifu-cli.py`. Never read tokens directly, construct authentication headers, or make raw platform API calls.

1. Run `shifu-cli.py verify` before considering login.
2. Handle the exit code:
   - Exit `0`: the token is valid; continue without logging in.
   - Exit `1`: guide the user through one [Agent Login Flow](#agent-login-flow).
   - Exit `2`: treat this as a network problem and retry later; do not start a new login.
3. Never re-login because token state is uncertain; `verify` is the source of truth.
4. Protect the SMS quota: each phone number receives at most five codes per day, so do not create duplicate login sessions.

After login, rerun `verify` once before continuing the requested workflow.

The command syntax, exit codes, and token-write side effects are defined in `cli/cli-reference.md#authentication`; this file owns the decision and conversation flow.

## Agent Login Flow

Use one login session per phone number. Each number is capped at five SMS codes per day, so a duplicate send wastes quota and can lock the user out.

- Collect the phone number, then send `login --phone <phone>` exactly once.
- If the user says the code has not arrived, tell them it normally arrives within 60 seconds; do not resend.
- After the first or second wrong code, ask the user to re-enter it without sending another SMS.
- Only after the third consecutive wrong code, send `login --phone <phone>` one final time for that session.

Run this fixed sequence without readiness questions, status checks, acknowledgment pauses, or unrelated intake:

1. In one short turn, explain that login uses SMS without a password, a four-digit code will arrive, the user should reply with it next, success saves the token locally, and a new number creates an account automatically; then ask for the phone number in the same turn.
2. Run `python3 {skillDir}/scripts/shifu-cli.py login --phone <phone>` once.
3. Ask only for the four-digit verification code.
4. Run `python3 {skillDir}/scripts/shifu-cli.py login --phone <phone> --sms-code <4-digit-code>`.
5. Rerun `verify`; on success, continue the original task.

Handle outcomes as follows:

| Outcome | Agent decision |
|---|---|
| `verify` exit 0 | Continue without login. |
| `verify` exit 1 | Run this SMS flow once. |
| `verify` exit 2 | Retry verification later; do not trigger login. |
| Login reports `SMS sent` | Wait for the user-provided code; do not resend. |
| Login reports `smsSendTooFrequent` | Wait 60 seconds; do not submit the phone again. |
| First or second code error | Ask for the code again without resending. |
| Third consecutive code error | Send one final SMS, then ask for the new code. |
| An API call reports expired-token codes `1001`, `1004`, or `1005` | Return to `verify`, then follow its result. |
