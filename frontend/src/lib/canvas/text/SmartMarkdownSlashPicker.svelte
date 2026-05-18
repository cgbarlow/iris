<script lang="ts">
	/**
	 * SmartMarkdownSlashPicker (ADR-205, issue #185).
	 *
	 * Two-step popover invoked by SmartMarkdownCanvas when the user types
	 * "/" at a token boundary.
	 *
	 * Step 1 — Entity: typeahead across element/package/diagram/set/
	 * collection via `/api/search/entities`. Up/Down to scroll, Enter to
	 * select. Empty query (just typed "/") shows no results until the
	 * user types at least one character.
	 *
	 * Step 2 — Field: for non-elements, `name` + `description`. For
	 * elements, those plus every key from
	 * `/api/elements/{id}/attribute-keys` as `attr:<key>`.
	 *
	 * On confirm, emits `oninsert(token)` with a well-formed
	 * `{{<type>:<id>:<field-spec>}}` string. Esc emits `onclose`.
	 */
	import { apiFetch } from '$lib/utils/api';
	import { onMount } from 'svelte';

	interface EntitySearchResult {
		id: string;
		entity_type: 'element' | 'package' | 'diagram' | 'set' | 'collection';
		name: string;
	}

	interface Props {
		oninsert: (token: string) => void;
		onclose: () => void;
	}

	let { oninsert, onclose }: Props = $props();

	type Step = 'entity' | 'field';
	let step = $state<Step>('entity');

	// Entity step
	let query = $state('');
	let results = $state<EntitySearchResult[]>([]);
	let entityIdx = $state(0);
	let searchDebounce: ReturnType<typeof setTimeout> | undefined;
	let searchSeq = 0;

	// Field step
	let chosenEntity = $state<EntitySearchResult | null>(null);
	let fieldOptions = $state<string[]>([]);
	let fieldIdx = $state(0);

	const UNIVERSAL_FIELDS = ['name', 'description'];

	let inputEl = $state<HTMLInputElement | undefined>(undefined);

	onMount(() => {
		inputEl?.focus();
	});

	function scheduleSearch() {
		clearTimeout(searchDebounce);
		searchDebounce = setTimeout(runSearch, 150);
	}

	async function runSearch() {
		const q = query.trim();
		if (!q) {
			results = [];
			entityIdx = 0;
			return;
		}
		const mySeq = ++searchSeq;
		try {
			const rows = await apiFetch<EntitySearchResult[]>(
				`/api/search/entities?q=${encodeURIComponent(q)}&limit=25`,
			);
			if (mySeq !== searchSeq) return;
			results = rows;
			entityIdx = 0;
		} catch {
			if (mySeq !== searchSeq) return;
			results = [];
		}
	}

	async function selectEntity(r: EntitySearchResult) {
		chosenEntity = r;
		if (r.entity_type === 'element') {
			try {
				const keys = await apiFetch<string[]>(
					`/api/elements/${encodeURIComponent(r.id)}/attribute-keys`,
				);
				fieldOptions = [...UNIVERSAL_FIELDS, ...keys.map((k) => `attr:${k}`)];
			} catch {
				fieldOptions = [...UNIVERSAL_FIELDS];
			}
		} else {
			fieldOptions = [...UNIVERSAL_FIELDS];
		}
		fieldIdx = 0;
		step = 'field';
	}

	function selectField(field: string) {
		if (!chosenEntity) return;
		const token = `{{${chosenEntity.entity_type}:${chosenEntity.id}:${field}}}`;
		oninsert(token);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose();
			return;
		}
		if (step === 'entity') {
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				if (results.length > 0) entityIdx = (entityIdx + 1) % results.length;
				return;
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				if (results.length > 0) entityIdx = (entityIdx - 1 + results.length) % results.length;
				return;
			}
			if (e.key === 'Enter' && results.length > 0) {
				e.preventDefault();
				selectEntity(results[entityIdx]);
			}
			return;
		}
		// step === 'field'
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (fieldOptions.length > 0) fieldIdx = (fieldIdx + 1) % fieldOptions.length;
			return;
		}
		if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (fieldOptions.length > 0) fieldIdx = (fieldIdx - 1 + fieldOptions.length) % fieldOptions.length;
			return;
		}
		if (e.key === 'Enter' && fieldOptions.length > 0) {
			e.preventDefault();
			selectField(fieldOptions[fieldIdx]);
		}
	}
