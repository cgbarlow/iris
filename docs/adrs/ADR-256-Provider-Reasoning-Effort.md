# ADR-256: Reasoning Effort Setting for AI Providers

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-256 |
| **Initiative** | Let admins turn off thinking on reasoning models (#310) |
| **Proposed By** | Product owner (issue #310, 2026-09-27) |
| **Date** | 2026-09-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** AI providers that point at reasoning models, such as
Qwen3.6 35B-A3B served by LM Studio, which think by default,

**facing** thinking that uses up the `max_tokens` budget and often leaves Iris
with an empty answer, with no way to stop it from the provider form. In the
issue's tests against LM Studio 0.4.25, `reasoning_effort: "none"` was the only
request parameter that stopped the thinking. `chat_template_kwargs` and
editing the chat template had no effect,

**we decided to** add an optional `reasoning_effort` field (`none` / `low` /
`medium` / `high`) to `ModelParameters`. It is stored in the provider's
existing `parameters` JSON. `OpenAICompatibleClient` sends it as
`reasoning_effort` in the chat-completions body only when it is set. The
Advanced Settings panel gets a **Reasoning effort** dropdown whose blank
default means "not sent",

**and neglected** (a) sending `chat_template_kwargs.enable_thinking`. Rejected:
the issue showed it has no effect on LM Studio; (b) a free-text field for extra
request-body JSON. Rejected: it can't be validated, and it's a much bigger
feature than this issue needs; (c) mapping the setting to Anthropic's
`thinking` parameter. Rejected: Iris doesn't turn on extended thinking for
Anthropic, so there's nothing to turn off. The Anthropic client ignores the
field; (d) a new column on `ai_providers`. Rejected: generation parameters
already live in the `parameters` JSON, so no migration is needed,

**to achieve** fast, non-empty answers from local reasoning models, while
providers that leave the field blank send exactly the same request as before,

**accepting that** whether the setting has any effect depends on the server
and the model. Servers that don't know `reasoning_effort` may ignore it or
reject it. Admins leave it blank for those.

---

## Consequences

- No schema change and no migration. Existing providers have no
  `reasoning_effort` key, so their requests don't change.
- The endpoints are unchanged (`parameters` gains an optional key), so surface
  parity is unaffected.
- Test uses the stored provider, so it sends the setting too.

## Dependencies

- ADR-093 (AI providers), ADR-114 (advanced provider parameters).

## References

- Implementation spec: [SPEC-256-A](./specs/SPEC-256-A-Provider-Reasoning-Effort.md)
- Issue #310
