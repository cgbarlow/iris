<script lang="ts">
	/**
	 * PropertyPanel: right-side, always-on, refreshes on selection (ADR-136 §UX).
	 *
	 * Tabs: General · BPMN · Documentation. The BPMN tab exposes the
	 * notation-specific discriminator fields (taskType, gatewayType,
	 * eventTrigger, eventDirection, boundaryInterrupting, subprocessKind,
	 * dataKind) plus the activity markers (loop, multi-instance, ad-hoc,
	 * compensation). Modal property dialogs are explicitly avoided per the
	 * UX research — every loved BPMN tool moved to an always-on side panel.
	 */
	import type {
		BpmnEntityType, BpmnTaskType, BpmnGatewayType,
		BpmnEventTrigger, BpmnEventDirection, BpmnSubprocessKind, BpmnDataKind,
	} from '$lib/types/canvas';

	export interface PropertyPanelData {
		id: string;
		entityType: BpmnEntityType | string;
		label?: string;
		description?: string;
		data?: Record<string, unknown>;
	}

	interface Props {
		selection: PropertyPanelData | null;
		onchange?: (id: string, patch: Record<string, unknown>) => void;
	}

	let { selection, onchange }: Props = $props();

	let activeTab: 'general' | 'bpmn' | 'documentation' = $state('general');

	function setData(key: string, value: unknown) {
		if (!selection) return;
		onchange?.(selection.id, { [key]: value });
	}

	function getData<T>(key: string, fallback: T): T {
		const v = selection?.data?.[key];
		return v === undefined ? fallback : (v as T);
	}

	const TASK_TYPES: BpmnTaskType[] = ['none', 'user', 'service', 'manual', 'send', 'receive', 'script', 'business_rule'];
	const GATEWAY_TYPES: BpmnGatewayType[] = ['exclusive', 'inclusive', 'parallel', 'event_based', 'complex', 'parallel_event_based'];
	const EVENT_TRIGGERS: BpmnEventTrigger[] = ['none', 'message', 'timer', 'signal', 'conditional', 'error', 'escalation', 'compensation', 'link', 'terminate'];
	const EVENT_DIRECTIONS: BpmnEventDirection[] = ['catch', 'throw'];
	const SUBPROCESS_KINDS: BpmnSubprocessKind[] = ['embedded', 'event', 'ad_hoc', 'transaction'];
	const DATA_KINDS: BpmnDataKind[] = ['object', 'input', 'output', 'collection'];
</script>

