# Language Resolution Policy

## Priority Order

Resolve target language with this strict priority:

1. `explicit_output_language_request` — language explicitly stated in the current user prompt.
2. `target_language_parameter` — `target_language` field supplied in the input payload (BCP-47 recommended).
3. `prior_context_language_directive` — language requirement declared **outside** the current prompt but visible to the skill: project/system instructions (e.g. `CLAUDE.md`), earlier turns of the same conversation, or directives injected by the calling agent. The skill cannot read external platform/account locale settings, so only in-context directives count here.
4. `prompt_language_detection` — language detected from the wording of the current user prompt itself.
5. `source_material_dominant_language` — the dominant language of the supplied course material.
6. `default_fallback_language` — `zh-CN`.

## Control Fields

- `target_language` (BCP-47 recommended, for example `fr-FR`, `ja-JP`, `zh-CN`)
- `bilingual_output` (`true|false`)
- `term_policy` (`preserve|translate|mixed`)
- `quote_policy` (`translate_only|original_plus_translation`)

## Rules

- Do not restrict supported languages to a fixed list.
- If output language is explicit, source-language distribution must not override it.
- Learner-facing script text must follow resolved target language unless `bilingual_output` is true.
