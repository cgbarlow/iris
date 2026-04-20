<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import { API_BASE_URL } from '$lib/config.js';
	import type { AIConversation } from '$lib/types/api';
	import { getActiveProviders, getProviderAvailability, type ActiveProvider } from '$lib/stores/aiProviders.svelte.js';
	import PackagePicker from '$lib/components/PackagePicker.svelte';

	interface Props {
		setIds: string[];
		collectionId?: string;
		packageIds?: string[];
		diagramIds?: string[];
		docrefDocIds?: string[];
		fileContexts?: { filename: string; text: string }[];
	}

	let { setIds, collectionId, packageIds, diagramIds, docrefDocIds, fileContexts }: Props = $props();

	// Primary set ID for backwards compatibility (history, diagram creation)
	const setId = $derived(setIds[0] || '');

	type ConvEntry = {
		id: string;
		question: string;
		answer: string;
		model_used: string;
		tokens_in: number | null;
		tokens_out: number | null;
		duration_ms: number | null;
		created_at: string;
		isCreation?: boolean;
	};

	// Creation mode state
	let creationMode = $state(false);
	let selectedNotation = $state('doview');
	let pendingDiagrams = $state<object | null>(null);
	let applyingDiagrams = $state(false);
	// Multi-turn creation conversation history
	let creationHistory = $state<{ role: string; content: string }[]>([]);

	let conversations = $state<ConvEntry[]>([]);
	let question = $state('');
	let asking = $state(false);
	let error = $state<string | null>(null);
	let streamingAnswer = $state('');
	let streamingQuestion = $state('');
	let historyLoaded = $state(false);
	let chatContainer: HTMLDivElement | undefined = $state();
	let qaInput: HTMLTextAreaElement | undefined = $state();
	let copiedId = $state<string | null>(null);
	let abortController: AbortController | null = null;
	let creationJsonBuffer = $state('');  // accumulates raw JSON in creation mode (hidden from UI)
	let askStartTime = $state(0);
	let elapsedSeconds = $state(0);
	let elapsedTimer: ReturnType<typeof setInterval> | null = null;
	let streamingTokensIn = $state<number | null>(null);
	let streamingTokensOut = $state<number | null>(null);
	let generatingDiagrams = $state(false);  // true when AI is outputting JSON
	let diagramsGenerated = $state(0);  // count of diagrams seen so far in the JSON stream
	let expectedDiagramCount = $state(0);  // estimated total from conversation
	let currentDiagramName = $state('');  // name of the diagram currently being generated
	let showLocationPicker = $state(false);  // show package picker before creating/generating diagrams
	let selectedPackageId = $state<string | null>(null);
	let locationChosen = $state(false);  // true once user has picked a location
	let pendingSendMessage = $state('');  // message waiting to be sent after location is chosen
	let showHistorySidebar = $state(false);
	let allHistory = $state<AIConversation[]>([]);
	let historyLoading = $state(false);
	let currentThreadId = $state(crypto.randomUUID());

	// Model selector (ADR-114) — providers & availability from global store
	function hostLabel(url: string | null): string {
		if (!url) return '';
		return url.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
	}
	let activeProviders = $derived(getActiveProviders());
	let selectedProviderId = $state('');
	let providerAvailability = $derived(getProviderAvailability());
	let providerDropdownOpen = $state(false);

	function isClearedSession(): boolean {
		return sessionStorage.getItem(`qa-cleared-${setId}`) === '1';
	}

	$effect(() => {
		if (setId && !isClearedSession()) loadHistory();
		else historyLoaded = true;
	});

	$effect(() => {
		// Auto-select default provider when providers load from global store
		if (activeProviders.length > 0 && !selectedProviderId) {
			const defaultProvider = activeProviders.find(p => p.is_default) ?? activeProviders[0];
			if (defaultProvider) selectedProviderId = defaultProvider.id;
		}
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

function promptForLocation() {
		showLocationPicker = true;
	}

	async function applyCreationDiagrams(packageId: string | null = null) {
		if (!pendingDiagrams || applyingDiagrams) return;
		showLocationPicker = false;
		applyingDiagrams = true;
		error = null;
		const diagramsToApply = pendingDiagrams;
		pendingDiagrams = null;  // Clear immediately to prevent duplicate prompts
		try {
			const body: Record<string, unknown> = { diagrams_json: JSON.stringify(diagramsToApply) };
			if (packageId) body.package_id = packageId;
			const result = await apiFetch<{ diagram_ids: string[]; primary_diagram_id: string | null }>(
				`/api/ai/sets/${setId}/create-diagram/apply`,
				{
					method: 'POST',
					body: JSON.stringify(body),
				}
			);
			if (result.primary_diagram_id) {
				goto(`/diagrams/${result.primary_diagram_id}`);
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create diagrams';
		}
		applyingDiagrams = false;
	}

	function parseTotalPagesFromStream(): number {
		// Parse "total_pages": N from the JSON stream (appears before the diagrams array)
		const match = creationJsonBuffer.match(/"total_pages"\s*:\s*(\d+)/);
		return match ? parseInt(match[1], 10) : 0;
	}

	function tryExtractDiagrams(text: string): object | null {
		// Try fenced code block first (```json ... ``` or ``` ... ```)
		const fenced = text.match(/```(?:json)?\s*(\{[\s\S]*?"diagrams"[\s\S]*?\})\s*```/);
		const candidates = fenced ? [fenced[1]] : [];
		// Also try bare JSON object
		const bare = text.match(/\{[\s\S]*?"diagrams"[\s\S]*\}/);
		if (bare) candidates.push(bare[0]);

		for (const candidate of candidates) {
			try {
				const parsed = JSON.parse(candidate);
				if (parsed && Array.isArray(parsed.diagrams) && parsed.diagrams.length > 0) return parsed;
			} catch {
				// keep trying
			}
		}
		return null;
	}

	function isAwaitingGenerationConfirm(): boolean {
		// Check if the last AI message is asking the user to confirm before generating.
		// Matches common confirmation phrases the AI might use.
		if (creationHistory.length === 0) return false;
		const lastAssistant = [...creationHistory].reverse().find(m => m.role === 'assistant');
		if (!lastAssistant) return false;
		const text = lastAssistant.content.toLowerCase();
		return text.includes("generate the diagram") || text.includes("i'll generate")
			|| text.includes("generate the json") || text.includes("shall i")
			|| text.includes("ready to generate") || text.includes("proceed with")
			|| text.includes("go ahead") || text.includes("create the diagram")
			|| text.includes("let me know") || text.includes("want me to");
	}

	function stopStreaming() {
		if (abortController) {
			abortController.abort();
			abortController = null;
		}
	}

	async function ask() {
		const q = question.trim();
		if (!q || asking) return;

		// In creation mode, if the AI is ready to generate and user hasn't picked a location yet,
		// show the location picker first before sending the confirmation.
		if (creationMode && !locationChosen && isAwaitingGenerationConfirm()) {
			pendingSendMessage = q;
			question = '';
			showLocationPicker = true;
			return;
		}

		streamingQuestion = q;
		question = '';
		error = null;
		asking = true;
		streamingAnswer = '';
		streamingTokensIn = null;
		streamingTokensOut = null;
		pendingDiagrams = null;
		abortController = new AbortController();
		askStartTime = Date.now();
		elapsedSeconds = 0;
		elapsedTimer = setInterval(() => { elapsedSeconds = Math.floor((Date.now() - askStartTime) / 1000); }, 100);

		setTimeout(scrollToBottom, 50);

		try {
			const token = getAccessToken();
			const resp = await fetch(`${API_BASE_URL}/api/ai/ask?stream=true`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
				body: JSON.stringify(creationMode
					? { set_ids: setIds, collection_id: collectionId || null, package_ids: packageIds || null, diagram_ids: diagramIds?.length ? diagramIds : null, docref_doc_ids: docrefDocIds?.length ? docrefDocIds : null, file_contexts: fileContexts?.length ? fileContexts : null, question: q, provider_id: selectedProviderId || undefined, mode: 'creation', notation: selectedNotation, history: creationHistory, thread_id: currentThreadId }
					: { set_ids: setIds, collection_id: collectionId || null, package_ids: packageIds || null, diagram_ids: diagramIds?.length ? diagramIds : null, docref_doc_ids: docrefDocIds?.length ? docrefDocIds : null, file_contexts: fileContexts?.length ? fileContexts : null, question: q, provider_id: selectedProviderId || undefined, thread_id: currentThreadId }
				),
				signal: abortController.signal,
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
							if (creationMode && generatingDiagrams) {
								// Already in JSON generation — accumulate silently
								creationJsonBuffer += payload.chunk;
								// Parse total_pages from stream (appears before diagrams array)
								if (expectedDiagramCount === 0) {
									expectedDiagramCount = parseTotalPagesFromStream();
								}
								// Track diagram progress by counting "diagram_type" occurrences
								const count = (creationJsonBuffer.match(/"diagram_type"/g) || []).length;
								if (count > diagramsGenerated) {
									diagramsGenerated = count;
									// Extract the latest diagram name
									const nameMatches = [...creationJsonBuffer.matchAll(/"name"\s*:\s*"([^"]+)"/g)];
									if (nameMatches.length > 0) {
										currentDiagramName = nameMatches[nameMatches.length - 1][1];
									}
								}
							} else if (creationMode && !generatingDiagrams) {
								// Check if JSON output is starting
								const combined = streamingAnswer + payload.chunk;
								const trimmed = combined.trimStart();
								if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
									// JSON generation has begun — switch to silent mode
									generatingDiagrams = true;
									creationJsonBuffer = combined;
									diagramsGenerated = 0;
									expectedDiagramCount = 0; // will be parsed from stream
									currentDiagramName = '';
									streamingAnswer = '';
								} else {
									streamingAnswer += payload.chunk;
								}
							} else {
								streamingAnswer += payload.chunk;
							}
							scrollToBottom();
						} else if (payload.done) {
							streamingTokensIn = payload.tokens_in ?? null;
							streamingTokensOut = payload.tokens_out ?? null;
							// In creation mode, auto-apply the generated diagrams
							let displayAnswer = streamingAnswer;
							if (creationMode) {
								const fullAnswer = generatingDiagrams ? creationJsonBuffer : streamingAnswer;
								creationHistory = [
									...creationHistory,
									{ role: 'user', content: q },
									{ role: 'assistant', content: fullAnswer },
								];
								const extracted = tryExtractDiagrams(fullAnswer);
								if (extracted) {
									pendingDiagrams = extracted;
									displayAnswer = 'Diagrams generated — creating…';
								} else if (generatingDiagrams) {
									// JSON generation happened but extraction failed
									displayAnswer = 'Generation complete but could not parse diagram data.';
									error = 'Failed to parse AI diagram output. Try again.';
								}
								generatingDiagrams = false;
								creationJsonBuffer = '';
							}
							conversations = [
								...conversations,
								{
									id: payload.conversation_id,
									question: q,
									answer: displayAnswer,
									model_used: payload.model_used,
									tokens_in: payload.tokens_in ?? null,
									tokens_out: payload.tokens_out ?? null,
									duration_ms: payload.duration_ms,
									created_at: new Date().toISOString(),
									isCreation: creationMode,
								},
							];
							streamingAnswer = '';
							streamingQuestion = '';
							scrollToBottom();

							// Auto-apply only if user already chose a location;
							// otherwise the "Diagrams ready — where?" prompt will show.
							if (pendingDiagrams && locationChosen) {
								await applyCreationDiagrams(selectedPackageId);
							}
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
			if (e instanceof DOMException && e.name === 'AbortError') {
				// User stopped the stream — keep partial answer
				if (streamingAnswer) {
					conversations = [
						...conversations,
						{
							id: crypto.randomUUID(),
							question: q,
							answer: streamingAnswer + '\n\n*(stopped)*',
							model_used: '',
							tokens_in: null,
							tokens_out: null,
							duration_ms: null,
							created_at: new Date().toISOString(),
							isCreation: creationMode,
						},
					];
				}
				streamingAnswer = '';
				streamingQuestion = '';
			} else {
				error = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Failed to get answer';
				question = q;
				streamingAnswer = '';
				streamingQuestion = '';
			}
		}
		abortController = null;
		if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
		asking = false;
		setTimeout(() => qaInput?.focus(), 50);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			ask();
		}
	}

	type HistoryThread = {
		thread_id: string;
		mode: string;
		set_name: string | null;
		first_question: string;
		message_count: number;
		created_at: string;
		messages: AIConversation[];
	};

	let groupedHistory = $state<HistoryThread[]>([]);

	async function loadFullHistory() {
		historyLoading = true;
		try {
			allHistory = await apiFetch<AIConversation[]>(`/api/ai/sets/${setId}/conversations?limit=200`);
			// Group by thread_id
			const threadMap = new Map<string, AIConversation[]>();
			for (const conv of allHistory) {
				const tid = conv.thread_id || conv.id;
				if (!threadMap.has(tid)) threadMap.set(tid, []);
				threadMap.get(tid)!.push(conv);
			}
			groupedHistory = [...threadMap.entries()].map(([tid, msgs]) => {
				// Messages are newest-first from API, reverse for chronological
				const sorted = [...msgs].sort((a, b) => a.created_at.localeCompare(b.created_at));
				return {
					thread_id: tid,
					mode: sorted[0].mode || 'discuss',
					set_name: sorted[0].set_name,
					first_question: sorted[0].question,
					message_count: sorted.length,
					created_at: sorted[0].created_at,
					messages: sorted,
				};
			}).sort((a, b) => b.created_at.localeCompare(a.created_at)); // newest threads first
		} catch {
			allHistory = [];
			groupedHistory = [];
		}
		historyLoading = false;
	}

	function toggleHistorySidebar() {
		showHistorySidebar = !showHistorySidebar;
		if (showHistorySidebar) loadFullHistory();
	}

	function loadFromHistory(thread: HistoryThread) {
		const isCreation = thread.mode === 'creation';
		creationMode = isCreation;
		pendingDiagrams = null;
		locationChosen = false;
		selectedPackageId = null;
		currentThreadId = thread.thread_id;

		// Populate all messages from the thread into the chat
		conversations = thread.messages.map(conv => ({
			id: conv.id,
			question: conv.question,
			answer: conv.answer,
			model_used: conv.model_used,
			tokens_in: conv.tokens_in,
			tokens_out: conv.tokens_out,
			duration_ms: conv.duration_ms,
			created_at: conv.created_at,
			isCreation: isCreation,
		}));

		// Seed creation history with all messages so AI has full context
		creationHistory = isCreation
			? thread.messages.flatMap(c => [
				{ role: 'user', content: c.question },
				{ role: 'assistant', content: c.answer },
			])
			: [];

		sessionStorage.removeItem(`qa-cleared-${setId}`);
		showHistorySidebar = false;
		setTimeout(scrollToBottom, 50);
	}

	function formatHistoryDate(iso: string): string {
		const d = new Date(iso);
		if (isNaN(d.getTime())) return iso;
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		const diffHours = Math.floor(diffMins / 60);
		if (diffHours < 24) return `${diffHours}h ago`;
		const diffDays = Math.floor(diffHours / 24);
		if (diffDays < 7) return `${diffDays}d ago`;
		return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
	}

	function clearConversation() {
		conversations = [];
		creationHistory = [];
		streamingAnswer = '';
		streamingQuestion = '';
		question = '';
		error = null;
		pendingDiagrams = null;
		generatingDiagrams = false;
		creationJsonBuffer = '';
		locationChosen = false;
		selectedPackageId = null;
		pendingSendMessage = '';
		currentThreadId = crypto.randomUUID();
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
	<!-- Header with mode toggle, clear, and history buttons -->
	<div class="mb-3 flex items-center justify-between gap-2 flex-wrap">
		<div class="flex items-center gap-2">
			<button
				onclick={() => { creationMode = false; pendingDiagrams = null; creationHistory = []; locationChosen = false; selectedPackageId = null; }}
				class="rounded px-3 py-1.5 text-sm"
				style={!creationMode
					? 'background: var(--color-primary); color: white; border: 1px solid var(--color-primary)'
					: 'border: 1px solid var(--color-border); color: var(--color-fg)'}
			>
				Discuss
			</button>
			<button
				onclick={() => {
					creationMode = true;
					pendingDiagrams = null;
					locationChosen = false;
					selectedPackageId = null;
					creationHistory = conversations.flatMap(c => [
						{ role: 'user' as const, content: c.question },
						{ role: 'assistant' as const, content: c.answer },
					]);
				}}
				class="rounded px-3 py-1.5 text-sm"
				style={creationMode
					? 'background: var(--color-primary); color: white; border: 1px solid var(--color-primary)'
					: 'border: 1px solid var(--color-border); color: var(--color-fg)'}
			>
				Create Diagram
			</button>
			{#if creationMode}
				<select
					bind:value={selectedNotation}
					class="rounded border px-2 py-1.5 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					<option value="doview">DoView</option>
				</select>
			{/if}
			{#if conversations.length > 0}
				<button
					onclick={clearConversation}
					class="rounded px-3 py-1.5 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-muted)"
				>
					Clear
				</button>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			{#if activeProviders.length > 0 && selectedProviderId}
				{@const selectedProvider = activeProviders.find(p => p.id === selectedProviderId)}
				<div class="provider-dropdown">
					<button
						type="button"
						class="provider-dropdown-trigger rounded border px-2 py-1 text-xs"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
						onclick={() => { providerDropdownOpen = !providerDropdownOpen; }}
					>
						<span class="provider-status-dot {Object.hasOwn(providerAvailability, selectedProviderId) ? (providerAvailability[selectedProviderId] ? 'available' : 'unavailable') : 'pending'}"></span>
						<span>{selectedProvider?.is_default ? '★ ' : ''}{selectedProvider?.name}{selectedProvider?.base_url ? ` (${hostLabel(selectedProvider.base_url)})` : ''}</span>
						<span class="provider-dropdown-arrow">▾</span>
					</button>
					{#if providerDropdownOpen}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div class="provider-dropdown-backdrop" onclick={() => { providerDropdownOpen = false; }} onkeydown={() => {}}></div>
						<ul class="provider-dropdown-menu rounded border" style="border-color: var(--color-border); background: var(--color-surface);">
							{#each activeProviders as p}
								{@const pinged = Object.hasOwn(providerAvailability, p.id)}
								{@const available = !!providerAvailability[p.id]}
								<li>
									<button
										type="button"
										class="provider-dropdown-item text-xs"
										style="color: var(--color-fg){p.is_default ? '; font-weight: bold' : ''}"
										disabled={pinged && !available}
										onclick={() => { selectedProviderId = p.id; providerDropdownOpen = false; }}
									>
										<span class="provider-status-dot {pinged ? (available ? 'available' : 'unavailable') : 'pending'}"></span>
										<span>{p.is_default ? '★ ' : ''}{p.name}{p.base_url ? ` (${hostLabel(p.base_url)})` : ''}</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
			<button
				onclick={toggleHistorySidebar}
				class="rounded px-3 py-1.5 text-sm flex items-center gap-1.5"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
				aria-pressed={showHistorySidebar}
			>
				History
			</button>
		</div>
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
								{#if conv.tokens_in != null || conv.tokens_out != null}
									<span>{(conv.tokens_in ?? 0) + (conv.tokens_out ?? 0)} tokens</span>
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
						{#if generatingDiagrams}
							<div class="flex flex-col gap-2 min-w-[220px]">
								<div class="flex items-center gap-2">
									<svg width="16" height="16" viewBox="0 0 16 16" fill="none" class="spinner-icon">
										<circle cx="8" cy="8" r="6" stroke="var(--color-primary)" stroke-width="2" stroke-dasharray="28" stroke-dashoffset="8" stroke-linecap="round"/>
									</svg>
									<span class="text-sm font-medium" style="color: var(--color-fg)">
										{#if diagramsGenerated > 0}
											Building page {diagramsGenerated}{expectedDiagramCount > 0 ? ` of ${expectedDiagramCount}` : ''}…
										{:else}
											Starting generation…
										{/if}
									</span>
								</div>
								{#if currentDiagramName}
									<span class="text-xs" style="color: var(--color-muted)">{currentDiagramName}</span>
								{/if}
								{#if diagramsGenerated > 0}
									{@const total = expectedDiagramCount || diagramsGenerated + 1}
									<div class="flex gap-1">
										{#each Array(total) as _, i}
											{#if i < diagramsGenerated}
												<div class="rounded-sm" style="width: 24px; height: 6px; background: var(--color-primary)"></div>
											{:else if i === diagramsGenerated}
												<div class="rounded-sm generating-next" style="width: 24px; height: 6px; background: var(--color-primary); opacity: 0.3"></div>
											{:else}
												<div class="rounded-sm" style="width: 24px; height: 6px; background: var(--color-border)"></div>
											{/if}
										{/each}
									</div>
								{:else}
									<div class="overflow-hidden rounded-full" style="height: 4px; background: var(--color-border)">
										<div class="generating-bar rounded-full" style="height: 100%; background: var(--color-primary)"></div>
									</div>
								{/if}
							</div>
						{:else if streamingAnswer}
							<div class="prose prose-sm max-w-none">
								{@html renderMarkdown(streamingAnswer)}
							</div>
						{:else}
							<div class="thinking-row">
								<span class="thinking-brain">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="16" height="16" aria-hidden="true">
										<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
									</svg>
								</span>
								<span class="thinking-label">Thinking...</span>
								<span class="thinking-stats">{elapsedSeconds}s</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>

	{#if pendingDiagrams}
		<div class="mt-2 flex items-center gap-3 rounded border p-3"
			style="border-color: var(--color-primary); background: var(--color-surface, #f5f5f5)">
			<p class="flex-1 text-sm" style="color: var(--color-fg)">
				{applyingDiagrams ? 'Creating diagrams…' : 'Diagrams ready. Where should they be created?'}
			</p>
			{#if !applyingDiagrams}
				<button
					onclick={() => applyCreationDiagrams(null)}
					class="rounded px-3 py-1.5 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Set Root
				</button>
				<button
					onclick={promptForLocation}
					class="rounded px-3 py-1.5 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Choose Package
				</button>
			{/if}
		</div>
	{/if}

	<PackagePicker
		open={showLocationPicker}
		title="Select location for diagrams"
		subtitle="Click a package to select it, then click OK. Or create a new package."
		setId={setId}
		onselect={(pkg) => {
			selectedPackageId = pkg.id;
			locationChosen = true;
			showLocationPicker = false;
			if (pendingSendMessage) {
				// Resume sending the confirmation message now that location is chosen
				question = pendingSendMessage;
				pendingSendMessage = '';
				ask();
			} else if (pendingDiagrams) {
				applyCreationDiagrams(pkg.id);
			}
		}}
		oncancel={() => {
			selectedPackageId = null;
			locationChosen = true;
			showLocationPicker = false;
			if (pendingSendMessage) {
				// User chose set root (cancelled picker) — resume sending
				question = pendingSendMessage;
				pendingSendMessage = '';
				ask();
			}
		}}
	/>

	{#if error}
		<div role="alert" class="mt-2 rounded border p-3 text-sm"
			style="border-color: var(--color-danger); color: var(--color-danger)">{error}</div>
	{/if}

	<!-- Input area -->
	<div class="mt-3 flex gap-2">
		<textarea
			id="qa-input"
			bind:this={qaInput}
			bind:value={question}
			onkeydown={handleKeydown}
			placeholder={creationMode ? `Describe what you'd like a ${selectedNotation === 'doview' ? 'DoView' : selectedNotation} diagram of...` : 'Ask a question...'}
			rows="2"
			maxlength="4000"
			disabled={asking}
			class="flex-1 rounded border px-3 py-2 text-sm disabled:opacity-50"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); resize: none"
		></textarea>
		{#if asking}
			<button
				onclick={stopStreaming}
				class="self-end rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
				title="Stop generating"
			>
				Stop
			</button>
		{:else}
			<button
				onclick={ask}
				disabled={!question.trim()}
				class="self-end rounded px-4 py-2 text-sm text-white disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				Send
			</button>
		{/if}
	</div>
</div>

<!-- History sidebar (reuses right-sidebar pattern from diagram comments panel) -->
{#if showHistorySidebar}
	<div
		style="position: fixed; top: 0; right: 0; bottom: 0; width: 316px; z-index: 40; overflow-y: auto; background: var(--color-bg); border-left: 1px solid var(--color-border);"
	>
		<div class="p-4">
			<div class="flex items-center justify-between mb-3">
				<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Conversation History</h3>
				<button
					onclick={() => { showHistorySidebar = false; }}
					class="rounded p-1 text-xs"
					style="color: var(--color-muted)"
					aria-label="Close history"
				>✕</button>
			</div>
			{#if historyLoading}
				<p class="text-sm" style="color: var(--color-muted)">Loading…</p>
			{:else if groupedHistory.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No conversation history.</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each groupedHistory as thread (thread.thread_id)}
						<button
							onclick={() => loadFromHistory(thread)}
							class="w-full rounded border p-3 text-left transition-colors"
							style="border-color: {currentThreadId === thread.thread_id ? 'var(--color-primary)' : 'var(--color-border)'}; background: transparent"
							title="Click to load this conversation ({thread.message_count} messages)"
						>
							<div class="flex items-center gap-2 mb-1">
								<span class="rounded-full px-2 py-0.5 text-xs font-medium"
									style={thread.mode === 'creation'
										? 'background: var(--color-primary); color: white'
										: 'background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)'}
								>{thread.mode === 'creation' ? 'Create' : 'Discuss'}</span>
								<span class="text-xs" style="color: var(--color-muted)">{formatHistoryDate(thread.created_at)}</span>
								<span class="text-xs" style="color: var(--color-muted)">{thread.message_count} msg{thread.message_count !== 1 ? 's' : ''}</span>
							</div>
							{#if thread.set_name}
								<p class="text-xs mb-1" style="color: var(--color-muted)">{thread.set_name}</p>
							{/if}
							<p class="text-xs font-medium" style="color: var(--color-fg)">{thread.first_question}</p>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.provider-dropdown {
		position: relative;
	}
	.provider-dropdown-trigger {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
	}
	.provider-dropdown-arrow {
		font-size: 0.7em;
		opacity: 0.6;
	}
	.provider-dropdown-backdrop {
		position: fixed;
		inset: 0;
		z-index: 49;
	}
	.provider-dropdown-menu {
		position: absolute;
		right: 0;
		top: calc(100% + 4px);
		z-index: 50;
		list-style: none;
		margin: 0;
		padding: 4px 0;
		min-width: 100%;
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0,0,0,0.15);
	}
	.provider-dropdown-item {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: 5px 10px;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
	}
	.provider-dropdown-item:hover:not(:disabled) {
		background-color: var(--color-bg);
	}
	.provider-dropdown-item:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.provider-status-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.provider-status-dot.available {
		background-color: #22c55e;
	}
	.provider-status-dot.unavailable {
		background-color: #ef4444;
	}
	.provider-status-dot.pending {
		background-color: var(--color-muted);
		animation: pulse-dot 1.5s ease-in-out infinite;
	}
	@keyframes pulse-dot {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 1; }
	}

	.spinner-icon {
		animation: spin 2s linear infinite;
		flex-shrink: 0;
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.generating-bar {
		animation: indeterminate 1.5s ease-in-out infinite;
		width: 40%;
	}

	@keyframes indeterminate {
		0% { transform: translateX(-100%); }
		100% { transform: translateX(350%); }
	}

	.generating-next {
		animation: pulse-next 1s ease-in-out infinite;
	}

	@keyframes pulse-next {
		0%, 100% { opacity: 0.15; }
		50% { opacity: 0.4; }
	}

	.thinking-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.thinking-label, .thinking-stats {
		font-size: 0.75rem;
		line-height: 1;
		color: var(--color-muted);
	}
	.thinking-stats {
		font-variant-numeric: tabular-nums;
		opacity: 0.7;
	}

	.thinking-brain {
		display: inline-flex;
		align-items: center;
		color: var(--color-primary, #3b82f6);
		animation: brain-pulse 2s ease-in-out infinite;
	}
	/* Functional loading indicator — exempt from reduced-motion blanket reset.
	   Scoped selector specificity (0,2,0) beats global * (0,0,0) even with !important. */
	@media (prefers-reduced-motion: reduce) {
		.thinking-brain {
			animation-duration: 2s !important;
			animation-iteration-count: infinite !important;
		}
	}
	@keyframes brain-pulse {
		0%, 100% {
			opacity: 0.4;
			transform: scale(1);
			filter: drop-shadow(0 0 0px #3b82f6);
		}
		50% {
			opacity: 1;
			transform: scale(1.15);
			filter: drop-shadow(0 0 8px #3b82f6);
		}
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
