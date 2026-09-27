# SPEC-255-A: AI Providers Can Be Deleted After They Have Been Used

Implements **[ADR-255](../ADR-255-Delete-Used-AI-Provider.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `backend/app/ai/service.py` | `delete_provider` runs `UPDATE ai_conversations SET provider_id = NULL WHERE provider_id = ?` and the same for `ai_usage_log`, before `DELETE FROM ai_providers`. All three statements share one commit. |

The default provider is still refused (400), as before.

## 2. Tests (TDD)

- `backend/tests/test_ai/test_service.py::test_delete_provider_that_has_been_used`
  turns on `PRAGMA foreign_keys` and creates a provider with one conversation
  and one usage-log row. The delete succeeds, and both rows remain with
  `provider_id` NULL and their model name intact. It failed before the change
  with the same FK `IntegrityError` seen in production.
- `backend/tests/test_ai`: 232 passed.

## 3. Acceptance criteria

- Any non-default provider can be deleted from Admin → Settings → AI, whether
  or not it has been used.
- Conversation history and usage logs are kept.
