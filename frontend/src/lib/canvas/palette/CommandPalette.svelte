<script lang="ts">
	/**
	 * CommandPalette: searchable BPMN element picker (ADR-136 §UX).
	 *
	 * The single most-praised UX innovation in bpmn-js / Camunda Modeler.
	 * Bound to:
	 *   N — create-anything (drop on canvas at cursor)
	 *   A — append-anything (after the selected element)
	 *   R — replace (morph the selected element to a different type)
	 *
	 * Fuzzy match across the full BPMN catalogue plus per-entry keyboard
	 * hint and category badge. Arrow-key navigation, Enter to confirm,
	 * Escape to close.
	 */
	import { onMount, onDestroy } from 'svelte';
	import { BPMN_ENTITY_TYPES, type BpmnEntityType, type BpmnEntityTypeInfo } from '$lib/types/canvas';

	export type CommandMode = 'create' | 'append' | 'replace';

	interface Props {
		/** Mode the palette is in — set when opened via N/A/R. */
		mode: CommandMode;
		/** Open state — parent toggles this. */
		open: boolean;
		/** Result callback. */
		onpick?: (entry: BpmnEntityTypeInfo, mode: CommandMode) => void;
		/** Called when the palette wants to close (Esc, click-out, after pick). */
		onclose?: () => void;
		/** Document-level shortcut binding — pass false in tests / embedded use. */
		bindShortcuts?: boolean;
		/** Externally controlled mode-setter, used by the host's keyboard listener. */
		onmode?: (mode: CommandMode) => void;
	}

	let {
		mode = $bindable(),
		open = $bindable(),
		onpick,
		onclose,
		bindShortcuts = true,
		onmode,
	}: Props = $props();

	let query = $state('');
	let cursor = $state(0);
	let inputEl: HTMLInputElement | null = $state(null);

	const filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!q) return BPMN_ENTITY_TYPES;
		return BPMN_ENTITY_TYPES.filter(e =>
			e.label.toLowerCase().includes(q) ||
			e.key.toLowerCase().includes(q) ||
			e.description.toLowerCase().includes(q),
		);
	});

	$effect(() => {
		if (open) {
			query = '';
			cursor = 0;
			queueMicrotask(() => inputEl?.focus());
		}
	});

	function pick(entry: BpmnEntityTypeInfo) {
		onpick?.(entry, mode);
		onclose?.();
	}

	function onKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') { e.preventDefault(); onclose?.(); return; }
		if (e.key === 'ArrowDown') { e.preventDefault(); cursor = Math.min(filtered.length - 1, cursor + 1); }
		else if (e.key === 'ArrowUp') { e.preventDefault(); cursor = Math.max(0, cursor - 1); }
		else if (e.key === 'Enter')   { e.preventDefault(); const f = filtered[cursor]; if (f) pick(f); }
	}

	function onGlobalKey(e: KeyboardEvent) {
		// Avoid hijacking when the user is typing in an input outside the palette.
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		if (e.key === 'n' || e.key === 'N') { e.preventDefault(); mode = 'create';  onmode?.('create');  open = true; }
		else if (e.key === 'a' || e.key === 'A') { e.preventDefault(); mode = 'append';  onmode?.('append');  open = true; }
		else if (e.key === 'r' || e.key === 'R') { e.preventDefault(); mode = 'replace'; onmode?.('replace'); open = true; }
	}

	onMount(() => {
		if (bindShortcuts && typeof document !== 'undefined') {
			document.addEventListener('keydown', onGlobalKey);
		}
	});
	onDestroy(() => {
		if (bindShortcuts && typeof document !== 'undefined') {
			document.removeEventListener('keydown', onGlobalKey);
		}
	});

	const titleByMode: Record<CommandMode, string> = {
		create: 'Create',
		append: 'Append after selection',
		replace: 'Change element type',
	};
</script>

{#if open}
	<div
		class="bpmn-cmd-palette__backdrop"
		role="presentation"
		onclick={() => onclose?.()}
		onkeydown={(e) => { if (e.key === 'Escape') onclose?.(); }}
	></div>
	<div class="bpmn-cmd-palette" role="dialog" aria-label="BPMN command palette" onkeydown={onKey}>
		<header class="bpmn-cmd-palette__header">
			<span class="bpmn-cmd-palette__mode">{titleByMode[mode]}</span>
			<kbd class="bpmn-cmd-palette__kbd">
				{mode === 'create' ? 'N' : mode === 'append' ? 'A' : 'R'}
			</kbd>
		</header>
		<input
			type="text"
			class="bpmn-cmd-palette__input"
			placeholder="Type to filter…"
			bind:this={inputEl}
			bind:value={query}
			oninput={() => (cursor = 0)}
		/>
		<ul class="bpmn-cmd-palette__list" role="listbox">
			{#each filtered as entry, i (entry.key)}
				<li
					class="bpmn-cmd-palette__item"
					class:bpmn-cmd-palette__item--cursor={i === cursor}
					role="option"
					aria-selected={i === cursor}
					data-key={entry.key}
				>
					<button type="button" onclick={() => pick(entry)}>
						<span class="bpmn-cmd-palette__icon" aria-hidden="true">{entry.icon}</span>
						<span class="bpmn-cmd-palette__label">{entry.label}</span>
						<span class="bpmn-cmd-palette__cat">{entry.category}</span>
					</button>
				</li>
			{/each}
			{#if filtered.length === 0}
				<li class="bpmn-cmd-palette__empty">No matching elements.</li>
			{/if}
		</ul>
	</div>
{/if}

<style>
	.bpmn-cmd-palette__backdrop {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.18);
		z-index: 998;
	}
	.bpmn-cmd-palette {
		position: fixed; top: 20%; left: 50%;
		transform: translateX(-50%);
		width: 420px; max-height: 60vh;
		display: flex; flex-direction: column;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 8px;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
		z-index: 999;
	}
	.bpmn-cmd-palette__header {
		display: flex; justify-content: space-between; align-items: center;
		padding: 8px 12px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
	}
	.bpmn-cmd-palette__mode { font-weight: 600; color: var(--color-fg, #202931); }
	.bpmn-cmd-palette__kbd {
		font-family: monospace;
		background: var(--color-surface-hover, #f3f4f6);
		padding: 2px 6px;
		border-radius: 4px;
		border: 1px solid var(--color-border, #e5e7eb);
	}
	.bpmn-cmd-palette__input {
		padding: 8px 12px;
		border: 0;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		font-size: 14px;
		outline: none;
	}
	.bpmn-cmd-palette__list {
		list-style: none; margin: 0; padding: 0;
		overflow-y: auto;
	}
	.bpmn-cmd-palette__item button {
		display: grid; grid-template-columns: 24px 1fr auto;
		gap: 10px; align-items: center;
		width: 100%;
		padding: 8px 12px;
		background: transparent; border: 0;
		text-align: left; cursor: pointer;
		color: var(--color-fg, #202931);
		font-size: 13px;
	}
	.bpmn-cmd-palette__item--cursor button { background: var(--color-surface-hover, #f3f4f6); }
	.bpmn-cmd-palette__icon { font-size: 16px; }
	.bpmn-cmd-palette__cat {
		font-size: 11px; opacity: 0.6;
		text-transform: capitalize;
	}
	.bpmn-cmd-palette__empty {
		padding: 16px; text-align: center;
		color: var(--color-muted, #6b7280); font-size: 13px;
	}
</style>
