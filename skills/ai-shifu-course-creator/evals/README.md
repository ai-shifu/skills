# Course Creator Behavioral Evaluations

`evals.json` contains behavioral scenarios for an external evaluation host or a
human coordinator. This repository does not include a model-conversation runner.
The repository quality checks validate the manifest and static skill contracts;
they do not execute or score these conversations. `trigger_eval.json` separately
contains skill-discovery cases.

## Scenario Fields

| Field | Meaning |
| --- | --- |
| `id` | Unique scenario identifier. |
| `eval_name` | Optional human-readable name. |
| `prompt` | The first teacher message sent to the executor. |
| `followup_turns` | Optional ordered list of nonblank teacher messages. An absent field or an empty list means a single-turn scenario. |
| `files` | Input fixtures made available to the executor. |
| `expected_output` | Outcome summary for the evaluator, withheld from the executor. |
| `expectations` | Observable criteria for the evaluator, withheld from the executor. |

## Run a Scenario

1. Record the scenario ID, skill revision or snapshot, model, host, available
   tools, and input fixtures. Start a fresh executor session with that skill and
   the scenario's `prompt`. Keep evaluation criteria, future teacher messages,
   and other runs' outputs out of the executor's context.
2. Wait for the assistant turn to finish, then preserve its response and any
   artifacts. If `followup_turns` is nonempty, send only the next message as a
   new user turn in the same session, retaining the prior conversation and
   artifacts. Repeat after each completed assistant turn until all messages
   have been sent. A host's separate resumed task turn may serve as the user
   turn; record which mechanism was used.
3. Preserve the host conversation or dispatch log, including session and turn
   identifiers when available, and the response/artifact snapshots for each
   turn. A Markdown transcript assembled afterward is useful for review, but
   its headings alone do not establish that separate turns occurred.
4. Give an independent evaluator the complete conversation, artifacts,
   `expected_output`, and `expectations`. Judge the whole exchange, including
   whether later teacher choices are respected. Report unobservable criteria
   as not assessed and record incomplete runs explicitly.

For example, a coordinator with `spawn_agent` and `followup_task` can start the
executor with `prompt`, wait for that agent's completed response, then call
`followup_task` on the same agent with one follow-up message at a time. Keep the
coordinator's full case data outside the executor's initial context. Equivalent
host APIs or manually submitted chat messages are also suitable.

Do not give the executor the entire manifest, append future messages to its
initial prompt, or ask it to read successive teacher-message files and answer
them during one assistant turn. That is a staged replay, not a separate-turn
conversation. It can provide artifact feedback, but it cannot validate the
collaboration behavior tested by a multi-turn scenario. If the host cannot
resume the same session with separate turns, mark the scenario skipped or
incomplete with that limitation; do not silently run only `prompt` or report a
multi-turn pass.

## Compare Skill Revisions

Use fresh executor sessions for each revision with the same scenario messages,
fixtures, model, tools, and execution protocol. Withhold the other revision's
outputs from each executor. Record differences in setup and distinguish static
checks, staged replays, and completed separate-turn runs in the report. A small
sample of model runs is behavioral evidence for those runs, not proof of a
general improvement in learner outcomes.

From the repository root, run the static manifest check with:

```bash
python3 -m unittest discover -s tests -p 'test_validate_skill_quality.py'
```

A passing result confirms the checked artifact contracts and manifest shape. It
does not substitute for the externally coordinated runs above.
