<script lang="ts">
	/**
	 * v5.2.0 (issue #37): BPMN authoring shell.
	 *
	 * Mounts the six BPMN-specific UX surfaces from ADR-136 §UX into a
	 * 3-column layout (palette / canvas / property panel) with a bottom
	 * problems dock and a fixed toast for canConnect rejection reasons.
	 *
	 * Mounted from `views/[id]/+page.svelte` only when
	 * `notation === 'bpmn' && editing`. Replaces the generic right-side
	 * ElementEditPanel/NodeStylePanel stack with the always-on
	 * PropertyPanel for BPMN views.
	 *
	 * Keeps the views detail page (already 3.2k lines) from ballooning.
	 */
	import { tick } from 'svelte';
	import type { Connection, Edge } from '@xyflow/svelte';
	import UnifiedCanvas from '$lib/canvas/UnifiedCanvas.svelte';
	import BpmnPalette from '$lib/canvas/palette/BpmnPalette.svelte';
	import CommandPalette, { type CommandMode } from '$lib/canvas/palette/CommandPalette.svelte';
	import EventMatrixPicker from '$lib/canvas/palette/EventMatrixPicker.svelte';
	import PropertyPanel, { type PropertyPanelData } from '$lib/canvas/properties/PropertyPanel.svelte';
	import ProblemsPanel from '$lib/canvas/validation/ProblemsPanel.svelte';
	import BpmnToast from '$lib/canvas/bpmn/BpmnToast.svelte';
	import { canConnect } from '$lib/canvas/validation/bpmnRules';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Element } from '$lib/types/api';
	import {
		BPMN_DEFAULT_DISCRIMINATORS,
		type BpmnEntityType,
		type BpmnEntityTypeInfo,
		type CanvasNode,
		type CanvasEdge,
		type NotationType,
	} from '$lib/types/canvas';
	import type { createCanvasHistory } from '$lib/canvas/useCanvasHistory.svelte';

	interface Props {
		canvasNodes: CanvasNode[];
		canvasEdges: CanvasEdge[];
		notation: NotationType;
		preferredThemeId?: string;
		selectedEditNodeId: string | null;
		history: ReturnType<typeof createCanvasHistory>;
		/** v5.4.0 (#13): the diagram's set_id, used when POSTing /api/elements
		 *  so the backing Iris Element lands in the right repository scope. */
		setId?: string | null;
		oncanvasdirty?: () => void;
		onnodeselect?: (id: string | null) => void;
		onedgeselect?: (id: string | null) => void;
	}

	let {
		canvasNodes = $bindable([]),
		canvasEdges = $bindable([]),
		notation,
		preferredThemeId,
		selectedEditNodeId = $bindable(null),
		history,
		setId,
		oncanvasdirty,
		onnodeselect,
		onedgeselect,
	}: Props = $props();

	let cmdOpen = $state(false);
	let cmdMode = $state<CommandMode>('create');
	let eventPickerOpen = $state(false);
	let eventPickerContext = $state<'create' | 'replace'>('create');
	let pendingDropPosition = $state<{ x: number; y: number } | null>(null);
	let toastMessage = $state('');

	// ────────────────────────────────────────────────────────────────────
	// Selection → PropertyPanel data
	// ────────────────────────────────────────────────────────────────────
	const selectedNode = $derived(
		selectedEditNodeId ? canvasNodes.find((n) => n.id === selectedEditNodeId) ?? null : null,
	);
	const propertySelection = $derived<PropertyPanelData | null>(
		selectedNode
			? {
					id: selectedNode.id,
					entityType: (selectedNode.data?.entityType as string) ?? 'task',
					label: (selectedNode.data?.label as string | undefined) ?? '',
					description: (selectedNode.data?.description as string | undefined) ?? '',
					data: ((selectedNode.data as Record<string, unknown> | undefined)?.data as
						| Record<string, unknown>
						| undefined) ?? {},
				}
			: null,
	);

	function dirty() {
		oncanvasdirty?.();
	}

	function pushHistory() {
		history.pushState(canvasNodes, canvasEdges);
	}

	// ────────────────────────────────────────────────────────────────────
	// Drop / palette / command palette → create node
	// ────────────────────────────────────────────────────────────────────

	/**
	 * v5.4.0 (#2/#4): per-entity-type node dimensions. Pre-v5.4 every BPMN
	 * node was created with `width: 200`, which is correct for tasks but
	 * wrong for events (visually 56×56 — see BpmnRenderer's `.bpmn-event-wrap`
	 * CSS), gateways (56×56), data objects (48×64), pools (wide containers),
	 * etc. The over-wide bounding box pushed ContextPad far to the right of
	 * the actual shape. These widths match the CSS in BpmnRenderer.svelte.
	 */
	const BPMN_NODE_DIMENSIONS: Record<BpmnEntityType, { width: number; height: number }> = {
		task:               { width: 200, height: 80 },
		subprocess:         { width: 200, height: 80 },
		call_activity:      { width: 200, height: 80 },
		event_start:        { width: 56,  height: 56 },
		event_intermediate: { width: 56,  height: 56 },
		event_end:          { width: 56,  height: 56 },
		event_boundary:     { width: 56,  height: 56 },
		gateway:            { width: 56,  height: 56 },
		pool:               { width: 600, height: 200 },
		lane:               { width: 560, height: 100 },
		data_object:        { width: 48,  height: 64 },
		data_store:         { width: 64,  height: 64 },
		group:              { width: 240, height: 140 },
		text_annotation:    { width: 160, height: 56 },
	};

	/** v5.4.0 (#13): every BPMN node is now backed by an Iris Element —
	 *  POSTs /api/elements with notation='bpmn' and stores the resulting
	 *  Element id (the canonical Iris entity id) on the node so the rest
	 *  of the platform (search, knowledge graph, tags, comments,
	 *  iris://element/<id> refs) can find it. Mirrors the page-level
	 *  handleAddElement pattern at views/[id]/+page.svelte. */
	async function createBpmnElement(
		entityKey: BpmnEntityType,
		name: string,
	): Promise<Element | null> {
		const body: Record<string, unknown> = {
			element_type: entityKey,
			name,
			description: '',
			data: {},
			notation: 'bpmn',
		};
		if (setId) body.set_id = setId;
		try {
			return await apiFetch<Element>('/api/elements', {
				method: 'POST',
				body: JSON.stringify(body),
			});
		} catch (e) {
			toastMessage = e instanceof ApiError ? `Couldn't save element: ${e.message}` : "Couldn't save element — check connection.";
			return null;
		}
	}

	/** v5.4.0 (#13): keep the backing Element in sync when the user edits
	 *  label/description in PropertyPanel. Best-effort — failures don't block
	 *  the canvas-level update. Reuses the existing /api/elements PUT shape
	 *  with If-Match for optimistic concurrency (matches handleEditElementSave). */
	async function updateBpmnElement(
		entityId: string,
		patch: { name?: string; description?: string; element_type?: string },
	): Promise<void> {
		if (!entityId) return;
		try {
			const current = await apiFetch<Element>(`/api/elements/${entityId}`);
			await apiFetch(`/api/elements/${entityId}`, {
				method: 'PUT',
				headers: { 'If-Match': String(current.current_version) },
				body: JSON.stringify({
					element_type: patch.element_type ?? current.element_type,
					name: patch.name ?? current.name,
					description: patch.description ?? current.description ?? '',
					data: current.data,
					notation: current.notation,
				}),
			});
		} catch {
			// Best-effort; canvas save will reconcile later.
		}
	}

	function makeBpmnNode(
		entityKey: BpmnEntityType,
		position: { x: number; y: number },
		options: { id?: string; label?: string; entityId?: string } = {},
	): CanvasNode {
		const id = options.id
			?? ((typeof crypto !== 'undefined' && 'randomUUID' in crypto)
				? crypto.randomUUID()
				: `bpmn-${Math.random().toString(36).slice(2, 10)}`);
		// CanvasNodeData.entityType is typed narrowly as SimpleEntityType but
		// stores values from every notation in practice (UML/ArchiMate/C4/DoView/BPMN).
		// Cast through unknown matches the existing pattern elsewhere in the
		// codebase for cross-notation entityType assignments.
		const dims = BPMN_NODE_DIMENSIONS[entityKey] ?? { width: 200, height: 80 };
		return {
			id,
			type: entityKey,
			position,
			width: dims.width,
			height: dims.height,
			data: {
				label: options.label ?? humanLabel(entityKey),
				entityType: entityKey,
				entityId: options.entityId,
				notation: 'bpmn',
				data: { ...(BPMN_DEFAULT_DISCRIMINATORS[entityKey] ?? {}) },
			},
		} as unknown as CanvasNode;
	}

	function humanLabel(key: BpmnEntityType): string {
		return key
			.split('_')
			.map((p) => p.charAt(0).toUpperCase() + p.slice(1))
			.join(' ');
	}

	function findOpenPosition(): { x: number; y: number } {
		// Mirrors views/[id]/+page.svelte::findOpenPosition: a column-major
		// fallback when we don't have a drop position. Picks the first slot
		// not occupied by an existing node within a tolerance window.
		const cols = 4;
		const W = 220, H = 100, GAP = 30;
		const cellW = W + GAP, cellH = H + GAP;
		for (let i = 0; i < 200; i++) {
			const col = i % cols;
			const row = Math.floor(i / cols);
			const x = 60 + col * cellW;
			const y = 60 + row * cellH;
			const overlaps = canvasNodes.some((n) => {
				const nx = n.position.x;
				const ny = n.position.y;
				return Math.abs(nx - x) < W + GAP / 2 && Math.abs(ny - y) < H + GAP / 2;
			});
			if (!overlaps) return { x, y };
		}
		return { x: 60, y: 60 };
	}

	async function createNode(entityKey: BpmnEntityType, atPosition?: { x: number; y: number }) {
		// Events have a 6×10 trigger × position matrix — route through the
		// matrix picker so the user picks a meaningful variant rather than
		// taking the default. Skip for boundary events that came from the
		// context pad's append flow (handled separately).
		const isEvent = entityKey.startsWith('event_');
		if (isEvent && eventPickerContext === 'create') {
			pendingDropPosition = atPosition ?? findOpenPosition();
			eventPickerOpen = true;
			return;
		}
		const pos = atPosition ?? findOpenPosition();
		// v5.4.0 (#13): create the backing Iris Element first; abort if it fails.
		const label = humanLabel(entityKey);
		const element = await createBpmnElement(entityKey, label);
		if (!element) return;
		pushHistory();
		canvasNodes = [
			...canvasNodes,
			makeBpmnNode(entityKey, pos, { entityId: element.id, label }),
		];
		dirty();
	}

	function handlePaletteSelect(key: BpmnEntityType) {
		eventPickerContext = 'create';
		createNode(key);
	}

	function handleDropEntity(key: string, position: { x: number; y: number }) {
		eventPickerContext = 'create';
		createNode(key as BpmnEntityType, position);
	}

	async function handleEventVariant(variant: {
		entityType: BpmnEntityType;
		eventTrigger: string;
		eventDirection?: string;
		boundaryInterrupting?: boolean;
	}) {
		eventPickerOpen = false;
		const pos = pendingDropPosition ?? findOpenPosition();
		pendingDropPosition = null;
		// v5.4.0 (#13): backing Element first.
		const label = humanLabel(variant.entityType);
		const element = await createBpmnElement(variant.entityType, label);
		if (!element) return;
		const node = makeBpmnNode(variant.entityType, pos, { entityId: element.id, label });
		const data = (node.data as Record<string, unknown>);
		data.data = {
			...((data.data as Record<string, unknown> | undefined) ?? {}),
			eventTrigger: variant.eventTrigger,
			...(variant.eventDirection ? { eventDirection: variant.eventDirection } : {}),
			...(typeof variant.boundaryInterrupting === 'boolean'
				? { boundaryInterrupting: variant.boundaryInterrupting }
				: {}),
		};
		pushHistory();
		canvasNodes = [...canvasNodes, node];
		dirty();
	}

	// ────────────────────────────────────────────────────────────────────
	// CommandPalette: pick → create / append / replace
	// ────────────────────────────────────────────────────────────────────
	async function handleCmdPick(entry: BpmnEntityTypeInfo, mode: CommandMode) {
		if (mode === 'create') {
			eventPickerContext = 'create';
			await createNode(entry.key);
			return;
		}
		if (mode === 'append') {
			if (!selectedNode) return;
			eventPickerContext = 'create';
			const src = selectedNode;
			const offset = { x: src.position.x + 280, y: src.position.y };
			// v5.4.0 (#13): backing Element first.
			const label = humanLabel(entry.key);
			const element = await createBpmnElement(entry.key, label);
			if (!element) return;
			const newNode = makeBpmnNode(entry.key, offset, { entityId: element.id, label });
			pushHistory();
			canvasNodes = [...canvasNodes, newNode];
			canvasEdges = [
				...canvasEdges,
				{
					id: `e-${src.id}-${newNode.id}`,
					source: src.id,
					target: newNode.id,
					type: 'sequence_flow',
					data: { label: '' },
				} as CanvasEdge,
			];
			dirty();
			return;
		}
		if (mode === 'replace') {
			if (!selectedNode) return;
			pushHistory();
			// v5.4.0 (#13): mutate the existing Element's element_type rather
			// than creating a new one — the Element identity follows the node.
			const entityId = (selectedNode.data as { entityId?: string }).entityId;
			if (entityId) {
				updateBpmnElement(entityId, { element_type: entry.key });
			}
			canvasNodes = canvasNodes.map((n) => {
				if (n.id !== selectedNode.id) return n;
				return {
					...n,
					type: entry.key,
					data: {
						...n.data,
						entityType: entry.key,
						data: { ...(BPMN_DEFAULT_DISCRIMINATORS[entry.key] ?? {}) },
					},
				} as unknown as CanvasNode;
			});
			dirty();
		}
	}

	// ────────────────────────────────────────────────────────────────────
	// ContextPad action handler
	// ────────────────────────────────────────────────────────────────────
	function handleContextPadAction(action: string, nodeId: string) {
		const src = canvasNodes.find((n) => n.id === nodeId);
		if (!src) return;
		switch (action) {
			case 'append_task':
				appendBpmn(src, 'task');
				break;
			case 'append_gateway':
				appendBpmn(src, 'gateway');
				break;
			case 'append_end_event':
				appendBpmn(src, 'event_end');
				break;
			case 'change':
				cmdMode = 'replace';
				cmdOpen = true;
				break;
			case 'bring_forward':
				adjustZOrder(nodeId, 'forward');
				break;
			case 'send_backward':
				adjustZOrder(nodeId, 'backward');
				break;
			case 'delete':
				deleteNodeById(nodeId);
				break;
			case 'connect':
				// Existing canvas connect-mode is keyboard-driven; no-op for now.
				toastMessage = 'Drag from the right handle to connect.';
				break;
		}
	}

	/** v5.4.0 (#5): xyflow doesn't auto-set parentId on visual overlap, so
	 *  validateBpmn::lane_outside_pool fires even when the user has dragged
	 *  the lane visually inside a pool. After every drag, hit-test the
	 *  dragged node against pool bounds and set parentId accordingly. The
	 *  rule then walks `parentId` and clears the error.
	 *
	 *  Only fires on lanes (the only BPMN entity that has a "must-be-inside-
	 *  parent" constraint per BPMN 2.0). */
	function handleBpmnDragStop(nodeId: string, position: { x: number; y: number }) {
		const node = canvasNodes.find((n) => n.id === nodeId);
		if (!node) return;
		const entityType = node.data?.entityType as string | undefined;
		if (entityType !== 'lane') return;

		// Hit-test against every pool's rectangle.
		const dims = BPMN_NODE_DIMENSIONS.lane;
		const lx1 = position.x;
		const ly1 = position.y;
		const lx2 = position.x + dims.width;
		const ly2 = position.y + dims.height;

		const pool = canvasNodes.find((p) => {
			// Cast: data.entityType is typed as SimpleEntityType but stores BPMN values.
			if ((p.data?.entityType as string) !== 'pool') return false;
			const pd = BPMN_NODE_DIMENSIONS.pool;
			const pw = (p as { width?: number }).width ?? pd.width;
			const ph = (p as { height?: number }).height ?? pd.height;
			const px2 = p.position.x + pw;
			const py2 = p.position.y + ph;
			// Centre-point hit-test (lane is "inside" if its centre falls in the pool).
			const cx = (lx1 + lx2) / 2;
			const cy = (ly1 + ly2) / 2;
			return cx >= p.position.x && cx <= px2 && cy >= p.position.y && cy <= py2;
		});

		const newParentId = pool?.id ?? null;
		const currentParentId = (node as { parentId?: string | null }).parentId ?? null;
		if (newParentId === currentParentId) return; // no change

		pushHistory();
		canvasNodes = canvasNodes.map((n) =>
			n.id === nodeId ? ({ ...n, parentId: newParentId } as unknown as CanvasNode) : n,
		);
		dirty();
	}

	/** v5.4.0 (#3): adjust the z-index of a node so the user can stack
	 *  things (lane on pool, annotation on activity) and reorder. SvelteFlow
	 *  honours the optional `zIndex` field on Node. */
	function adjustZOrder(nodeId: string, direction: 'forward' | 'backward') {
		pushHistory();
		const others = canvasNodes
			.filter((n) => n.id !== nodeId)
			.map((n) => ((n as { zIndex?: number }).zIndex ?? 0));
		const max = others.length > 0 ? Math.max(...others) : 0;
		const min = others.length > 0 ? Math.min(...others) : 0;
		const next = direction === 'forward' ? max + 1 : min - 1;
		canvasNodes = canvasNodes.map((n) =>
			n.id === nodeId ? ({ ...n, zIndex: next } as unknown as CanvasNode) : n,
		);
		dirty();
	}

	async function appendBpmn(src: CanvasNode, key: BpmnEntityType) {
		// v5.4.0 (#13): backing Element first.
		const label = humanLabel(key);
		const element = await createBpmnElement(key, label);
		if (!element) return;
		const newNode = makeBpmnNode(key, { x: src.position.x + 280, y: src.position.y }, {
			entityId: element.id,
			label,
		});
		pushHistory();
		canvasNodes = [...canvasNodes, newNode];
		canvasEdges = [
			...canvasEdges,
			{
				id: `e-${src.id}-${newNode.id}`,
				source: src.id,
				target: newNode.id,
				type: 'sequence_flow',
				data: { label: '' },
			} as CanvasEdge,
		];
		dirty();
	}

	function deleteNodeById(nodeId: string) {
		pushHistory();
		canvasNodes = canvasNodes.filter((n) => n.id !== nodeId);
		canvasEdges = canvasEdges.filter((e) => e.source !== nodeId && e.target !== nodeId);
		dirty();
	}

	// ────────────────────────────────────────────────────────────────────
	// PropertyPanel: patch the selected node's data
	// ────────────────────────────────────────────────────────────────────
	function handlePropChange(id: string, patch: Record<string, unknown>) {
		pushHistory();
		const node = canvasNodes.find((n) => n.id === id);
		canvasNodes = canvasNodes.map((n) => {
			if (n.id !== id) return n;
			// Top-level fields the panel knows about: label, description.
			const next = { ...n, data: { ...n.data } };
			if ('label' in patch) (next.data as Record<string, unknown>).label = patch.label;
			if ('description' in patch) (next.data as Record<string, unknown>).description = patch.description;
			// Everything else is a discriminator field on the inner data.data record.
			const innerKeys = Object.keys(patch).filter((k) => k !== 'label' && k !== 'description');
			if (innerKeys.length > 0) {
				const inner = {
					...(((n.data as Record<string, unknown>).data as Record<string, unknown> | undefined) ?? {}),
				};
				for (const k of innerKeys) inner[k] = patch[k];
				(next.data as Record<string, unknown>).data = inner;
			}
			return next as CanvasNode;
		});
		dirty();

		// v5.4.0 (#13): keep the backing Iris Element in sync. Fire-and-forget;
		// canvas-level save reconciles failures. Only fires for label/description
		// — discriminator fields live entirely on the canvas node payload.
		const entityId = (node?.data as { entityId?: string } | undefined)?.entityId;
		if (entityId && ('label' in patch || 'description' in patch)) {
			updateBpmnElement(entityId, {
				name: 'label' in patch ? (patch.label as string | undefined) : undefined,
				description: 'description' in patch ? (patch.description as string | undefined) : undefined,
			});
		}
	}

	// ────────────────────────────────────────────────────────────────────
	// canConnect bridge
	// ────────────────────────────────────────────────────────────────────
	function handleBeforeConnect(c: Edge | Connection): boolean {
		const src = canvasNodes.find((n) => n.id === c.source);
		const tgt = canvasNodes.find((n) => n.id === c.target);
		if (!src || !tgt) return true;
		const verdict = canConnect({
			source: {
				id: src.id,
				type: (src.data?.entityType as string | undefined) ?? src.type,
				parentId: src.parentId ?? null,
				data: src.data as Record<string, unknown>,
			},
			target: {
				id: tgt.id,
				type: (tgt.data?.entityType as string | undefined) ?? tgt.type,
				parentId: tgt.parentId ?? null,
				data: tgt.data as Record<string, unknown>,
			},
			edgeType: 'sequence_flow',
			nodes: canvasNodes.map((n) => ({
				id: n.id,
				type: (n.data?.entityType as string | undefined) ?? n.type,
				parentId: n.parentId ?? null,
				data: n.data as Record<string, unknown>,
			})),
		});
		if (!verdict.allowed) {
			toastMessage = verdict.reason ?? 'Connection blocked';
		}
		return verdict.allowed;
	}

	// ────────────────────────────────────────────────────────────────────
	// ProblemsPanel: focus the offending node(s)
	// ────────────────────────────────────────────────────────────────────
	async function focusProblemNodes(elementIds: string[]) {
		if (elementIds.length === 0) return;
		selectedEditNodeId = elementIds[0];
		onnodeselect?.(elementIds[0]);
		await tick();
		// SvelteFlow's fitView would jump the viewport; the user-facing UX is
		// just to highlight via selection, which the existing canvas handles.
	}

	// ────────────────────────────────────────────────────────────────────
	// N / A / R hotkey relay (shell-level so it disables on non-BPMN routes)
	// ────────────────────────────────────────────────────────────────────
	function handleWindowKey(e: KeyboardEvent) {
		if (notation !== 'bpmn') return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		const k = e.key.toLowerCase();
		if (k === 'n') {
			e.preventDefault();
			cmdMode = 'create';
			cmdOpen = true;
		} else if (k === 'a') {
			if (!selectedNode) return;
			e.preventDefault();
			cmdMode = 'append';
			cmdOpen = true;
		} else if (k === 'r') {
			if (!selectedNode) return;
			e.preventDefault();
			cmdMode = 'replace';
			cmdOpen = true;
		}
	}

	const problemsData = $derived({
		nodes: canvasNodes.map((n) => ({
			id: n.id,
			type: (n.data?.entityType as string | undefined) ?? n.type,
			parentId: n.parentId ?? null,
			data: n.data as Record<string, unknown>,
		})),
		edges: canvasEdges.map((e) => ({
			id: e.id,
			source: e.source,
			target: e.target,
			type: e.type,
			data: e.data as Record<string, unknown>,
		})),
	});
