<script lang="ts">
	/**
	 * EventMatrixPicker: 2D grid for picking BPMN event variants (ADR-136 §UX).
	 *
	 * BPMN events ARE a 2D matrix: trigger × position. Other tools either
	 * flat-list every variant in the palette (~50 entries, unscannable) or
	 * hide them inside a wrench menu (low discoverability). The matrix
	 * picker is Iris's strong opinion — present the dimensionality directly.
	 *
	 * Output: a tuple { entityType, eventTrigger, eventDirection?, boundaryInterrupting? }
	 * that the parent applies as the new node's data.
	 */
	import type { BpmnEntityType, BpmnEventTrigger, BpmnEventDirection } from '$lib/types/canvas';

	export interface EventVariant {
		entityType: BpmnEntityType;
		eventTrigger: BpmnEventTrigger;
		eventDirection?: BpmnEventDirection;
		boundaryInterrupting?: boolean;
	}

	interface Props {
		open: boolean;
		onpick?: (variant: EventVariant) => void;
		onclose?: () => void;
	}

	let { open = $bindable(), onpick, onclose }: Props = $props();

	type Position = 'start' | 'intermediate_catch' | 'intermediate_throw' | 'end' | 'boundary' | 'boundary_ni';

	const POSITIONS: { id: Position; label: string }[] = [
		{ id: 'start',              label: 'Start' },
		{ id: 'intermediate_catch', label: 'Intermediate (catch)' },
		{ id: 'intermediate_throw', label: 'Intermediate (throw)' },
		{ id: 'end',                label: 'End' },
		{ id: 'boundary',           label: 'Boundary (interrupting)' },
		{ id: 'boundary_ni',        label: 'Boundary (non-interrupting)' },
	];

	const TRIGGERS: { id: BpmnEventTrigger; label: string; glyph: string }[] = [
		{ id: 'none',         label: 'None',         glyph: '' },
		{ id: 'message',      label: 'Message',      glyph: '✉' },
		{ id: 'timer',        label: 'Timer',        glyph: '⏱' },
		{ id: 'signal',       label: 'Signal',       glyph: '▲' },
		{ id: 'conditional',  label: 'Conditional',  glyph: '☰' },
		{ id: 'error',        label: 'Error',        glyph: '⚡' },
		{ id: 'escalation',   label: 'Escalation',   glyph: '⇗' },
		{ id: 'compensation', label: 'Compensation', glyph: '◀◀' },
		{ id: 'link',         label: 'Link',         glyph: '➤' },
		{ id: 'terminate',    label: 'Terminate',    glyph: '●' },
	];

	/** Which (position × trigger) combinations are legal in BPMN 2.0. */
	function isLegal(p: Position, t: BpmnEventTrigger): boolean {
		// Terminate is end-only.
		if (t === 'terminate') return p === 'end';
		// Error: catch-only at start/intermediate/boundary; allowed at end (throw).
		if (t === 'error') return p !== 'intermediate_throw';
		// Timer: catch-only.
		if (t === 'timer') return p !== 'intermediate_throw' && p !== 'end';
		// Conditional: catch-only.
		if (t === 'conditional') return p !== 'intermediate_throw' && p !== 'end';
		// Compensation: throw at intermediate/end; catch at boundary.
		if (t === 'compensation') return p === 'intermediate_throw' || p === 'end' || p === 'boundary';
		// Link is intermediate-only.
		if (t === 'link') return p === 'intermediate_catch' || p === 'intermediate_throw';
		// Signal is allowed everywhere.
		// Message is allowed everywhere.
		// Escalation: throw at intermediate/end; catch at boundary, start (event subprocess).
		if (t === 'escalation') return p === 'intermediate_throw' || p === 'end' || p === 'boundary' || p === 'boundary_ni' || p === 'start';
		return true;
	}

	function variantFor(p: Position, t: BpmnEventTrigger): EventVariant {
		switch (p) {
			case 'start':              return { entityType: 'event_start',        eventTrigger: t };
			case 'intermediate_catch': return { entityType: 'event_intermediate', eventTrigger: t, eventDirection: 'catch' };
			case 'intermediate_throw': return { entityType: 'event_intermediate', eventTrigger: t, eventDirection: 'throw' };
			case 'end':                return { entityType: 'event_end',          eventTrigger: t };
			case 'boundary':           return { entityType: 'event_boundary',     eventTrigger: t, boundaryInterrupting: true };
			case 'boundary_ni':        return { entityType: 'event_boundary',     eventTrigger: t, boundaryInterrupting: false };
		}
	}

	function pick(p: Position, t: BpmnEventTrigger) {
		if (!isLegal(p, t)) return;
		onpick?.(variantFor(p, t));
		onclose?.();
	}
