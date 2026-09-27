# SPEC-256-A: Reasoning Effort Setting for AI Providers

Implements **[ADR-256](../ADR-256-Provider-Reasoning-Effort.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `backend/app/ai/models.py` | `ModelParameters.reasoning_effort: Literal["none", "low", "medium", "high"] \| None = None`. Any other value is a 422. |
| `backend/app/ai/client.py` | `OpenAICompatibleClient._payload` adds `reasoning_effort` when it is set, for both chat and streaming. `AnthropicClient` never sends it. |
| `frontend/src/lib/utils/reasoningEffort.ts` | `REASONING_EFFORTS` (the one frontend list of values) and `reasoningEffortFromParams`. |
| `frontend/src/routes/admin/settings/ai/+page.svelte`, `frontend/src/routes/admin/ai/+page.svelte` | **Reasoning effort** select in Advanced Settings: "Default (not sent)" plus the four values. It is saved in `parameters` only when set, and a stored value opens Advanced Settings on edit. |

## 2. Tests (TDD)

- `backend/tests/test_ai/test_models.py`: valid values, omitted by default,
  invalid value rejected.
- `backend/tests/test_ai/test_client.py`: sent in chat and streaming payloads.
  A blank setting gives exactly `{model, messages, stream}`. `test_connection`
  sends it (checked with respx). The Anthropic payload omits it.
- `frontend/tests/unit/reasoningEffort.test.ts`: option order and
  stored-value parsing.

## 3. Acceptance criteria

- A provider with reasoning effort `none` sends `"reasoning_effort": "none"`
  in every chat-completions request, including Test.
- Providers with the field blank send the same request as before.
