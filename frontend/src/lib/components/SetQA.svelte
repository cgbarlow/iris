<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import type { AIConversation } from '$lib/types/api';

	interface Props {
		setId: string;
	}

	let { setId }: Props = $props();

	type ConvEntry = {
		id: string;
		question: string;
		answer: string;
		model_used: string;
		tokens_in: number | null;
		tokens_out: number | null;
		duration_ms: number | null;
		created_at: string;
	};

	let conversations = $state<ConvEntry[]>([]);
	let question = $state('');
	let asking = $state(false);
	let error = $state<string | null>(null);
	let streamingAnswer = $state('');
	let streamingQuestion = $state('');
	let historyLoaded = $state(false);
	let chatContainer: HTMLDivElement | undefined = $state();
	let copiedId = $state<string | null>(null);

	function isClearedSession(): boolean {
		return sessionStorage.getItem(`qa-cleared-${setId}`) === '1';
	}

	$effect(() => {
		if (setId && !isClearedSession()) loadHistory();
		else historyLoaded = true;
	});

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}

	async function loadHistory() {
		try {
			const convs = await apiFetch<AIConversation[]>(`/api/ai/sets/${setId}/conversations?limit=50`);
			conversations = convs.map((c) => ({
				id: c.id,
				question: c.question,
				answer: c.answer,
				model_used: c.model_used,
				tokens_in: c.tokens_in,
				tokens_out: c.tokens_out,
				duration_ms: c.duration_ms,
				created_at: c.created_at,
			})).reverse(); // oldest first for chat order
			historyLoaded = true;
			setTimeout(scrollToBottom, 50);
		} catch {
			historyLoaded = true;
		}
	}

	async function ask() {
		const q = question.trim();
		if (!q || asking) return;

		streamingQuestion = q;
		question = '';
		error = null;
		asking = true;
		streamingAnswer = '';

		setTimeout(scrollToBottom, 50);

		try {
			const token = getAccessToken();
			const resp = await fetch(`/api/ai/sets/${setId}/ask?stream=true`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
				body: JSON.stringify({ question: q }),
			});

			if (!resp.ok) {
				const errData = await resp.json().catch(() => null);
				throw new Error(errData?.detail || `HTTP ${resp.status}`);
			}

			const reader = resp.body?.getReader();
			if (!reader) throw new Error('No response stream');

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					try {
						const payload = JSON.parse(line.slice(6));
						if (payload.chunk) {
							streamingAnswer += payload.chunk;
							scrollToBottom();
						} else if (payload.done) {
							conversations = [
								...conversations,
								{
									id: payload.conversation_id,
									question: q,
									answer: streamingAnswer,
									model_used: payload.model_used,
									tokens_in: null,
									tokens_out: null,
									duration_ms: payload.duration_ms,
									created_at: new Date().toISOString(),
								},
							];
							streamingAnswer = '';
							streamingQuestion = '';
							scrollToBottom();
						} else if (payload.error) {
							throw new Error(payload.error);
						}
					} catch (e) {
						if (e instanceof SyntaxError) continue;
						throw e;
					}
				}
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Failed to get answer';
			question = q;
			streamingAnswer = '';
			streamingQuestion = '';
		}
		asking = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			ask();
		}
	}

	function clearConversation() {
		conversations = [];
		streamingAnswer = '';
		streamingQuestion = '';
		question = '';
		error = null;
		sessionStorage.setItem(`qa-cleared-${setId}`, '1');
	}

	async function copyToClipboard(text: string, id: string) {
		try {
			await navigator.clipboard.writeText(text);
			copiedId = id;
			setTimeout(() => { copiedId = null; }, 2000);
		} catch {
			// fallback
		}
	}

	function formatDuration(ms: number | null): string {
		if (ms == null) return '';
		return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
	}

	// Safe markdown rendering (Protocol 7)
	function renderMarkdown(text: string): string {
		const raw = marked.parse(text, { async: false }) as string;
		return DOMPurify.sanitize(raw, {
			ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'del', 'span'],
			ALLOWED_ATTR: ['href', 'title', 'class'],
		});
	}
</script>

