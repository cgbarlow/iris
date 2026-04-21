# Ask AI

Iris has a built-in AI assistant that can answer questions about your architecture content, propose changes, and even generate diagrams from plain-text descriptions.

![Ask AI](/guide/ask-ai.png)

## Anonymous vs signed-in

- **Anonymous visitors** can use Ask AI, rate-limited to **10 requests per hour per IP**. Your conversation lives in the browser tab; it's not persisted.
- **Signed-in users** have a higher rate limit (part of the general bucket, ~1000/min) and their conversations are logged against their user id for the audit trail. They can also use creation prompts and diagram generation (see below).

## The Ask AI page

Two tabs:

### Context

Choose what the AI sees:

- **Sets** — pick one or more sets to include in the prompt. The AI gets every element, relationship, and diagram description in the selected sets.
- **Collections** — pick an entire collection for broader coverage.
- **Diagram drill-down** — if you've picked sets, drill into a specific diagram within them for precise queries.
- **Legislation** — when the DocRef extension is installed, select imported legislation documents as context.
- **File upload** — upload a PDF, DOCX, XLSX, PPTX, CSV, or plain-text file (≤ 5 MB) as **session-scoped** context. The file is held in your browser tab; it's not persisted to Iris.
- **Search results tray** — entities added via **Add to AI context** on search results. See the tray at the top of the Context tab.

### Chat

Type your question in the text field and press **Send** (or `Ctrl + Enter`). The answer streams token-by-token. Under each answer:

- **Provider name and model** used.
- **Tokens in / out** (counts the context size and response length).
- **Duration**.
- **Conversation id** (signed-in only) for follow-up questions within the same thread.

## Provider picker

The toolbar on the Chat tab has a **Provider** dropdown listing every active AI provider configured by admins. Pick the one you want; your choice is remembered for the session.

Providers can include:

- **Anthropic Claude** (direct API).
- **OpenAI GPT** (direct API).
- **Any OpenAI-compatible endpoint** — Ollama, LM Studio, Agentics, OpenRouter, custom gateways.
- Each provider has a health-check dot next to its name: green = responsive, red = unreachable, grey = unchecked.

See the [System Notification Banner](admin#system-notification-banner) section for how admins signal a known provider outage.

## Creation prompts

> **Sign in as architect or admin.**

Ask AI can generate **DoView strategy diagrams** from a plain-text outcome description. The system prompts are editable by admins at **Admin → AI Providers → Creation Prompts** — you can tune the tone, constraints, or notation-specific guidance.

The flow:

1. On a set detail page, click **Create diagram with AI**.
2. Describe the outcome in plain English ("Reduce hospital re-admissions by 10 % over two years").
3. The AI proposes a structured DoView outcome chain (activities → outputs → intermediate outcomes → final impacts).
4. Review and accept — Iris creates the diagram with causal links and positions the elements sensibly.
5. Edit freely from there (see [Canvas Editing](canvas-editing)).

Currently DoView is the only notation with creation-prompt support; others are planned.

## Semantic retrieval (MNEMOS)

> **Admin task to install the extension.**

When the MNEMOS extension is enabled, Iris uses semantic retrieval instead of naive token-budget truncation to pick context for an AI query. For sets with hundreds of elements, MNEMOS ranks elements by semantic relevance to your question — so the AI gets the *right* 5 elements in its context window rather than the *first* 5.

MNEMOS is transparent from the user's perspective — same Ask AI UX, better answers on large sets.

## Advanced provider parameters

> **Admin task on the provider.**

In **Admin → AI Providers**, each provider has an **Advanced Settings** panel exposing:

- `top_p`, `top_k`, `min_p` — sampling parameters.
- `frequency_penalty`, `presence_penalty` — repetition control.
- `stop` sequences — terminate generation on specific strings.

Unsupported parameters are silently omitted on providers that don't accept them.

## Rate limits

- **Anonymous**: 10 AI calls per hour per IP (env `IRIS_RATE_LIMIT_ANON_AI`).
- **Signed-in**: general bucket (default 1000/minute).
- **Provider upstream**: obeys the chosen provider's own rate limits; 429s are surfaced as "AI provider rate-limited the request. Wait a moment and try again." (see v4.1.1 error mapper).

## Where your AI context lives

- **Search-tray items** persist in sessionStorage under `iris-ai-context` — survive navigation but not tab close.
- **Set / collection picks** reset when you leave the Ask AI page.
- **Uploaded files** live only in the tab's memory; never persisted to Iris.
- **Conversation history** (signed-in users) is in `ai_conversations` — audit-logged, queryable from **Admin → Audit**.

## Next steps

- [Search](search) — how entities end up in the AI context tray.
- [Admin & Permissions](admin) — provider setup, creation prompts, MNEMOS.
- [Imports & Data](imports-data) — upload files for one-off context.
