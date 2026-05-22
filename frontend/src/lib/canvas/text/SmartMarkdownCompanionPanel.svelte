<script lang="ts">
	/**
	 * SmartMarkdownCompanionPanel (SPEC-205-b, v6.30.0).
	 *
	 * Right-side panel rendered alongside the source textarea in
	 * SmartMarkdownCanvas edit mode. Two stacked sections:
	 *
	 *   1. Fill in the blanks — labeled input for every empty-override
	 *      token in the source. Filling it rewrites the source token
	 *      at the matched byte position from `=` to `=<value>`.
	 *   2. Tokens preview — the last-saved resolved markdown (data.content)
	 *      rendered in muted grey via MarkdownView.
	 *
	 * Closes the deferred fillable-slot UX from SPEC-210-a §5.1 (v6.18.0)
	 * + the C5 tip-text ask.
	 */

	import MarkdownView from '$lib/components/MarkdownView.svelte';
	import { apiFetch } from '$lib/utils/api';

	interface ElementSummary {
		name: string;
		attrNames: Set<string>;
	}

	interface FillableToken {
		start: number;
		end: number;
		elementId: string;
		/** e.g. "attributes/Quantity/type". */
		attrPath: string;
		/** humanised — e.g. "Quantity" */
		attrLabel: string;
		/** the user's typed value (in-progress) */
		value: string;
	}

	interface Props {
		source: string;
		content: string;
		canvasDirty: boolean;
		onsourcechange: (next: string) => void;
	}

	let { source, content, canvasDirty, onsourcechange }: Props = $props();

	// Regex captures fillable tokens — { { element : id : attr : path = } }
	// Captures: (1) element id, (2) attribute path (everything between
	// "attr:" and "="). Greedy attr-path match stops at `=` (the
	// fillable-slot marker). Multiple matches: re-extract on every
	// derived change.
	const FILLABLE_RE = /\{\{element:([^:}]+):attr:([^=}]+)=\}\}/g;

	let elementCache = $state<Map<string, ElementSummary | 'pending' | 'missing'>>(new Map());
	let typedValues = $state<Record<string, string>>({});

	// $derived: scan the source for fillable tokens. Re-runs on every
	// edit. Tokens are keyed by `${start}` so typed-but-unsaved values
	// persist as long as the matched start stays at the same byte
	// position (which it does until the user types in the textarea
	// itself, at which point we lose the in-progress value — acceptable
	// since the user is mid-edit on a different surface anyway).
	const fillableTokens = $derived.by((): FillableToken[] => {
		const out: FillableToken[] = [];
		if (!source) return out;
		FILLABLE_RE.lastIndex = 0;
		let m: RegExpExecArray | null;
		while ((m = FILLABLE_RE.exec(source)) !== null) {
			const start = m.index;
			const end = start + m[0].length;
			const elementId = m[1];
			const attrPath = m[2];
			const attrLabel = humaniseAttrPath(attrPath);
			const key = `${start}`;
			out.push({
				start, end, elementId, attrPath, attrLabel,
				value: typedValues[key] ?? '',
			});
		}
		return out;
	});

	const uniqueElementIds = $derived(
		Array.from(new Set(fillableTokens.map((t) => t.elementId))),
	);

	$effect(() => {
		// Lazy-fetch element data for any uncached id.
		for (const id of uniqueElementIds) {
			if (!elementCache.has(id)) {
				elementCache.set(id, 'pending');
				void fetchElement(id);
			}
		}
	});

	async function fetchElement(id: string) {
		try {
			const data = await apiFetch<{ name?: string; data?: { attributes?: { name?: string }[] } }>(
				`/api/elements/${encodeURIComponent(id)}`,
			);
			const name = typeof data.name === 'string' ? data.name : id;
			const attrNames = new Set<string>(
				(data.data?.attributes ?? [])
					.map((a) => a?.name)
					.filter((n): n is string => typeof n === 'string'),
			);
			const next = new Map(elementCache);
			next.set(id, { name, attrNames });
			elementCache = next;
		} catch {
			const next = new Map(elementCache);
			next.set(id, 'missing');
			elementCache = next;
		}
	}

	function humaniseAttrPath(attrPath: string): string {
		// "attributes/Quantity/type"   → "Quantity"
		// "attributes/Unit/notes"      → "Unit"
		// "name"                       → "name" (rare for fillable)
		const segs = attrPath.split('/').filter(Boolean);
		if (segs[0] === 'attributes' && segs.length >= 2) {
			return segs[1];
		}
		return attrPath;
	}

	function elementName(id: string): string {
		const cached = elementCache.get(id);
		if (cached && typeof cached === 'object') return cached.name;
		if (cached === 'missing') return '(deleted element)';
		return '…';
	}

	function previewForRow(token: FillableToken): string {
		// Build a small preview by substituting THIS row's value (live)
		// + a best-effort substitution of OTHER tokens on the same line.
		// We don't run the full resolver — just enough to give a useful
		// cue.
		const lineStart = source.lastIndexOf('\n', token.start - 1) + 1;
		const lineEnd = source.indexOf('\n', token.end);
		const line = source.slice(lineStart, lineEnd === -1 ? source.length : lineEnd);

		const cached = elementCache.get(token.elementId);
		const elName = cached && typeof cached === 'object' ? cached.name : '…';

		// Substitute THIS token (with typed value) and `:name` tokens.
		// Other token types (other attributes) are left as `…` placeholders.
		return line
			.replaceAll(
				new RegExp(`\\{\\{element:${escapeRegex(token.elementId)}:name\\}\\}`, 'g'),
				elName,
			)
			.replace(
				source.slice(token.start, token.end),
				token.value || '…',
			)
			// Other tokens → ellipsis
			.replaceAll(/\{\{element:[^}]+\}\}/g, '…');
	}

	function escapeRegex(s: string): string {
		return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function commitValue(token: FillableToken, raw: string) {
		const safe = raw.replace(/[\\}]/g, '').trim();
		typedValues = { ...typedValues, [String(token.start)]: safe };
		if (!safe) return; // empty → don't mutate source
		const before = source.substring(0, token.start);
		const after = source.substring(token.end);
		const newToken = source.substring(token.start, token.end).replace(/=\}\}$/, `=${safe}}}`);
		const nextSource = before + newToken + after;
		onsourcechange(nextSource);
	}