</script>

<div
	class="slash-picker"
	role="dialog"
	aria-label="Insert reference"
	onkeydown={handleKeydown}
	tabindex="-1"
>
	{#if step === 'entity'}
		<div class="slash-picker__header">Insert reference</div>
		<input
			bind:this={inputEl}
			type="text"
			class="slash-picker__input"
			placeholder="Search entities…"
			bind:value={query}
			oninput={scheduleSearch}
		/>
		<ul class="slash-picker__list" role="listbox" aria-label="Entities">
			{#each results as r, i (r.id)}
				<li
					role="option"
					aria-selected={i === entityIdx}
					class="slash-picker__item"
					class:active={i === entityIdx}
					onclick={() => selectEntity(r)}
					onkeydown={(e) => { if (e.key === 'Enter') selectEntity(r); }}
					tabindex="-1"
				>
					<span class="slash-picker__badge slash-picker__badge--{r.entity_type}">{r.entity_type}</span>
					<span class="slash-picker__name">{r.name}</span>
				</li>
			{/each}
			{#if results.length === 0 && query.trim()}
				<li class="slash-picker__empty">No matches.</li>
			{/if}
		</ul>
	{:else}
		<div class="slash-picker__header">
			Field for <strong>{chosenEntity?.name}</strong>
			<button class="slash-picker__back" onclick={() => { step = 'entity'; inputEl?.focus(); }}>Back</button>
		</div>
		<ul class="slash-picker__list" role="listbox" aria-label="Fields">
			{#each fieldOptions as field, i (field)}
				<li
					role="option"
					aria-selected={i === fieldIdx}
					class="slash-picker__item"
					class:active={i === fieldIdx}
					onclick={() => selectField(field)}
					onkeydown={(e) => { if (e.key === 'Enter') selectField(field); }}
					tabindex="-1"
				>
					<span class="slash-picker__field">{field}</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.slash-picker {
		position: absolute;
		top: 56px; left: 16px;
		width: 320px;
		max-height: 320px;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 6px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
		display: flex; flex-direction: column;
		z-index: 50;
		outline: none;
	}
	.slash-picker__header {
		display: flex; justify-content: space-between; align-items: center;
		padding: 8px 12px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
		color: var(--color-muted, #6b7280);
	}
	.slash-picker__back {
		background: transparent;
		border: 0;
		color: var(--color-primary, #2563eb);
		font-size: 12px;
		cursor: pointer;
	}
	.slash-picker__input {
		margin: 8px 12px;
		padding: 6px 8px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 13px;
		outline: none;
		background: var(--color-bg, #ffffff);
		color: var(--color-fg, #111827);
	}
	.slash-picker__list {
		list-style: none;
		margin: 0; padding: 4px 0;
		overflow-y: auto;
		flex: 1;
	}
	.slash-picker__item {
		display: flex; align-items: center; gap: 8px;
		padding: 6px 12px;
		cursor: pointer;
		font-size: 13px;
		color: var(--color-fg, #111827);
	}
	.slash-picker__item.active,
	.slash-picker__item:hover {
		background: var(--color-hover, #f3f4f6);
	}
	.slash-picker__empty {
		padding: 8px 12px;
		color: var(--color-muted, #9ca3af);
		font-size: 12px;
		font-style: italic;
	}
	.slash-picker__badge {
		display: inline-block;
		padding: 1px 6px;
		border-radius: 10px;
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		background: var(--color-muted-bg, #e5e7eb);
		color: var(--color-muted, #4b5563);
	}
	.slash-picker__badge--element { background: #dbeafe; color: #1e3a8a; }
	.slash-picker__badge--package { background: #fef3c7; color: #92400e; }
	.slash-picker__badge--diagram { background: #fce7f3; color: #831843; }
	.slash-picker__badge--set { background: #dcfce7; color: #14532d; }
	.slash-picker__badge--collection { background: #f3e8ff; color: #581c87; }
	.slash-picker__name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.slash-picker__field {
		font-family: ui-monospace, monospace;
		font-size: 12px;
	}
</style>
