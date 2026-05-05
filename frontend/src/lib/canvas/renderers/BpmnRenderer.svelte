<script lang="ts">
	/**
	 * BpmnRenderer: Renders nodes in BPMN 2.0 notation (ADR-136).
	 *
	 * BPMN has only ~14 base entity types but each renders as a distinct
	 * shape with inner-marker variants driven by `data` discriminator
	 * fields (taskType, gatewayType, eventTrigger, eventDirection,
	 * boundaryInterrupting, subprocessKind, dataKind). This renderer
	 * dispatches on entityType and applies the right SVG shape + marker.
	 *
	 * Theme defaults come from the bpmn-default theme seeded by m043/m044.
	 */
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import type { CanvasNodeData, NotationType } from '$lib/types/canvas';
	import { getThemeRendering } from '$lib/stores/themeStore.svelte';
	import { nodeOverrideStyle, titleFontStyle } from '$lib/canvas/utils/visualStyles';
	import ContextPad from '$lib/canvas/palette/ContextPad.svelte';

	interface Props {
		/** Node id — xyflow auto-passes this to custom node components. Used by
		 *  the v5.2.0 (issue #37) ContextPad mount so it can call back to the
		 *  page-level handler with the right nodeId. */
		id?: string;
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { id = '', data, selected = false }: Props = $props();

	/** v5.2.0 (issue #37): the page sets this via UnifiedCanvas's
	 *  setContext('bpmnContextPadAction', …). When undefined the pad still
	 *  renders but actions are no-ops. */
	const onContextPadAction = getContext<(action: string, nodeId: string) => void>('bpmnContextPadAction');

	const notation = getContext<NotationType>('notation') ?? 'bpmn';
	const rendering = $derived(getThemeRendering(notation));
	const wrapLabels = $derived(rendering?.wrapLabels ?? true);
	const textAlign = $derived(rendering?.textAlign ?? 'center');

	const visualStyle = $derived(nodeOverrideStyle(data.visual));
	const titleStyle = $derived(titleFontStyle(data.visual));

	type Disc = Record<string, unknown>;
	const disc = $derived((data as unknown as { data?: Disc }).data ?? (data as unknown as Disc));

	function discStr(key: string, fallback = ''): string {
		const v = disc?.[key];
		return typeof v === 'string' ? v : fallback;
	}
	function discBool(key: string, fallback = true): boolean {
		const v = disc?.[key];
		return typeof v === 'boolean' ? v : fallback;
	}

	// Discriminators
	const taskType            = $derived(discStr('taskType', 'none'));
	const subprocessKind      = $derived(discStr('subprocessKind', 'embedded'));
	const eventTrigger        = $derived(discStr('eventTrigger', 'none'));
	const eventDirection      = $derived(discStr('eventDirection', 'catch'));
	const boundaryInterrupting = $derived(discBool('boundaryInterrupting', true));
	const gatewayType         = $derived(discStr('gatewayType', 'exclusive'));
	const dataKind            = $derived(discStr('dataKind', 'object'));

	const entity = $derived(data.entityType);
	const isActivity     = $derived(entity === 'task' || entity === 'subprocess' || entity === 'call_activity');
	const isEvent        = $derived(entity?.startsWith('event_') ?? false);
	const isGateway      = $derived(entity === 'gateway');
	const isSwimlane     = $derived(entity === 'pool' || entity === 'lane');
	const isData         = $derived(entity === 'data_object' || entity === 'data_store');
	const isGroup        = $derived(entity === 'group');
	const isAnnotation   = $derived(entity === 'text_annotation');

	// Activity marker glyphs (Unicode approximations of BPMN 2.0 markers).
	const TASK_MARKERS: Record<string, string> = {
		none: '', user: '👤', service: '⚙', manual: '✋', send: '✉',
		receive: '✉', script: '📜', business_rule: '▤',
	};
	const taskMarker = $derived(TASK_MARKERS[taskType] ?? '');

	// Event trigger glyphs — BPMN 2.0 uses these inner markers.
	const EVENT_TRIGGERS: Record<string, string> = {
		none: '', message: '✉', timer: '⏱', signal: '▲', conditional: '☰',
		error: '⚡', escalation: '⇗', compensation: '◀◀', link: '➤', terminate: '●',
	};
	const eventTrigger_glyph = $derived(EVENT_TRIGGERS[eventTrigger] ?? '');

	// Gateway markers.
	const GATEWAY_MARKERS: Record<string, string> = {
		exclusive: '✕', inclusive: '○', parallel: '✚', event_based: '⬠',
		complex: '✱', parallel_event_based: '⬠',
	};
	const gatewayMarker = $derived(GATEWAY_MARKERS[gatewayType] ?? '');

	const label = $derived(data.label ?? '');
</script>

<!-- Source/target handles common to every BPMN node -->
<Handle type="target" position={Position.Left} />
<Handle type="source" position={Position.Right} />

<!-- v5.2.0 (issue #37): on-element context pad. Already wraps <NodeToolbar>
	 so it auto-anchors to this node and follows pan/zoom. -->
<ContextPad
	nodeId={id}
	visible={selected}
	onaction={(action, nodeId) => onContextPadAction?.(action, nodeId)}
/>

{#if isActivity}
	<div
		class="bpmn-activity"
		class:bpmn-activity--task={entity === 'task'}
		class:bpmn-activity--subprocess={entity === 'subprocess'}
		class:bpmn-activity--call={entity === 'call_activity'}
		class:bpmn-activity--event-sub={entity === 'subprocess' && subprocessKind === 'event'}
		class:bpmn-activity--transaction={entity === 'subprocess' && subprocessKind === 'transaction'}
		class:bpmn-activity--ad-hoc={entity === 'subprocess' && subprocessKind === 'ad_hoc'}
		class:selected
		style={visualStyle}
	>
		{#if taskMarker}
			<span class="bpmn-task-marker" aria-hidden="true">{taskMarker}</span>
		{/if}
		<span
			class="bpmn-label"
			class:bpmn-label--wrap={wrapLabels}
			style="text-align: {textAlign}; {titleStyle}"
		>{label}</span>
		{#if entity === 'subprocess' && subprocessKind === 'ad_hoc'}
			<span class="bpmn-subprocess-marker" aria-label="ad-hoc">~</span>
		{/if}
	</div>
{:else if isEvent}
	<div class="bpmn-event-wrap" class:selected>
		<svg viewBox="0 0 64 64" class="bpmn-event-svg" aria-hidden="true">
			{#if entity === 'event_start'}
				<circle cx="32" cy="32" r="28" stroke-width="2" fill="var(--bpmn-event-start-fill, #E0F2D6)" stroke="var(--bpmn-event-start-stroke, #3BA51F)" />
			{:else if entity === 'event_end'}
				<circle cx="32" cy="32" r="28" stroke-width="4" fill="var(--bpmn-event-end-fill, #FBE3E3)" stroke="var(--bpmn-event-end-stroke, #C03434)" />
			{:else if entity === 'event_intermediate'}
				<circle cx="32" cy="32" r="28" stroke-width="1" fill="var(--bpmn-event-int-fill, #F4F4F4)" stroke="var(--bpmn-event-int-stroke, #A88B0F)" />
				<circle cx="32" cy="32" r="24" stroke-width="1" fill="none" stroke="var(--bpmn-event-int-stroke, #A88B0F)" />
			{:else if entity === 'event_boundary'}
				<circle cx="32" cy="32" r="28" stroke-width="1" stroke-dasharray={boundaryInterrupting ? 'none' : '4 3'} fill="var(--bpmn-event-int-fill, #F4F4F4)" stroke="var(--bpmn-event-int-stroke, #A88B0F)" />
				<circle cx="32" cy="32" r="24" stroke-width="1" stroke-dasharray={boundaryInterrupting ? 'none' : '4 3'} fill="none" stroke="var(--bpmn-event-int-stroke, #A88B0F)" />
			{/if}
			<text x="32" y="38" text-anchor="middle" font-size="22"
				class:event-trigger--throw={isEvent && eventDirection === 'throw'}>
				{eventTrigger_glyph}
			</text>
		</svg>
		{#if label}
			<div class="bpmn-event-label" class:bpmn-label--wrap={wrapLabels}>{label}</div>
		{/if}
	</div>
{:else if isGateway}
	<div class="bpmn-gateway-wrap" class:selected>
		<svg viewBox="0 0 64 64" class="bpmn-gateway-svg" aria-hidden="true">
			<polygon points="32,2 62,32 32,62 2,32" stroke="var(--bpmn-gateway-stroke, #A88B0F)" stroke-width="2" fill="var(--bpmn-gateway-fill, #FFFFFF)" />
			<text x="32" y="40" text-anchor="middle" font-size="28" font-weight="bold">{gatewayMarker}</text>
		</svg>
		{#if label}
			<div class="bpmn-event-label" class:bpmn-label--wrap={wrapLabels}>{label}</div>
		{/if}
	</div>
{:else if isSwimlane}
	<div
		class="bpmn-swimlane"
		class:bpmn-swimlane--pool={entity === 'pool'}
		class:bpmn-swimlane--lane={entity === 'lane'}
		class:selected
		style={visualStyle}
	>
		<div class="bpmn-swimlane-banner" style={titleStyle}>{label}</div>
		<div class="bpmn-swimlane-body" />
	</div>
{:else if isData}
	<div class="bpmn-data-wrap" class:selected>
		{#if entity === 'data_object'}
			<svg viewBox="0 0 48 64" class="bpmn-data-svg" aria-hidden="true">
				<polygon points="0,0 36,0 48,12 48,64 0,64" fill="var(--bpmn-data-fill, #FFFFFF)" stroke="var(--bpmn-data-stroke, #202931)" stroke-width="1" />
				<polyline points="36,0 36,12 48,12" fill="none" stroke="var(--bpmn-data-stroke, #202931)" stroke-width="1" />
				{#if dataKind === 'input'}
					<text x="24" y="56" text-anchor="middle" font-size="16">▷</text>
				{:else if dataKind === 'output'}
					<text x="24" y="56" text-anchor="middle" font-size="16">▶</text>
				{:else if dataKind === 'collection'}
					<text x="24" y="58" text-anchor="middle" font-size="14">≡</text>
				{/if}
			</svg>
		{:else}
			<svg viewBox="0 0 64 64" class="bpmn-data-svg" aria-hidden="true">
				<path d="M 4,12 Q 4,2 32,2 Q 60,2 60,12 L 60,52 Q 60,62 32,62 Q 4,62 4,52 Z" fill="var(--bpmn-data-fill, #FFFFFF)" stroke="var(--bpmn-data-stroke, #202931)" stroke-width="1" />
				<path d="M 4,12 Q 4,22 32,22 Q 60,22 60,12" fill="none" stroke="var(--bpmn-data-stroke, #202931)" stroke-width="1" />
			</svg>
		{/if}
		{#if label}
			<div class="bpmn-event-label" class:bpmn-label--wrap={wrapLabels}>{label}</div>
		{/if}
	</div>
{:else if isGroup}
	<div class="bpmn-group" class:selected style={visualStyle}>
		{#if label}<span class="bpmn-group-label" style={titleStyle}>{label}</span>{/if}
	</div>
{:else if isAnnotation}
	<div class="bpmn-annotation" class:selected style={visualStyle}>
		<span class="bpmn-annotation-bracket" aria-hidden="true">[</span>
		<span class="bpmn-label" class:bpmn-label--wrap={wrapLabels} style={titleStyle}>{label}</span>
	</div>
{:else}
	<!-- Unknown BPMN entity — fall back to simple labelled box. -->
	<div class="bpmn-activity bpmn-activity--task" style={visualStyle}>
		<span class="bpmn-label" class:bpmn-label--wrap={wrapLabels} style={titleStyle}>{label}</span>
	</div>
{/if}

<style>
	/* ── Activities ── */
	.bpmn-activity {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 110px;
		min-height: 60px;
		padding: 6px 10px;
		background: #FFFFFF;
		border: 2px solid #202931;
		border-radius: 6px;
		color: #202931;
		font-size: 12px;
		position: relative;
		box-sizing: border-box;
	}
	.bpmn-activity.selected { box-shadow: 0 0 0 2px var(--color-primary, #2563eb); }

	.bpmn-activity--call { border-width: 4px; }
	.bpmn-activity--event-sub { border-style: dashed; }
	.bpmn-activity--transaction {
		box-shadow: inset 0 0 0 2px #FFFFFF, inset 0 0 0 4px #202931;
	}
	.bpmn-activity--subprocess { background: #FFFFFF; }

	.bpmn-task-marker {
		position: absolute;
		top: 4px;
		left: 6px;
		font-size: 14px;
		opacity: 0.85;
		line-height: 1;
	}
	.bpmn-subprocess-marker {
		position: absolute;
		bottom: 4px;
		right: 8px;
		font-size: 14px;
		opacity: 0.85;
	}

	.bpmn-label {
		display: block;
		text-align: center;
		font-weight: 500;
	}
	.bpmn-label--wrap {
		white-space: normal;
		word-wrap: break-word;
		overflow-wrap: break-word;
		line-height: 1.3;
	}

	/* ── Events ── */
	.bpmn-event-wrap {
		width: 56px;
		height: 56px;
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.bpmn-event-wrap.selected .bpmn-event-svg circle:first-child {
		stroke-width: 3;
		filter: drop-shadow(0 0 2px var(--color-primary, #2563eb));
	}
	.bpmn-event-svg { width: 100%; height: 100%; }
	.bpmn-event-label {
		position: absolute;
		top: 100%;
		left: 50%;
		transform: translateX(-50%);
		margin-top: 2px;
		font-size: 11px;
		text-align: center;
		min-width: 80px;
	}
	.event-trigger--throw { fill: #202931; font-weight: bold; }

	/* ── Gateways ── */
	.bpmn-gateway-wrap {
		width: 56px;
		height: 56px;
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.bpmn-gateway-wrap.selected .bpmn-gateway-svg polygon {
		stroke-width: 3;
		filter: drop-shadow(0 0 2px var(--color-primary, #2563eb));
	}
	.bpmn-gateway-svg { width: 100%; height: 100%; }

	/* ── Swimlanes ── */
	.bpmn-swimlane {
		display: grid;
		grid-template-columns: 28px 1fr;
		min-width: 240px;
		min-height: 120px;
		background: #FFFFFF;
		border: 2px solid #202931;
	}
	.bpmn-swimlane--lane { border-width: 1px; }
	.bpmn-swimlane.selected { box-shadow: 0 0 0 2px var(--color-primary, #2563eb); }
	.bpmn-swimlane-banner {
		writing-mode: vertical-rl;
		transform: rotate(180deg);
		display: flex;
		align-items: center;
		justify-content: center;
		border-right: 1px solid #202931;
		font-weight: 600;
		padding: 4px;
	}
	.bpmn-swimlane-body { background: #FAFAFA; }

	/* ── Data ── */
	.bpmn-data-wrap {
		width: 48px;
		height: 64px;
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.bpmn-data-wrap.selected .bpmn-data-svg :is(polygon, path) {
		stroke-width: 2;
		filter: drop-shadow(0 0 2px var(--color-primary, #2563eb));
	}
	.bpmn-data-svg { width: 100%; height: 100%; }

	/* ── Group ── */
	.bpmn-group {
		min-width: 200px;
		min-height: 120px;
		border: 1px dashed #666666;
		border-radius: 8px;
		background: transparent;
		padding: 8px;
		position: relative;
		box-sizing: border-box;
	}
	.bpmn-group.selected { box-shadow: 0 0 0 2px var(--color-primary, #2563eb); }
	.bpmn-group-label {
		position: absolute;
		top: -10px;
		left: 12px;
		background: #FFFFFF;
		padding: 0 6px;
		font-size: 11px;
		color: #666666;
	}

	/* ── Text Annotation ── */
	.bpmn-annotation {
		display: flex;
		align-items: center;
		min-width: 120px;
		padding: 6px 10px;
		font-size: 12px;
		color: #202931;
		background: transparent;
		border: none;
	}
	.bpmn-annotation.selected { outline: 1px dashed var(--color-primary, #2563eb); }
	.bpmn-annotation-bracket {
		font-size: 26px;
		color: #666666;
		margin-right: 6px;
		line-height: 1;
	}
</style>