</script>

<div class="companion-panel">
	<section class="fill-section">
		<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Fill in the blanks</h3>
		{#if fillableTokens.length === 0}
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				No fillable slots in this diagram. Stamps you insert via the picker (Shift+Enter on an attribute) will appear here ready to fill.
			</p>
		{:else}
			<div class="mt-3 flex flex-col gap-3">
				{#each fillableTokens as t (`${t.start}-${t.attrPath}`)}
					<div class="rounded border p-2" style="border-color: var(--color-border); background: var(--color-surface)">
						<div class="text-xs" style="color: var(--color-muted)">
							<strong style="color: var(--color-fg)">{elementName(t.elementId)}</strong>
							— {t.attrLabel}
						</div>
						<input
							type="text"
							value={t.value}
							onblur={(e) => commitValue(t, (e.currentTarget as HTMLInputElement).value)}
							placeholder="value…"
							class="mt-1 w-full rounded border px-2 py-1 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
						<div class="mt-1 text-xs italic" style="color: var(--color-muted)">
							↳ {previewForRow(t)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<section class="preview-section">
		<div class="flex items-center justify-between">
			<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Tokens preview</h3>
			<small style="color: var(--color-muted); font-size: 11px">
				{canvasDirty ? '* unsaved — preview shows last save' : '↻ saved'}
			</small>
		</div>
		<div class="preview-muted mt-2 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
			<MarkdownView source={content ?? ''} />
		</div>
	</section>
</div>

<style>
	.companion-panel {
		display: flex;
		flex-direction: column;
		gap: 16px;
		padding: 12px 16px;
		max-height: 100%;
		overflow-y: auto;
	}
	.fill-section, .preview-section {
		min-width: 0;
	}
	.preview-muted {
		opacity: 0.85;
	}
	.preview-muted :global(*) {
		color: var(--color-muted) !important;
	}
</style>
