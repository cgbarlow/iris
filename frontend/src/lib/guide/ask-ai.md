# Ask AI

Iris has a built-in AI assistant that can answer questions about your content.

![Ask AI](/guide/ask-ai.png)

## Context tab

On the Context tab you choose what the AI sees:

- **Sets** — pick one or more sets to include in the prompt.
- **Collections** — pick a whole collection for broader coverage.
- **Legislation** — optional DocRef documents (if the extension is installed).
- **File upload** — upload a PDF, DOCX, XLSX, PPTX, CSV, or plain-text file as session-scoped context.
- **Diagram scope** — drill into a specific diagram for precise queries.

## Chat tab

Type your question, pick a provider/model if you want, and send. The response streams back as it arrives; tokens-in, tokens-out, and duration are shown under each answer.

## Anonymous rate limit

When you aren't signed in, Ask AI is still available but rate-limited to **10 requests per hour per IP** to bound cost on the public deployment. Sign in to use the full-usage bucket.

## Providers

Admins configure AI providers (Anthropic, OpenAI, local, etc.) in the admin panel. Users with multiple providers available see a model picker in the chat toolbar.