</script>

<svelte:window onkeydown={handleWindowKey} />

<div class="bpmn-shell">
	<div class="bpmn-shell__row">
		<aside class="bpmn-shell__palette" aria-label="BPMN palette">
			<BpmnPalette onselect={handlePaletteSelect} />
		</aside>
		<div class="bpmn-shell__canvas">
			<UnifiedCanvas
				{notation}
				{preferredThemeId}
				bind:nodes={canvasNodes}
				bind:edges={canvasEdges}
				onbeforeconnect={handleBeforeConnect}
				ondropentity={handleDropEntity}
				oncontextpadaction={handleContextPadAction}
				onnodedragstop={handleBpmnDragStop}
				onnodeselect={(id) => { selectedEditNodeId = id; onnodeselect?.(id); }}
				onedgeselect={(id) => onedgeselect?.(id)}
			/>
		</div>
		<aside class="bpmn-shell__props" aria-label="BPMN property panel">
			<PropertyPanel selection={propertySelection} onchange={handlePropChange} />
		</aside>
	</div>
	<div class="bpmn-shell__problems">
		<ProblemsPanel data={problemsData} onfocus={focusProblemNodes} />
	</div>
</div>

<CommandPalette
	bind:open={cmdOpen}
	bind:mode={cmdMode}
	bindShortcuts={false}
	onpick={handleCmdPick}
	onclose={() => (cmdOpen = false)}
