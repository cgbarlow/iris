<script lang="ts">
	/**
	 * BpmnPalette: 6-section accordion palette for BPMN authoring (ADR-136).
	 *
	 * Sections (BPMN 2.0 §7.4 categories): Activities, Events, Gateways,
	 * Swimlanes, Data, Artifacts. Each section shows ONE representative per
	 * family — variants are picked through the EventMatrixPicker and
	 * PropertyPanel discriminator fields. This avoids draw.io's failure mode
	 * of flat-listing every BPMN variant on the palette.
	 *
	 * Emits `select` with the entity-type key on click/drag-end so the parent
	 * can drop the element on the canvas.
	 */
	import { BPMN_ENTITY_TYPES, type BpmnCategory, type BpmnEntityType, type BpmnEntityTypeInfo } from '$lib/types/canvas';

	interface Props {
		/** Initial section that is expanded. */
		initialOpen?: BpmnCategory;
		/** Called when the user clicks (or drag-ends) a palette entry. */
		onselect?: (key: BpmnEntityType) => void;
	}

	let { initialOpen = 'activity', onselect }: Props = $props();

	const SECTIONS: { id: BpmnCategory; label: string }[] = [
		{ id: 'activity', label: 'Activities' },
		{ id: 'event',    label: 'Events' },
		{ id: 'gateway',  label: 'Gateways' },
		{ id: 'swimlane', label: 'Swimlanes' },
		{ id: 'data',     label: 'Data' },
		{ id: 'artifact', label: 'Artifacts' },
	];

	let open: Set<BpmnCategory> = $state(new Set([initialOpen]));

	function toggle(id: BpmnCategory) {
		if (open.has(id)) open.delete(id);
		else open.add(id);
		open = new Set(open);
	}

	function entriesFor(category: BpmnCategory): BpmnEntityTypeInfo[] {
		return BPMN_ENTITY_TYPES.filter(e => e.category === category);
	}

	function pick(key: BpmnEntityType) {
		onselect?.(key);
	}
</script>

<aside class="bpmn-palette" aria-label="BPMN palette">
	{#each SECTIONS as section (section.id)}
		<section class="bpmn-palette__section">
			<button
				type="button"
				class="bpmn-palette__heading"
				aria-expanded={open.has(section.id)}
				onclick={() => toggle(section.id)}
			>
				<span class="bpmn-palette__chevron" aria-hidden="true">{open.has(section.id) ? '▾' : '▸'}</span>
				<span>{section.label}</span>
			</button>
			{#if open.has(section.id)}
				<ul class="bpmn-palette__list" role="list">
					{#each entriesFor(section.id) as entry (entry.key)}
						<li>
							<button
								type="button"
								class="bpmn-palette__item"
								title={entry.description}
								draggable="true"
								ondragstart={(e) => e.dataTransfer?.setData('application/iris-bpmn-entity', entry.key)}
								onclick={() => pick(entry.key)}
								data-key={entry.key}
							>
								<span class="bpmn-palette__icon" aria-hidden="true">{entry.icon}</span>
								<span class="bpmn-palette__label">{entry.label}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/each}
</aside>

<style>
	.bpmn-palette {
		width: 220px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 8px;
		background: var(--color-surface, #ffffff);
		border-right: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
	}
	.bpmn-palette__section { display: flex; flex-direction: column; }
	.bpmn-palette__heading {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 6px;
		background: transparent;
		border: 0;
		text-align: left;
		font-weight: 600;
		cursor: pointer;
		color: var(--color-fg, #202931);
	}
	.bpmn-palette__heading:hover { background: var(--color-surface-hover, #f3f4f6); border-radius: 4px; }
	.bpmn-palette__chevron { font-size: 10px; opacity: 0.6; width: 10px; }
	.bpmn-palette__list { list-style: none; margin: 0; padding: 0 0 4px 18px; display: flex; flex-direction: column; gap: 2px; }
	.bpmn-palette__item {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 4px 6px;
		background: transparent;
		border: 1px solid transparent;
		border-radius: 4px;
		text-align: left;
		cursor: grab;
		color: var(--color-fg, #202931);
	}
	.bpmn-palette__item:hover { background: var(--color-surface-hover, #f3f4f6); border-color: var(--color-border, #e5e7eb); }
	.bpmn-palette__item:active { cursor: grabbing; }
	.bpmn-palette__icon { display: inline-flex; width: 18px; justify-content: center; }
</style>
