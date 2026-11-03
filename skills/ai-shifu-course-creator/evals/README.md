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

### Matched Teaching-Choice Cases

Cases 123–130 reuse the same meeting-record material. Run each case in its own
fresh executor session before comparing the resulting teaching behavior:

| Cases | Comparison |
| --- | --- |
| 123 and 124 | Same novice audience and source, with recognition versus independent writing as the learning goal. |
| 124 and 125 | Same writing goal and source, with different established prior knowledge. |
| 126, 127 and 128 | Same authored response task and simulated delivery, followed by a correct, mistaken or incomplete answer. |
| 129 and 130 | Boundary checks for a short non-interactive lesson and a teacher-defined teaching sequence. |

For the matched pairs, compare the learner task, explanatory support, success
criteria and feedback rather than requiring different method names or layouts.
Keep each answer-path case in a separate session so an earlier simulated answer
does not become context for another path. Send its follow-up messages as separate
turns under the protocol above. The evaluator can inspect the matched outputs;
the executors receive only their own case messages and source material.

### Matched Activity and Evidence Cases

Cases 131–138 extend the teaching-choice set with concrete activity and evidence
boundaries. They are newly authored scenarios, not records of executed runs.
Use the same model, host, tool availability and revision snapshots for a matched
group, while giving every case and revision its own fresh executor session:

| Cases | Comparison or boundary |
| --- | --- |
| 131 and 132 | Support for a current difficulty versus feedback on a changing work product; inspect actual pauses, latest-answer use and appropriate closure. |
| 126–128 and 132 | Correct, mistaken and incomplete responses versus a revision that fixes an old omission but introduces a new error. |
| 133 | Three fixed questions over three rounds; inspect each withheld-feedback interval, actual score, stable question identity and retry set. |
| 134 and 135 | A source-constrained explanation versus an open judgment; distinguish a genuine rewrite from a reasoned retained view. |
| 136 and 137 | An interactive page without an event bridge versus software coaching without screen or execution access; compare which observations are actually available. |
| 138 | An existing group artifact with simulated audience feedback, reported real-user feedback and identified individual contributions. |

For each group, compare observable teaching actions and the evidence supporting
its conclusions. Do not require a method name, a common whole-course sequence,
an internal schema or identical wording. In case 133 the supplied question bank
is part of the teacher input; its answer keys must remain out of simulated
learner delivery until each round ends. Scores are checked from the separate
turns, not inferred from a final summary. Cases 131–135, 137 and 138 require all
listed follow-ups as separate turns; case 136 is an authoring-boundary case.
Keep future learner inputs and all evaluator fields outside the executor
context under the protocol above.

### Natural Requests and Unfinished Learning

Cases 153–155 supplement the more prescriptive activity regressions with
requests that leave teaching decisions to the skill and with unsuccessful
learning paths:

| Case | What to inspect |
| --- | --- |
| 153 | A natural request for meeting-record practice; inspect the chosen teaching actions, actual writing task, success criteria and feedback without supplying those decisions in the teacher request. |
| 154 | A self-study exercise followed by uncertainty, an irrelevant summary, continued difficulty and a request to stop; inspect support, non-achievement closure and truthful evidence. |
| 155 | An independent multistep performance goal under a fixed 90-second non-interactive limit; inspect the feasible demonstration and the unresolved gap without silently changing the goal or constraints. |

Run case 154's follow-ups as separate turns, withholding future learner inputs
and evaluator criteria. Follow the authored activity rather than redesigning
it during simulation to rescue a missing feedback or stopping path. A useful
bounded close may occur before the final follow-up; do not require extra
attempts merely to consume the messages or treat a later stop request as
permission to restart the activity. Inspect both the authored instructions and
the actual handling of the supplied responses.

For revision comparisons, retain the same inputs and execution setup and judge
the resulting teaching behavior, not method-name variety or a fixed interaction
count. These scenarios do not establish real learner outcomes; recording them
here also does not establish that they have been run.

Record scenario additions, static validation and completed behavioral runs as
separate results. For revision comparisons, report each case and turn actually
executed, observed failures and not-assessed criteria; adding these cases or
passing the manifest check does not establish a behavioral pass.

### Frozen-Prompt Runtime Adaptation