/>

<EventMatrixPicker
	bind:open={eventPickerOpen}
	onpick={handleEventVariant}
	onclose={() => { eventPickerOpen = false; pendingDropPosition = null; }}
/>

<BpmnToast bind:message={toastMessage} />

<style>
	.bpmn-shell {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		gap: 8px;
		height: calc(100vh - 230px);
	}
	.bpmn-shell__row {
		display: grid;
		grid-template-columns: 220px 1fr 280px;
		gap: 8px;
		flex: 1;
		min-height: 0;
		min-width: 0;
	}
	.bpmn-shell__palette,
	.bpmn-shell__props {
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		border: 1px solid var(--color-border, #d4d4d4);
		border-radius: 6px;
		background: var(--color-surface, #fff);
	}
	.bpmn-shell__canvas {
		min-width: 0;
		min-height: 0;
		border: 1px solid var(--color-border, #d4d4d4);
		border-radius: 6px;
		overflow: hidden;
	}
	.bpmn-shell__problems {
		min-height: 80px;
		max-height: 200px;
		/* v5.4.0 (#1): the inner ProblemsPanel list scrolls itself; the
		   wrapper used to clip that scroll, sending overflow up to the page. */
		overflow-y: auto;
		border: 1px solid var(--color-border, #d4d4d4);
		border-radius: 6px;
		background: var(--color-surface, #fff);
	}
</style>
