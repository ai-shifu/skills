# Frozen-prompt adaptation comparison

Executed on 2026-11-03. This is an independent-model simulation, not platform verification or evidence of real learner learning gains.

## Setup and integrity

- One fresh author per skill revision received the same [teacher request and fixed source task](../fixtures/runtime-adaptation.json), without test learner contexts, future answers or evaluator criteria. Authoring used baseline `2f1125119bdb090abfb855619b3929c14259ef8e` and updated guidance `5e14c6296af9e1529fec0cb515b6264ceb931055`; the execution-boundary clarification is `989c52c`.
- Each revision then used one byte-identical Course Prompt / Teaching Prompt pair in nine fresh delivery agents. The first six sessions crossed two relevant backgrounds with three answer types; the remaining three changed only support preference, removed context, or supplied an irrelevant interest.
- Root independently verified 18 unique agent IDs, all 42 captured output hashes, each first answer against its fixture, and unchanged original, anonymous and checked-in prompt hashes. There were 42 separate dispatches, with future answers sent only after the preceding teaching turn completed.
- Baseline: 20 observed teaching turns. Updated: 22. All 18 planned test observations completed; 10 observations ended while the lesson was waiting for another learner input. Test completion does not mean learner graduation.
- Six follow-up inputs were not sent: four optional transfer inputs were outside the frozen lessons; the baseline had already closed before a final correction and before the stop input. These paths are not assessed, not failures.
- Host: Codex team subagents, inheriting the same parent-session model without overrides. The exact model revision and token counts were not exposed. Course and lesson instructions were supplied through the initial simulation message, not the actual platform instruction slots.

## Frozen artifacts

| Revision | Artifact | SHA-256 |
| --- | --- | --- |
| baseline | [course-prompt.md](../fixtures/runtime-adaptation/prompts/baseline/course-prompt.md) | `20095e3d4dab603f0cdd54ba4028a6be196551413f4b6a560e22c7c7c8d797db` |
| baseline | [teaching-prompt.md](../fixtures/runtime-adaptation/prompts/baseline/teaching-prompt.md) | `bf06fe8cbcb401d7b7deb2b4eb13ca287ff1269da01b9c1d77d63f2d35879646` |
| updated | [course-prompt.md](../fixtures/runtime-adaptation/prompts/updated/course-prompt.md) | `6bf122d9c548f59da39528ddc454c2e263f436f8c3a1cc4475131e592ae5467c` |
| updated | [teaching-prompt.md](../fixtures/runtime-adaptation/prompts/updated/teaching-prompt.md) | `302c0ddaff5e51ed5ec23f80c0497566aff505b2df9bef93486b0c5975b77035` |

## Observed behavior

An independent reviewer inspected anonymous labels without the version mapping. No critical factual, answer-leakage, unauthorized-reopening or false-completion failure was observed. After review, label A maps to updated and B to baseline.

| Comparison | Observation |
| --- | --- |
| Relevant background | Updated connects product interviews to overgeneralized user needs, and classroom history material to overgeneralized attitudes. Baseline uses a neutral workplace entry consistent with its frozen authorization. |
| Correct / mistaken / incomplete | Both recognize correct answers, target the submitted support/scope error and ask for missing reasoning without inventing a misconception. |
| Updated background and new error | Updated uses the content-editing correction and catches the new population-percentage error; its next response recognizes the corrected sample boundary. Baseline truthfully closes at its earlier authored retry limit. |
| Support preference | The focused-clue preference has observable bounded support in both samples. One run per condition cannot establish a stable causal preference effect or a universal advantage. |
| Empty / irrelevant context | Neutral teaching and actual-answer feedback remain available; neither requires a background questionnaire or an unrelated jazz analogy. |
| Stuck / stop | Updated changes support and then honors the actual stop without claiming completion. Baseline stop handling is not assessed because its earlier authorized close already ended the activity. |

The contrast supports improved background-connected teaching in this recorded pair. It does not imply that neutral baseline teaching violated its own instructions, that longer retry limits are inherently better, or that every learner requires a different path.

## Selected captured evidence

### Updated product-task connection

Source: `A/session-01/turn-01.md`. Full-output SHA-256: `e518b6fdde5c3dc53c891cff2b30d008e30e70966e114f53477d3023b1ed0855`.

