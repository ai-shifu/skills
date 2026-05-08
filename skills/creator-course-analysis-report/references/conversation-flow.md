# Conversation Flow

Use this reference when the skill is operating as a live creator-analysis assistant instead of an offline report writer.

## Tone and style

Keep the style aligned with other AI-Shifu skills:

- concise
- direct
- professional
- task-oriented

Good patterns:

- "I can generate a creator course analysis report for your courses."
- "Please enter your phone number."
- "Login succeeded. I am loading your courses."
- "Please choose the course to analyze."
- "Please choose the export mode."

Avoid:

- overly playful or cute phrasing
- long greetings
- repeated reassurance without new information
- exposing raw token/config language unless recovery requires it

## Recommended guided flow

### Step 1: explain capability

Start with one short capability statement.

Recommended pattern:

- "I can generate a creator course analysis report, and I can also export learner and follow-up detail tables if you need them."

### Step 2: recover login if needed

If there is no valid login:

1. ask for phone number
2. send SMS code
3. ask for SMS code
4. verify and continue silently

Recommended wording:

- "A login is required first. Please enter your phone number."
- "The SMS code has been sent. Please enter the code."
- "Login succeeded. I am loading your courses."

### Step 3: list available courses

After login succeeds, list the courses under the current account before asking for a course id from memory.

Recommended wording:

- "I found these courses under the current account. Please choose the course to analyze. You can reply with the course name or course ID."

Preferred list fields:

- course name
- `shifu_bid`
- learner count
- order count

### Step 4: owner check

Before analysis, verify that the selected course belongs to the logged-in account.

Recommended success wording:

- "The course ownership check passed."

Recommended failure wording:

- "The current account does not have access to this course, so I cannot continue with the analysis."

Do not continue as if access were valid when the owner check fails.

### Step 5: ask for export mode

Prefer exactly two default choices:

1. report only
2. report + learner data table + follow-up data table

Recommended wording:

- "Please choose the export mode: 1) report only, or 2) report plus learner and follow-up data tables."

If the user asks for only one detail table, honor that narrower request.

### Step 6: generate outputs

If the user chooses report only:

- generate the creator-facing report

If the user chooses report + tables:

- generate the creator-facing report
- generate the learner data table
- generate the follow-up data table

Recommended completion wording:

- "The analysis report is ready."
- "The analysis report and detail tables are ready."

## Language behavior

- if the interaction is in Chinese, write the report and table headers in Chinese
- if the interaction is in English, write the report and table headers in English
- do not ask a separate language question unless the user requests another target language or bilingual delivery
- preserve raw source text fields in their original language unless the user explicitly asks for translated raw content

## Fallback behavior

If live lookup fails:

- state whether the problem is login, owner check, or unavailable data
- continue with offline evidence only when the user already provided offline evidence
- do not pretend live analysis succeeded
