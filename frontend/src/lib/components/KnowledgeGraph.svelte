<script lang="ts">
	import { onMount } from 'svelte';
	import type { GraphNode, GraphEdge, GraphSettings } from '$lib/types/api';
	import { getNodeTypeColor, NODE_TYPE_LABELS } from '$lib/utils/graphColors';

	interface Props {
		nodes: GraphNode[];
		edges: GraphEdge[];
		settings: GraphSettings;
		onNodeClick?: (nodeId: string, nodeType: string) => void;
		onNodeHover?: (nodeId: string | null) => void;
		highlightNodeId?: string | null;
	}

	let { nodes, edges, settings, onNodeClick, onNodeHover, highlightNodeId = null }: Props = $props();

	let container: HTMLDivElement | undefined = $state();
	let graph: any = $state(null);

	// Track previous node count to detect data loads that need a re-fit
	let prevNodeCount = 0;

	// Focus mode: fade unrelated nodes when hovering on canvas
	let canvasHoverId: string | null = null;
	let focusNeighbors: Set<string> | null = null;
	let focusTimer: ReturnType<typeof setTimeout> | undefined;
	let focusActive = false;
	let focusFade = 1.0; // 1 = fully visible, 0.1 = faded

	// Legend: only show node types present in data
	let presentNodeTypes = $derived(new Set(nodes.map((n) => n.node_type)));
	let legend = $derived(
		Object.entries(NODE_TYPE_LABELS)
			.filter(([key]) => settings.nodes[key] && presentNodeTypes.has(key))
			.map(([key, label]) => ({ type: label, color: getNodeTypeColor(key) }))
	);

	// Filter nodes and edges based on settings
	let filteredNodes = $derived.by(() => {
		return nodes.filter((n) => settings.nodes[n.node_type] !== false);
	});
	let filteredEdges = $derived.by(() => {
		const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
		return edges.filter((e) =>
			settings.edges[e.edge_type] !== false &&
			visibleNodeIds.has(e.source as string) &&
			visibleNodeIds.has(e.target as string)
		);
	});

	function readThemeColors() {
		const style = getComputedStyle(document.documentElement);
		return {
			bg: style.getPropertyValue('--color-bg').trim() || '#ffffff',
			fg: style.getPropertyValue('--color-fg').trim() || '#1a1a1a',
			muted: style.getPropertyValue('--color-muted').trim() || '#6b7280',
		};
	}

	function updateGraph(graphInstance: any) {
		if (!graphInstance || !container) return;
		const colors = readThemeColors();

		const { width, height } = container.getBoundingClientRect();
		if (width > 0) graphInstance.width(width);
		if (height > 0) graphInstance.height(height);

		const nodeData = filteredNodes.map((n) => ({
			...n,
			_color: getNodeTypeColor(n.node_type),
		}));

		graphInstance
			.backgroundColor(colors.bg)
			.nodeColor((n: any) => {
				if (focusActive && focusNeighbors && !focusNeighbors.has(n.id)) {
					const alpha = Math.round(focusFade * 255).toString(16).padStart(2, '0');
					return n._color + alpha;
				}
				return n._color;
			})
			.nodeLabel(() => '') // labels drawn in onRenderFramePost
			.nodeRelSize(3)
			.nodeVal((n: any) => {
				if (n.node_type === 'collection') return 160;
				if (n.node_type === 'set') return 55;
				if (n.node_type === 'package') return 40;
				if (n.node_type === 'diagram') return 12;
				return 0.5;
			})
			.linkColor((l: any) => {
				if (focusActive && focusNeighbors) {
					const src = typeof l.source === 'object' ? l.source.id : l.source;
					const tgt = typeof l.target === 'object' ? l.target.id : l.target;
					if (!focusNeighbors.has(src) || !focusNeighbors.has(tgt)) {
						const alpha = Math.round(focusFade * 255).toString(16).padStart(2, '0');
						return colors.muted + alpha;
					}
				}
				if (l.edge_type === 'hierarchy' || l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package'
					|| l.edge_type === 'collection_membership' || l.edge_type === 'set_membership') {
					return colors.muted + '80';
				}
				return colors.muted;
			})
			.linkDirectionalArrowLength((l: any) => l.edge_type === 'hierarchy' ? 0 : 6)
			.linkDirectionalArrowColor(() => colors.muted)
			.linkLabel(() => '')
			.linkWidth((l: any) => {
				if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') return 0.5;
				if (l.edge_type === 'hierarchy' || l.edge_type === 'collection_membership' || l.edge_type === 'set_membership') return 0.8;
				return 1.5;
			})
			.linkLineDash((l: any) => {
				if (l.edge_type === 'diagram_link') return [4, 2];
				if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') return [2, 2];
				return null;
			})
			.graphData({
				nodes: nodeData,
				links: filteredEdges.map((e) => ({ ...e })),
			});
	}

	onMount(() => {
		if (!container) return;

		let ro: ResizeObserver | undefined;
		let mo: MutationObserver | undefined;
		let breatheInterval: ReturnType<typeof setInterval> | undefined;
		let destroyed = false;

		(async () => {
			const ForceGraph = (await import('force-graph')).default;
			if (destroyed || !container) return;

			const colors = readThemeColors();
			const rect = container.getBoundingClientRect();

			const PACKAGE_ZOOM = 0.5;
			const DIAGRAM_ZOOM = 1.5;
			const ELEMENT_ZOOM = 3.0;
			const MAX_PER_TIER = 20;

			let wasDragged = false;

			const fg = new ForceGraph(container)
				.width(rect.width || 300)
				.height(rect.height || 450)
				.backgroundColor(colors.bg)
				.nodeColor(() => colors.fg)
				.linkColor(() => colors.muted)
				.linkWidth(1.5)
				.onNodeDrag(() => { wasDragged = true; })
				.onNodeDragEnd(() => { setTimeout(() => { wasDragged = false; }, 50); })
				.onNodeClick((n: any) => {
					if (wasDragged) return;
					if (onNodeClick && n.id) onNodeClick(n.id, n.node_type);
				})
				.onNodeHover((n: any) => {
					onNodeHover?.(n ? n.id : null);
					clearTimeout(focusTimer);
					if (n) {
						canvasHoverId = n.id;
						const neighbors = new Set<string>([n.id]);
						const graphData = fg.graphData();
						for (const l of graphData.links) {
							const src = typeof l.source === 'object' ? l.source.id : l.source;
							const tgt = typeof l.target === 'object' ? l.target.id : l.target;
							if (src === n.id) neighbors.add(tgt);
							if (tgt === n.id) neighbors.add(src);
						}
						focusNeighbors = neighbors;
						focusTimer = setTimeout(() => { focusActive = true; }, 400);
					} else {
						canvasHoverId = null;
						focusNeighbors = null;
						focusActive = false;
						focusFade = 1.0;
					}
				})
				.showPointerCursor(() => true)
				.d3AlphaMin(0)
				.d3AlphaDecay(0.02)
				.d3VelocityDecay(0.3)
				.onRenderFramePost((ctx: CanvasRenderingContext2D, globalScale: number) => {
					// Drive fade animation each frame
					if (focusActive && focusFade > 0.1) {
						focusFade = Math.max(focusFade - 0.04, 0.1);
					}

					const hlId = highlightNodeId;
					const graphData = fg.graphData();
					if (!graphData.nodes.length) return;

					const themeColors = readThemeColors();

					// Viewport bounds in graph coordinates
					const { x: cx, y: cy } = fg.centerAt();
					const w = fg.width() / globalScale;
					const h = fg.height() / globalScale;
					const left = cx - w / 2;
					const right = cx + w / 2;
					const top = cy - h / 2;
					const bottom = cy + h / 2;

					// Find visible nodes
					const visible = graphData.nodes.filter((n: any) =>
						n.x != null && n.x >= left && n.x <= right && n.y >= top && n.y <= bottom
					);

					// Highlighted node: always draw ring + label
					if (hlId) {
						const target = graphData.nodes.find((n: any) => n.id === hlId);
						if (target && target.x != null) {
							const r = Math.sqrt(Math.max(target.__val || 1, 1)) * fg.nodeRelSize() + 2;
							ctx.beginPath();
							ctx.arc(target.x, target.y, r + 3, 0, 2 * Math.PI);
							ctx.strokeStyle = '#ef4444';
							ctx.lineWidth = 2 / globalScale;
							ctx.stroke();
							const fontSize = 12 / globalScale;
							ctx.font = `bold ${fontSize}px sans-serif`;
							ctx.textAlign = 'center';
							ctx.textBaseline = 'bottom';
							ctx.fillStyle = themeColors.fg;
							ctx.fillText(target.name || '', target.x, target.y - r - 4 / globalScale);
						}
					}

					// Progressive labels: packages first, then diagrams, then elements
					const labelled = new Set(hlId ? [hlId] : []);
					ctx.textAlign = 'center';
					ctx.textBaseline = 'bottom';

					const tiers: { type: string; minZoom: number; bold: boolean; size: number }[] = [
						{ type: 'collection', minZoom: 0, bold: true, size: 22 },
						{ type: 'set', minZoom: 0, bold: true, size: 16 },
						{ type: 'package', minZoom: PACKAGE_ZOOM, bold: true, size: 12 },
						{ type: 'diagram', minZoom: DIAGRAM_ZOOM, bold: false, size: 9 },
						{ type: 'element', minZoom: ELEMENT_ZOOM, bold: false, size: 7 },
					];

					for (const tier of tiers) {
						if (globalScale < tier.minZoom) continue;
						const fontSize = tier.size / globalScale;
						ctx.font = `${tier.bold ? 'bold ' : ''}${fontSize}px sans-serif`;

						const tierNodes = visible
							.filter((n: any) => n.node_type === tier.type && !labelled.has(n.id))
							.sort((a: any, b: any) => (b.relationship_count || 0) - (a.relationship_count || 0))
							.slice(0, MAX_PER_TIER);

						for (const n of tierNodes) {
							const isFaded = focusActive && focusNeighbors && !focusNeighbors.has(n.id);
							ctx.globalAlpha = isFaded ? focusFade : 1.0;
							ctx.fillStyle = themeColors.fg;
							const r = Math.sqrt(Math.max(n.__val || 1, 1)) * fg.nodeRelSize() + 2;
							ctx.fillText(n.name || '', n.x, n.y - r - 2 / globalScale);
							labelled.add(n.id);
						}
						ctx.globalAlpha = 1.0;
					}
				});

			graph = fg;

			// Shorter link distances for containment edges
			const linkForce = fg.d3Force('link');
			if (linkForce) {
				linkForce.distance((l: any) => {
					if (l.edge_type === 'collection_membership') return 40;
					if (l.edge_type === 'set_membership') return 30;
					if (l.edge_type === 'hierarchy') return 30;
					if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') return 40;
					return 60;
				});
			}

			// After initial layout settles, keep a tiny alpha target so nodes drift gently
			breatheInterval = setTimeout(() => {
				if (!destroyed && fg && typeof fg.d3AlphaTarget === 'function') {
					const engine = fg.d3Force('charge');
					if (engine?.strength) engine.strength(-30);
					fg.d3AlphaTarget(0.02);
				}
			}, 3000) as unknown as ReturnType<typeof setInterval>;

			ro = new ResizeObserver((entries) => {
				for (const entry of entries) {
					const { width, height } = entry.contentRect;
					if (width > 0 && height > 0) {
						fg.width(width).height(height);
					}
				}
			});
			ro.observe(container);

			mo = new MutationObserver(() => {
				updateGraph(fg);
			});
			mo.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ['class'],
			});

			updateGraph(fg);

			// Centre the graph once the simulation settles
			setTimeout(() => {
				if (!destroyed) fg.zoomToFit(400, 40);
			}, 1500);
		})();

		return () => {
			destroyed = true;
			clearTimeout(breatheInterval);
			clearTimeout(focusTimer);
			mo?.disconnect();
			ro?.disconnect();
			if (graph) graph._destructor();
		};
	});

	// Re-render when data or settings change
	$effect(() => {
		const nodeCount = filteredNodes.length;
		void filteredEdges.length;
		if (graph) {
			updateGraph(graph);
			// Re-fit when data arrives or changes significantly
			if (nodeCount !== prevNodeCount && nodeCount > 0) {
				prevNodeCount = nodeCount;
				setTimeout(() => graph.zoomToFit(400, 40), 1500);
			}
		}
	});

	// Zoom to highlighted node (visuals handled in onRenderFramePost)
	$effect(() => {
		if (!graph || !highlightNodeId) return;
		const id = highlightNodeId;
		const graphData = graph.graphData();
		const target = graphData.nodes.find((n: any) => n.id === id);
		if (target && target.x != null && target.y != null) {
			graph.centerAt(target.x, target.y, 400);
			graph.zoom(3, 400);
		}
	});
