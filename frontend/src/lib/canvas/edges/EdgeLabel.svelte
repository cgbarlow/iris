<script lang="ts">
	/** Shared edge label component for display, inline editing, and repositioning (WP-3/WP-4).
	 *
	 * When double-clicked, enters edit mode. On commit, dispatches a
	 * 'edgelabeledit' CustomEvent on the document with {edgeId, label} detail.
	 * Supports drag-to-reposition via pointer events, dispatching
	 * 'edgelabelmove' CustomEvent with {edgeId, offsetX, offsetY}.
	 */
	import { EdgeLabel as FlowEdgeLabel } from '@xyflow/svelte';
	import DOMPurify from 'dompurify';

	interface Props {
		edgeId: string;
		label: string;
		labelX: number;
		labelY: number;
		offsetX?: number;
		offsetY?: number;
		rotation?: number;
	}

	let { edgeId, label, labelX, labelY, offsetX = 0, offsetY = 0, rotation = 0 }: Props = $props();

	let isEditing = $state(false);
	let editValue = $state('');

	// Drag state
	let isDragging = $state(false);
	let dragStartX = $state(0);
	let dragStartY = $state(0);
	let dragOffsetX = $state(0);
	let dragOffsetY = $state(0);

	const effectiveX = $derived(labelX + offsetX + dragOffsetX);
	const effectiveY = $derived(labelY + offsetY + dragOffsetY);

	function startEdit() {
		if (isDragging) return;
		editValue = label;
		isEditing = true;
	}

	function commitEdit() {
		const sanitized = DOMPurify.sanitize(editValue.trim());
		if (sanitized !== label) {
			document.dispatchEvent(
				new CustomEvent('edgelabeledit', { detail: { edgeId, label: sanitized } }),
			);
		}
		isEditing = false;
	}

	function cancelEdit() {
		isEditing = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			commitEdit();
		} else if (event.key === 'Escape') {
			cancelEdit();
		}
	}

	function onpointerdown(event: PointerEvent) {
		if (isEditing) return;
		event.stopPropagation();
		isDragging = true;
		dragStartX = event.clientX;
		dragStartY = event.clientY;
		dragOffsetX = 0;
		dragOffsetY = 0;
		(event.target as HTMLElement).setPointerCapture(event.pointerId);
	}

	function onpointermove(event: PointerEvent) {
		if (!isDragging) return;
		dragOffsetX = event.clientX - dragStartX;
		dragOffsetY = event.clientY - dragStartY;
	}

	function onpointerup() {
		if (!isDragging) return;
		isDragging = false;
		if (Math.abs(dragOffsetX) > 2 || Math.abs(dragOffsetY) > 2) {
			document.dispatchEvent(
				new CustomEvent('edgelabelmove', {
					detail: {
						edgeId,
						offsetX: offsetX + dragOffsetX,
						offsetY: offsetY + dragOffsetY,
					},
				}),
			);
		}
		dragOffsetX = 0;
		dragOffsetY = 0;
	}
</script>

<FlowEdgeLabel x={effectiveX} y={effectiveY}>
	<div
		class="edge-label"
		style="transform: rotate({rotation}deg);"
	>
		{#if isEditing}
			<input
				type="text"
				bind:value={editValue}
				onblur={commitEdit}
				onkeydown={handleKeydown}
				class="edge-label__input"
				style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-primary); border-radius: 3px; padding: 1px 4px; font-size: 0.7rem; width: 100px; text-align: center;"
				aria-label="Edit edge label"
			/>
		{:else}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<button
				class="edge-label__text"
				style="background: var(--color-bg); color: var(--color-muted); border: none; padding: 1px 4px; font-size: 0.7rem; cursor: {isDragging ? 'grabbing' : 'grab'}; border-radius: 3px; user-select: none;"
				ondblclick={startEdit}
				{onpointerdown}
				{onpointermove}
				{onpointerup}
				aria-label="Edge label: {label}"
			>
				{label}
			</button>
		{/if}
	</div>
</FlowEdgeLabel>