Use [fixtures/runtime-adaptation.json](fixtures/runtime-adaptation.json) for a
matched independent-model comparison of runtime teaching. The fixture contains
coordinator-only inputs, including future answers and assessment criteria. Do
not attach the complete fixture to an authoring or delivery executor. Cases
158–163 cover the associated authoring default, explicit-selection compatibility,
existing-course boundary and response-dependent teaching; the frozen comparison
below supplies a separate delivery experiment rather than regenerating a lesson
for every learner.

1. For each skill revision, start one fresh authoring session with only
   `author_request` and that revision's skill. The request supplies the common
   material, goal and fixed verification task without a test learner profile or
   an instruction to enable personalization. Preserve the resulting Course
   Prompt and Teaching Prompt exactly once. Record the skill commit or snapshot,
   author model and host, tools, session and turn identifiers, both artifact
   paths and their SHA-256 hashes. If authoring is incomplete, report that result
   instead of inventing or quietly repairing a frozen pair.
2. Start a fresh delivery session for each entry in `sessions`. Every session for
   that revision receives the same byte-identical frozen Course Prompt and
   Teaching Prompt, plus only its own `registration_context`. Use the host's
   documented course- and lesson-instruction positions where available; otherwise
   record the simulated context arrangement. Ask the executor to deliver these
   artifacts without rewriting them. Do not provide authoring references, other
   learner contexts, answer paths, future turns or evaluator criteria. Recheck
   the artifact hashes across sessions; a repaired or newly authored Prompt is
   a different experiment and cannot rescue a failed frozen run.
3. Let initial delivery reach the fixed task and wait for the learner. Only then
   send that session's `first_answer` as a new user turn. Preserve the complete
   output after each turn. If a session references a follow-up script, send its
   messages one at a time after the preceding assistant turn has completed.
   Future inputs remain with the coordinator. An early or missing pause is an
   observed failure; do not synthesize missing learner submissions or silently
   rewrite delivery to restore the intended path.
4. Compare the six core sessions as the full product of two relevant backgrounds
   and three answers: correct, misconception and incomplete. The backgrounds
   have identical stated prior knowledge and expression preference, so compare
   backgrounds at the same answer and answers within the same background.
   Compare the preference variant with `product_misconception`, changing only
   the stated support preference. The empty and irrelevant-interest contexts
   test neutral fallback with that same mistaken answer. The fixed task,
   required evidence and success criteria stay identical across all nine.
5. Use the three follow-up scripts to inspect an independent attempt, updated
   background with a newly introduced error, and continued difficulty followed
   by a stop. Judge the actual current submission: a repaired old error does
   not make a new population-inference error correct. An explicit request for
   independent work should not receive an advance solution. A stop or unresolved
   difficulty must not be reported as independent completion or mastery.
6. Give an independent evaluator the frozen artifacts, actual registration
   context, full chronological outputs and coordinator-only criteria. Hide skill
   revision labels and randomize revision order for the evaluator while retaining
   the mapping with the coordinator. Evaluate source fidelity, relevant observable
   support, current-answer use, waiting, fixed standards, fallback and closure;
   attach an output location to each pass or failure. Different wording, role
   labels, length or method names alone do not establish adaptive teaching. Nor
   must every background produce a different action when the same support is
   justified by the available evidence. Report unobserved behavior as
   not-assessed and retain authored, simulated and platform evidence separately.

| Sessions | Controlled comparison |
| --- | --- |
| `product_correct`, `product_misconception`, `product_incomplete` | Same product-work background and preferences, three actual-answer paths. |
| `teacher_correct`, `teacher_misconception`, `teacher_incomplete` | Same teaching-work background and preferences, the same three answer paths. |
| `preference_misconception` | Product background and prior knowledge unchanged; only support preference changes. |
| `empty_misconception`, `irrelevant_misconception` | The same mistaken answer with absent or irrelevant registration context. |

For an old/new revision comparison, freeze one pair per revision and run the
same nine session inputs for each, with matched model, host and tools. Keep
revision outputs out of the other revision's authoring and delivery sessions.
The resulting eighteen sessions are local model simulations, not platform
pause/resume tests, newly published courses or real-learner learning evidence.
The fixture is evaluation input, not a course-directory schema, CLI payload or
requirement to build a model runner. Its strings and keys must not be serialized
into the authored course. Record each case and turn actually run, including
failures and incomplete paths, rather than reporting the matrix as executed
because it exists in the repository.

From the repository root, run the static manifest check with:

```bash
python3 -m unittest discover -s tests -p 'test_validate_skill_quality.py'
```

A passing result confirms the checked artifact contracts and manifest shape. It
does not substitute for the externally coordinated runs above.
