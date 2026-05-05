<script lang="ts">
	/**
	 * ContextPad: on-element actions (ADR-136 §UX).
	 *
	 * Mirrors bpmn-js's context pad: appears next to the selected element
	 * with the canonical action order — Append Task → Append Gateway →
	 * Append End Event → Connect → Change (wrench, tooltip exposes "R") →
	 * Delete. The wrench tooltip explicitly names the keyboard shortcut to
	 * fix bpmn-js's documented discoverability problem.
	 *
	 * Wraps Svelte Flow's <NodeToolbar> so the pad anchors to the node and
	 * follows pan/zoom.
	 */
	import { NodeToolbar, Position } from '@xyflow/svelte';

	export type ContextPadAction =
		| 'append_task'
		| 'append_gateway'
		| 'append_end_event'
		| 'connect'
		| 'change'
		| 'bring_forward'
		| 'send_backward'
		| 'delete';

	interface Props {
		/** Node id used by the parent to dispatch the action. */
		nodeId: string;
		/** Visible only when this node is selected. */
		visible?: boolean;
		/** Hide the wrench (e.g. on event/data nodes that have no morph targets). */
		hideChange?: boolean;
		/** Action callback — parent applies it to its diagram state. */
		onaction?: (action: ContextPadAction, nodeId: string) => void;
	}

	let { nodeId, visible = true, hideChange = false, onaction }: Props = $props();

	const ACTIONS: { id: ContextPadAction; label: string; tooltip: string; glyph: string }[] = [
		{ id: 'append_task',      label: 'Append Task',      tooltip: 'Append Task',                glyph: '▭' },
		{ id: 'append_gateway',   label: 'Append Gateway',   tooltip: 'Append Gateway',             glyph: '◇' },
		{ id: 'append_end_event', label: 'Append End Event', tooltip: 'Append End Event',           glyph: '⬤' },
		{ id: 'connect',          label: 'Connect',          tooltip: 'Drag to connect',            glyph: '⇢' },
		{ id: 'change',           label: 'Change',           tooltip: 'Change element type (R)',    glyph: '🔧' },
		// v5.4.0 (#3): z-order controls — needed when items stack (lane on pool, etc).
		{ id: 'bring_forward',    label: 'Bring Forward',    tooltip: 'Bring forward',              glyph: '↑' },
		{ id: 'send_backward',    label: 'Send Backward',    tooltip: 'Send backward',              glyph: '↓' },
		{ id: 'delete',           label: 'Delete',           tooltip: 'Delete element (Del)',       glyph: '✖' },
	];

	const visibleActions = $derived(
		hideChange ? ACTIONS.filter(a => a.id !== 'change') : ACTIONS,
	);
</script>

{#if visible}
	<NodeToolbar position={Position.Right} offset={8}>
		<div class="bpmn-context-pad" role="toolbar" aria-label="BPMN context pad">
			{#each visibleActions as a (a.id)}
				<button
					type="button"
					class="bpmn-context-pad__btn"
					title={a.tooltip}
					aria-label={a.label}
					data-action={a.id}
					onclick={() => onaction?.(a.id, nodeId)}
				>
					<span aria-hidden="true">{a.glyph}</span>
				</button>
			{/each}
		</div>
	</NodeToolbar>
{/if}

<style>
	.bpmn-context-pad {
		display: grid;
		grid-template-columns: repeat(2, 28px);
		gap: 2px;
		padding: 2px;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
	}
	.bpmn-context-pad__btn {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: 0;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
		color: var(--color-fg, #202931);
	}
	.bpmn-context-pad__btn:hover { background: var(--color-surface-hover, #f3f4f6); }
</style>