<div class="flex flex-col" style="height: 100%">
	<!-- Header with clear button -->
	<div class="mb-3 flex items-center justify-between">
		<p class="text-xs" style="color: var(--color-muted)">Press Enter to send, Shift+Enter for newline</p>
		{#if conversations.length > 0}
			<button
				onclick={clearConversation}
				class="rounded px-3 py-1 text-xs"
				style="border: 1px solid var(--color-border); color: var(--color-muted)"
			>
				Clear conversation
			</button>
		{/if}
	</div>

	<!-- Chat messages area -->
	<div
		bind:this={chatContainer}
		class="flex-1 overflow-y-auto rounded border p-4"
		style="border-color: var(--color-border)"
	>
		{#if conversations.length === 0 && !asking && historyLoaded}
			<p class="text-sm" style="color: var(--color-muted)">No conversations yet. Ask a question below.</p>
		{/if}

		<div class="flex flex-col gap-4">
			{#each conversations as conv (conv.id)}
				<!-- User question -->
				<div class="flex justify-end">
					<div class="max-w-[80%] rounded-lg px-4 py-2 text-sm"
						style="background: var(--color-primary); color: white">
						{conv.question}
					</div>
				</div>
				<!-- AI answer -->
				<div class="flex justify-start">
					<div class="group max-w-[85%]">
						<div class="prose prose-sm max-w-none rounded-lg px-4 py-3 text-sm"
							style="background: var(--color-surface, #f5f5f5); color: var(--color-fg)">
							{@html renderMarkdown(conv.answer)}
						</div>
						<div class="mt-1 flex items-center gap-3">
							<div class="flex flex-wrap gap-2 text-xs" style="color: var(--color-muted)">
								<span>{conv.model_used}</span>
								{#if conv.duration_ms != null}
									<span>{formatDuration(conv.duration_ms)}</span>
								{/if}
							</div>
							<button
								onclick={() => copyToClipboard(conv.answer, conv.id)}
								class="rounded px-1.5 py-0.5 text-xs opacity-0 transition-opacity group-hover:opacity-100"
								style="color: var(--color-muted); border: 1px solid var(--color-border)"
								title="Copy to clipboard"
							>
								{copiedId === conv.id ? 'Copied!' : 'Copy'}
							</button>
						</div>
					</div>
				</div>
			{/each}

			<!-- Streaming in progress -->
			{#if asking}
				<!-- Show the question being asked -->
				<div class="flex justify-end">
					<div class="max-w-[80%] rounded-lg px-4 py-2 text-sm"
						style="background: var(--color-primary); color: white">
						{streamingQuestion}
					</div>
				</div>
				<!-- Streaming answer or thinking indicator -->
				<div class="flex justify-start">
					<div class="max-w-[85%] rounded-lg px-4 py-3 text-sm"
						style="background: var(--color-surface, #f5f5f5); color: var(--color-fg)">
						{#if streamingAnswer}
							<div class="prose prose-sm max-w-none">
								{@html renderMarkdown(streamingAnswer)}
							</div>
						{:else}
							<div class="flex items-center gap-2">
								<span class="thinking-dots" style="color: var(--color-muted)">
									<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
								</span>
								<span class="text-xs" style="color: var(--color-muted)">Thinking</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>

	{#if error}
		<div role="alert" class="mt-2 rounded border p-3 text-sm"
			style="border-color: var(--color-danger); color: var(--color-danger)">{error}</div>
	{/if}

	<!-- Input area -->
	<div class="mt-3 flex gap-2">
		<textarea
			id="qa-input"
			bind:value={question}
			onkeydown={handleKeydown}
			placeholder="Ask a question about this Set..."
			rows="2"
			maxlength="4000"
			disabled={asking}
			class="flex-1 rounded border px-3 py-2 text-sm disabled:opacity-50"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); resize: none"
		></textarea>
		<button
			onclick={ask}
			disabled={asking || !question.trim()}
			class="self-end rounded px-4 py-2 text-sm text-white disabled:opacity-50"
			style="background-color: var(--color-primary)"
		>
			{#if asking}
				<span class="inline-block animate-spin">↻</span>
			{:else}
				Send
			{/if}
		</button>
	</div>
</div>

<style>
	.thinking-dots .dot {
		animation: blink 1.4s infinite both;
		font-size: 1.5em;
		line-height: 1;
	}
	.thinking-dots .dot:nth-child(2) { animation-delay: 0.2s; }
	.thinking-dots .dot:nth-child(3) { animation-delay: 0.4s; }

	@keyframes blink {
		0%, 80%, 100% { opacity: 0; }
		40% { opacity: 1; }
	}

	/* Markdown styling inside chat bubbles */
	.prose :global(pre) {
		background: rgba(0, 0, 0, 0.05);
		border-radius: 4px;
		padding: 0.75em;
		overflow-x: auto;
		margin: 0.5em 0;
	}
	.prose :global(code) {
		font-size: 0.85em;
		padding: 0.15em 0.3em;
		border-radius: 3px;
		background: rgba(0, 0, 0, 0.05);
	}
	.prose :global(pre code) {
		padding: 0;
		background: none;
	}
	.prose :global(ul), .prose :global(ol) {
		padding-left: 1.5em;
		margin: 0.5em 0;
	}
	.prose :global(p) {
		margin: 0.4em 0;
	}
	.prose :global(p:first-child) {
		margin-top: 0;
	}
	.prose :global(p:last-child) {
		margin-bottom: 0;
	}
	.prose :global(blockquote) {
		border-left: 3px solid var(--color-border, #ddd);
		padding-left: 0.75em;
		margin: 0.5em 0;
		opacity: 0.85;
	}
	.prose :global(table) {
		border-collapse: collapse;
		margin: 0.5em 0;
		font-size: 0.9em;
	}
	.prose :global(th), .prose :global(td) {
		border: 1px solid var(--color-border, #ddd);
		padding: 0.3em 0.6em;
	}
</style>