<aside class="bpmn-props" aria-label="Element properties">
	{#if !selection}
		<div class="bpmn-props__empty">Select an element to edit its properties.</div>
	{:else}
		<header class="bpmn-props__header">
			<div class="bpmn-props__title">{selection.entityType}</div>
			<div class="bpmn-props__id">{selection.id}</div>
		</header>
		<nav class="bpmn-props__tabs" role="tablist">
			{#each ['general', 'bpmn', 'documentation'] as t}
				<button
					type="button"
					role="tab"
					aria-selected={activeTab === t}
					class="bpmn-props__tab"
					class:bpmn-props__tab--active={activeTab === t}
					onclick={() => (activeTab = t as typeof activeTab)}
				>{t}</button>
			{/each}
		</nav>

		{#if activeTab === 'general'}
			<div class="bpmn-props__body">
				<label>
					Label
					<input type="text" value={selection.label ?? ''} oninput={(e) => onchange?.(selection!.id, { label: (e.target as HTMLInputElement).value })} />
				</label>
			</div>
		{:else if activeTab === 'bpmn'}
			<div class="bpmn-props__body">
				{#if selection.entityType === 'task'}
					<label>
						Task type
						<select value={getData('taskType', 'none')} onchange={(e) => setData('taskType', (e.target as HTMLSelectElement).value)}>
							{#each TASK_TYPES as t}<option value={t}>{t}</option>{/each}
						</select>
					</label>
				{/if}
				{#if selection.entityType === 'gateway'}
					<label>
						Gateway type
						<select value={getData('gatewayType', 'exclusive')} onchange={(e) => setData('gatewayType', (e.target as HTMLSelectElement).value)}>
							{#each GATEWAY_TYPES as t}<option value={t}>{t}</option>{/each}
						</select>
					</label>
				{/if}
				{#if selection.entityType === 'subprocess'}
					<label>
						Subprocess kind
						<select value={getData('subprocessKind', 'embedded')} onchange={(e) => setData('subprocessKind', (e.target as HTMLSelectElement).value)}>
							{#each SUBPROCESS_KINDS as t}<option value={t}>{t}</option>{/each}
						</select>
					</label>
				{/if}
				{#if selection.entityType === 'data_object'}
					<label>
						Data kind
						<select value={getData('dataKind', 'object')} onchange={(e) => setData('dataKind', (e.target as HTMLSelectElement).value)}>
							{#each DATA_KINDS as t}<option value={t}>{t}</option>{/each}
						</select>
					</label>
				{/if}
				{#if selection.entityType?.startsWith('event_')}
					<label>
						Trigger
						<select value={getData('eventTrigger', 'none')} onchange={(e) => setData('eventTrigger', (e.target as HTMLSelectElement).value)}>
							{#each EVENT_TRIGGERS as t}<option value={t}>{t}</option>{/each}
						</select>
					</label>
					{#if selection.entityType === 'event_intermediate'}
						<label>
							Direction
							<select value={getData('eventDirection', 'catch')} onchange={(e) => setData('eventDirection', (e.target as HTMLSelectElement).value)}>
								{#each EVENT_DIRECTIONS as t}<option value={t}>{t}</option>{/each}
							</select>
						</label>
					{/if}
					{#if selection.entityType === 'event_boundary'}
						<label class="bpmn-props__checkbox">
							<input
								type="checkbox"
								checked={getData('boundaryInterrupting', true)}
								onchange={(e) => setData('boundaryInterrupting', (e.target as HTMLInputElement).checked)}
							/>
							Interrupting (solid border)
						</label>
					{/if}
				{/if}
				{#if ['task', 'subprocess', 'call_activity'].includes(selection.entityType)}
					<fieldset class="bpmn-props__markers">
						<legend>Markers</legend>
						{#each ['loop', 'multi_instance_parallel', 'multi_instance_sequential', 'compensation'] as marker}
							<label class="bpmn-props__checkbox">
								<input
									type="checkbox"
									checked={getData(`marker_${marker}`, false)}
									onchange={(e) => setData(`marker_${marker}`, (e.target as HTMLInputElement).checked)}
								/>
								{marker.replace(/_/g, ' ')}
							</label>
						{/each}
					</fieldset>
				{/if}
			</div>
		{:else}
			<div class="bpmn-props__body">
				<label>
					Documentation
					<textarea
						rows="6"
						value={selection.description ?? ''}
						oninput={(e) => onchange?.(selection!.id, { description: (e.target as HTMLTextAreaElement).value })}
					></textarea>
				</label>
			</div>
		{/if}
	{/if}
</aside>

<style>
	.bpmn-props {
		width: 280px; height: 100%;
		display: flex; flex-direction: column;
		background: var(--color-surface, #ffffff);
		border-left: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
	}
	.bpmn-props__empty { padding: 16px; color: var(--color-muted, #6b7280); text-align: center; }
	.bpmn-props__header { padding: 12px; border-bottom: 1px solid var(--color-border, #e5e7eb); }
	.bpmn-props__title { font-weight: 600; font-size: 13px; }
	.bpmn-props__id { font-family: monospace; font-size: 10px; color: var(--color-muted, #6b7280); margin-top: 2px; }
	.bpmn-props__tabs { display: flex; border-bottom: 1px solid var(--color-border, #e5e7eb); }
	.bpmn-props__tab {
		flex: 1; padding: 8px;
		background: transparent; border: 0; cursor: pointer;
		text-transform: capitalize; font-size: 11px;
		color: var(--color-muted, #6b7280);
	}
	.bpmn-props__tab--active {
		color: var(--color-fg, #202931);
		border-bottom: 2px solid var(--color-primary, #2563eb);
	}
	.bpmn-props__body { padding: 12px; display: flex; flex-direction: column; gap: 12px; }
	.bpmn-props__body label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 500; }
	.bpmn-props__body input, .bpmn-props__body select, .bpmn-props__body textarea {
		font-size: 12px; padding: 4px 6px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		background: var(--color-surface, #ffffff);
		color: var(--color-fg, #202931);
	}
	.bpmn-props__checkbox { flex-direction: row; align-items: center; gap: 6px; }
	.bpmn-props__markers { border: 1px solid var(--color-border, #e5e7eb); padding: 8px; border-radius: 4px; display: flex; flex-direction: column; gap: 4px; }
	.bpmn-props__markers legend { font-size: 11px; font-weight: 600; padding: 0 4px; }
</style>
