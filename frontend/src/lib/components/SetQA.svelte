<script lang="ts">
	import DOMPurify from 'dompurify';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { AIConversation, QAResponse } from '$lib/types/api';

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
	let isStreaming = $state(false);
	let historyLoaded = $state(false);

	$effect(() => {
		if (setId) loadHistory();
	});

	async function loadHistory() {
		try {
			const convs = await apiFetch<AIConversation[]>(`/api/ai/sets/${setId}/conversations?limit=20`);
			conversations = convs.map((c) => ({
				id: c.id,
				question: c.question,
				answer: c.answer,
				model_used: c.model_used,
				tokens_in: c.tokens_in,
				tokens_out: c.tokens_out,
				duration_ms: c.duration_ms,
				created_at: c.created_at,
			}));
			historyLoaded = true;
		} catch {
			// Non-fatal — just won't show history
			historyLoaded = true;
		}
	}

	async function ask() {
		const q = question.trim();
		if (!q || asking) return;
		question = '';
		error = null;
		asking = true;

		try {
			const result = await apiFetch<QAResponse>(`/api/ai/sets/${setId}/ask`, {
				method: 'POST',
				body: JSON.stringify({ question: q }),
			});

			conversations = [
				{
					id: result.conversation_id,
					question: q,
					answer: result.answer,
					model_used: result.model_used,
					tokens_in: result.tokens_in,
					tokens_out: result.tokens_out,
					duration_ms: result.duration_ms,
					created_at: new Date().toISOString(),
				},
				...conversations,
			];
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to get answer';
			question = q; // restore so user can retry
		}
		asking = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			ask();
		}
	}

	function formatDuration(ms: number | null): string {
		if (ms == null) return '';
		return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
	}

	function formatTokens(inp: number | null, out: number | null): string {
		if (inp == null && out == null) return '';
		return `${inp ?? '?'} in / ${out ?? '?'} out`;
	}

	// Safe HTML rendering of AI output (Protocol 7)
	function safeHtml(text: string): string {
		return DOMPurify.sanitize(text, { ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'blockquote'] });
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Question input -->
	<div class="flex flex-col gap-2">
		<label for="qa-input" class="text-sm font-medium" style="color: var(--color-fg)">
			Ask a question about this Set
		</label>
		<div class="flex gap-2">
			<textarea
				id="qa-input"
				bind:value={question}
				onkeydown={handleKeydown}
				placeholder="e.g. What are the main components and how do they relate?"
				rows="2"
				maxlength="4000"
				disabled={asking}
				class="flex-1 rounded border px-3 py-2 text-sm disabled:opacity-50"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); resize: vertical"
			></textarea>
			<button
				onclick={ask}
				disabled={asking || !question.trim()}
				class="self-end rounded px-4 py-2 text-sm text-white disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{asking ? 'Asking…' : 'Ask'}
			</button>
		</div>
		<p class="text-xs" style="color: var(--color-muted)">Press Enter to send, Shift+Enter for newline.</p>
	</div>

	{#if error}
		<div role="alert" class="rounded border p-3 text-sm"
			style="border-color: var(--color-danger); color: var(--color-danger)">{error}</div>
	{/if}

	{#if asking}
		<div class="rounded border p-4 text-sm" style="border-color: var(--color-border)">
			<p class="animate-pulse" style="color: var(--color-muted)">Thinking…</p>
		</div>
	{/if}

	<!-- Conversation history -->
	{#if conversations.length > 0}
		<div class="flex flex-col gap-3">
			{#each conversations as conv (conv.id)}
				<div class="rounded border p-4" style="border-color: var(--color-border)">
					<p class="mb-2 text-sm font-medium" style="color: var(--color-fg)">
						Q: {conv.question}
					</p>
					<div class="prose prose-sm max-w-none text-sm" style="color: var(--color-fg)">
						{@html safeHtml(conv.answer.replace(/\n/g, '<br>'))}
					</div>
					<div class="mt-2 flex flex-wrap gap-3 text-xs" style="color: var(--color-muted)">
						<span>{conv.model_used}</span>
						{#if conv.duration_ms != null}
							<span>{formatDuration(conv.duration_ms)}</span>
						{/if}
						{#if conv.tokens_in != null || conv.tokens_out != null}
							<span>{formatTokens(conv.tokens_in, conv.tokens_out)} tokens</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{:else if historyLoaded && !asking}
		<p class="text-sm" style="color: var(--color-muted)">No conversations yet. Ask a question above.</p>
	{/if}
</div>
