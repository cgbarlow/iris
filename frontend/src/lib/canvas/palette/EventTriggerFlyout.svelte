<script lang="ts">
	/**
	 * v5.4.1 (#46 item #11): EventTriggerFlyout — compact ContextPad-style
	 * horizontal row of trigger glyph buttons. Replaces the 60-cell
	 * EventMatrixPicker dialog for the common path (palette-drop / palette-
	 * click), which duplicated information the user had already supplied
	 * (the position is implied by which palette entry they picked).
	 *
	 * Renders ONLY the legal triggers for the chosen position so the
	 * surface stays small and scannable. Closes on pick / Esc / outside-
	 * click. If the user dismisses without picking, the placed node keeps
	 * its default `none` trigger.
	 */
	import type { BpmnEventTrigger } from '$lib/types/canvas';
	import { TRIGGERS, isLegal, type EventPosition } from './bpmnEventModel';

	interface Props {
		open: boolean;
		position: EventPosition;
		/** Pixel coordinates relative to the canvas viewport — anchor the flyout near the just-placed node. */
		x?: number;
		y?: number;
		onpick?: (trigger: BpmnEventTrigger) => void;
		onclose?: () => void;
	}

	let { open = $bindable(), position, x = 0, y = 0, onpick, onclose }: Props = $props();

	const legalTriggers = $derived(TRIGGERS.filter((t) => isLegal(position, t.id)));

	function pick(t: BpmnEventTrigger) {
		onpick?.(t);
		onclose?.();
	}

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose?.();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<!-- Backdrop swallows clicks so the flyout dismisses on outside-click. -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="bpmn-event-flyout__backdrop" role="presentation" onclick={() => onclose?.()}></div>
	<div
		class="bpmn-event-flyout"
		role="dialog"
		aria-label="Pick event trigger"
		style="left: {x}px; top: {y}px"
	>
		{#each legalTriggers as t (t.id)}
			<button
				type="button"
				class="bpmn-event-flyout__btn"
				title={t.label}
				data-trigger={t.id}
				onclick={() => pick(t.id)}
			>
				<span aria-hidden="true">{t.glyph}</span>
				<span class="sr-only">{t.label}</span>
			</button>
		{/each}
	</div>
{/if}

<style>
	.bpmn-event-flyout__backdrop {
		position: fixed;
		inset: 0;
		z-index: 49;
		background: transparent;
	}
	.bpmn-event-flyout {
		position: absolute;
		z-index: 50;
		display: flex;
		flex-direction: row;
		gap: 4px;
		padding: 6px;
		border: 1px solid var(--color-border, #d4d4d4);
		border-radius: 8px;
		background: var(--color-surface, #fff);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
	}
	.bpmn-event-flyout__btn {
		min-width: 32px;
		height: 32px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		line-height: 1;
		padding: 0 6px;
		border: 1px solid var(--color-border, #d4d4d4);
		border-radius: 6px;
		background: var(--color-bg, #fff);
		color: var(--color-fg, #111);
		cursor: pointer;
	}
	.bpmn-event-flyout__btn:hover {
		background: var(--color-hover, #f3f4f6);
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
</style>