> AI 给出出处之后，仍要检查它写出的这句话能否使用。整理用户访谈时，这会直接影响你准备交付的需求结论：少数人提出的意见，不能只因附上了出处，就写成所有用户的需求。

### Updated classroom-task connection

Source: `A/session-04/turn-01.md`. Full-output SHA-256: `d43feb6ba78421dfc7ad76f7efd1d675a5ed764ba3a4d96f9fce7f09eb4b9b0c`.

> AI 给出出处之后，你仍要检查：它写出的这句话，能不能放进课堂材料。整理历史材料时，个别记述可能有真实来源，但这并不意味着它能代表所有人的态度；核验会直接影响你准备向学生呈现的那句概括。

### Baseline neutral classroom-context entry

Source: `B/session-04/turn-01.md`. Full-output SHA-256: `2eb6818e85b64f8f19455f3980b8924a814ceaf8f2b24be06150677994b40df5`.

> 在把 AI 的整理结果写进报告或发给同事前，你需要判断：**这条引用是否真的支撑这句话？**

### Updated background correction and new percentage error

Source: `A/session-02/turn-03.md`. Full-output SHA-256: `179f57a713f3580a7854bd69d7cf0268679bfa94c7047027f93f51df22e7913a`.

> 核验文章引用时，文中的比例同样要能对回原文中的人群。
>
> 1. **你已保留原文存在的判断，也把计算写成了参与者中的比例。** 这部分可以保留。
> 2. **仍要修订的是比例的对象。** 你前面写“3/5 的参与者”，修正句却变成“60% 的所有用户”。原文给的是“5 名自愿参与者”，自愿参与反馈不能自动代表所有用户。请对照这两个对象，收紧修正句的主语，让计算和表述一致。
> 3. 还需补明：原 AI 句能否直接使用；其余 2 人没有谈及该功能，是否足以判断他们的态度。
>
> 请据此再修订一次同一道题，保留已答对的部分，完整写出使用判断、三个核验及一句修正。

### Updated focused-clue preference

Source: `A/session-07/turn-02.md`. Full-output SHA-256: `282810d19a00ba50be1ea2e27a09946f387f059bed77f5b91d1afd156698b278`.

> 1. 你确认“原文已经找到，人数也核对了”，这一项判断正确，可以保留。
>
> 2. 需要重新检查的是：**有真实出处，只能回答原文是否存在；还不能据此确认 AI 的整句话有依据。** 你指出有人提出需求，但待核验的是“所有用户都需要”这一整句。
>
> 先给你一个线索：把原文中描述反馈来源的词，与 AI 结论中描述对象的词并排写出来，看看两者覆盖的是不是同一群人。
>
> 请保留已答对的部分，在同一份答复中写出“原文的词”和“AI 扩出的词”，再据此补全或修订这四部分：**使用判断、存在核验、支持与范围核验、一句修正**。你目前还没有说明结论范围，也没有写出修正句，需要一并补上。

### Updated stop without completion

Source: `A/session-06/turn-04.md`. Full-output SHA-256: `8e5080ef618709ca40f8d5f1384195411b68924b401b8ae82a83675d1b7c234a`.

> 今天就停在这里。你已说明原文能找到，仍需留意**原文是否支持这句具体结论**；本次尚未完成范围判断和修正句，不能据此认定你已独立完成核验。
>
> **先确认原文存在，再确认原文支持这句话，最后让结论停在证据覆盖的范围内。**

## Validation and limits

- Local checks: skill quality passed for all three skills; 61 targeted contract tests, 382 repository tests and 183 release-tool tests passed. A local preview build and package verification also passed. No version bump or release was performed.
- Follow the [frozen-prompt protocol](../README.md#frozen-prompt-runtime-adaptation) with the supplied fixture and frozen artifacts. Independent authoring and delivery sessions are required; do not give executors the whole fixture.
- Full chronological inputs, outputs, dispatch metadata, the blinded review and root integrity result remain in the ignored local workspace `ai-shifu-course-creator-workspace/runtime-adaptation/iteration-1/`. This report includes selected captured evidence rather than claiming every conditional path was exercised.
- There is one authored pair and one delivery per condition. Platform profile injection, rendered controls, real pause/resume behavior, profile writes, durable recall, transfer, delayed retention and real learning gains are not assessed. Initial prompt contents and separate-turn dispatches establish the recorded simulation setup, not hidden host internals.