</script>

<div class="knowledge-graph-wrapper">
	<!-- Legend -->
	{#if legend.length > 0}
		<div
			style="position: absolute; top: 8px; right: 8px; z-index: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); font-size: 0.75rem; display: flex; flex-wrap: wrap; gap: 8px; max-width: 300px"
		>
			{#each legend as entry}
				<span class="flex items-center gap-1">
					<span
						style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {entry.color}"
					></span>
					<span style="color: var(--color-muted)">{entry.type}</span>
				</span>
			{/each}
		</div>
	{/if}

	<!-- Reset zoom button -->
	<button
		onclick={() => { if (graph) graph.zoomToFit(400, 40); }}
		style="position: absolute; bottom: 8px; right: 8px; z-index: 1; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); font-size: 0.7rem; cursor: pointer"
		title="Reset zoom to fit all nodes"
	>
		Fit
	</button>

	<!-- Graph container -->
	<div
		bind:this={container}
		aria-label="Knowledge graph showing entity relationships"
		role="img"
		class="knowledge-graph-canvas"
	></div>
</div>

<style>
	.knowledge-graph-wrapper {
		position: relative;
		width: 100%;
		overflow: hidden;
		border-radius: 8px;
		border: 1px solid var(--color-border);
		flex: 1 1 0;
		min-height: 300px;
	}
	.knowledge-graph-canvas {
		width: 100%;
		height: 100%;
		overflow: hidden;
	}
	.knowledge-graph-canvas :global(.force-graph-container),
	.knowledge-graph-canvas :global(canvas) {
		width: 100% !important;
		max-width: 100% !important;
		display: block;
	}
</style>