</script>

{#if open}
	<div
		class="bpmn-event-matrix__backdrop"
		role="presentation"
		onclick={() => onclose?.()}
		onkeydown={(e) => { if (e.key === 'Escape') onclose?.(); }}
	></div>
	<div class="bpmn-event-matrix" role="dialog" aria-label="BPMN event picker">
		<header class="bpmn-event-matrix__header">
			<span>Pick an event</span>
			<button type="button" onclick={() => onclose?.()} aria-label="Close">✕</button>
		</header>
		<div class="bpmn-event-matrix__grid" role="grid">
			<div class="bpmn-event-matrix__cell bpmn-event-matrix__cell--corner"></div>
			{#each TRIGGERS as t (t.id)}
				<div class="bpmn-event-matrix__cell bpmn-event-matrix__cell--trigger" title={t.label}>
					<span aria-hidden="true">{t.glyph}</span>
				</div>
			{/each}
			{#each POSITIONS as p (p.id)}
				<div class="bpmn-event-matrix__cell bpmn-event-matrix__cell--position">{p.label}</div>
				{#each TRIGGERS as t (t.id)}
					{@const legal = isLegal(p.id, t.id)}
					<button
						type="button"
						class="bpmn-event-matrix__cell bpmn-event-matrix__cell--option"
						class:bpmn-event-matrix__cell--disabled={!legal}
						disabled={!legal}
						onclick={() => pick(p.id, t.id)}
						title="{p.label} · {t.label}"
						data-position={p.id}
						data-trigger={t.id}
					>
						{#if legal}<span aria-hidden="true">{t.glyph || '○'}</span>{/if}
					</button>
				{/each}
			{/each}
		</div>
	</div>
{/if}

<style>
	.bpmn-event-matrix__backdrop {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.18); z-index: 998;
	}
	.bpmn-event-matrix {
		position: fixed; top: 12%; left: 50%;
		transform: translateX(-50%);
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 8px;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
		z-index: 999; padding: 8px;
	}
	.bpmn-event-matrix__header {
		display: flex; justify-content: space-between; align-items: center;
		padding: 4px 8px 8px; font-weight: 600;
	}
	.bpmn-event-matrix__header button {
		background: transparent; border: 0; cursor: pointer; font-size: 16px;
	}
	.bpmn-event-matrix__grid {
		display: grid;
		grid-template-columns: 180px repeat(10, 32px);
		gap: 2px;
	}
	.bpmn-event-matrix__cell {
		display: flex; align-items: center; justify-content: center;
		min-height: 30px; font-size: 14px;
	}
	.bpmn-event-matrix__cell--position { justify-content: flex-start; padding-left: 6px; font-size: 12px; font-weight: 500; }
	.bpmn-event-matrix__cell--trigger  { font-size: 14px; opacity: 0.8; }
	.bpmn-event-matrix__cell--option {
		background: transparent;
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 4px; cursor: pointer;
	}
	.bpmn-event-matrix__cell--option:hover:not(.bpmn-event-matrix__cell--disabled) {
		background: var(--color-surface-hover, #f3f4f6);
		border-color: var(--color-fg, #202931);
	}
	.bpmn-event-matrix__cell--disabled {
		background: repeating-linear-gradient(45deg, transparent 0 4px, rgba(0,0,0,0.04) 4px 6px);
		cursor: not-allowed;
	}
	.bpmn-event-matrix__cell--corner { background: transparent; }
</style>
