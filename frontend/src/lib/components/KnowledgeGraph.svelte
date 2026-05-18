<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import type { GraphNode, GraphEdge, GraphSettings } from '$lib/types/api';
	import { getNodeTypeColor, NODE_TYPE_LABELS } from '$lib/utils/graphColors';
	import KnowledgeGraphSettings from '$lib/components/KnowledgeGraphSettings.svelte';

	interface Props {
		nodes: GraphNode[];
		edges: GraphEdge[];
		settings: GraphSettings;
		onSettingsChange?: (settings: GraphSettings) => void;
		onNodeClick?: (nodeId: string, nodeType: string) => void;
		onNodeHover?: (nodeId: string | null) => void;
		highlightNodeId?: string | null;
		isAdmin?: boolean;
		onSaveDefault?: (settings: GraphSettings) => void | Promise<void>;
		onResetToDefaults?: (tab: 'nodes' | 'relationships' | 'display') => void;
	}

	let { nodes, edges, settings, onSettingsChange, onNodeClick, onNodeHover, highlightNodeId = null, isAdmin = false, onSaveDefault, onResetToDefaults }: Props = $props();

	let showSettings = $state(false);

	let container: HTMLDivElement | undefined = $state();
	let graph: any = $state(null);
	let maximised = $state(false);

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
	// Diagrams that have a hierarchy parent (used to suppress redundant set→diagram edges)
	let diagramsWithParent = $derived(new Set(
		edges.filter((e) => e.edge_type === 'hierarchy').map((e) => e.target as string)
	));
	let filteredEdges = $derived.by(() => {
		const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
		// Note: the `direct_diagram_links` toggle is handled via force-graph's
		// linkVisibility (see setupForceGraph) rather than by filtering here.
		// Removing set→diagram edges from the simulation would take away the
		// link force (distance 120 px) that pulls diagrams outward into their
		// "petal" around the set node, which is what gives each set its
		// visible cluster and — combined with the inner-layer repulsion from
		// SPEC-119-A — the galaxy effect across collections (ADR-119 /
		// SPEC-119-A follow-up).
		return edges.filter((e) =>
			settings.edges[e.edge_type] !== false &&
			visibleNodeIds.has(e.source as string) &&
			visibleNodeIds.has(e.target as string)
		);
	});

	// Hierarchy rank order (low to high)
	const RANK_ORDER = ['element', 'diagram', 'package', 'set', 'collection'];
	const BASE_SIZES: Record<string, number> = { collection: 160, set: 55, package: 40, diagram: 12, element: 0.5 };

	function _computeNodeSize(nodeType: string, s: GraphSettings): number {
		const contrast = s.size_contrast ?? 1.0;
		if (contrast === 1.0) return BASE_SIZES[nodeType] ?? 1;

		const visible = RANK_ORDER.filter((t) => s.nodes[t] !== false);
		const rank = visible.indexOf(nodeType);
		if (rank < 0) return BASE_SIZES[nodeType] ?? 1;

		const n = visible.length;
		// Position from -1 (lowest) to +1 (highest)
		const pos = n > 1 ? (2 * rank) / (n - 1) - 1 : 0;
		const base = BASE_SIZES[nodeType] ?? 1;
		// Scale: at contrast=0 all uniform, at contrast=1 base sizes, above=amplified
		// Spread per unit of contrast beyond 1.0
		const spread = 40;
		return Math.max(0.5, base + pos * spread * (contrast - 1.0));
	}

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
				return _computeNodeSize(n.node_type, settings);
			})
			.linkVisibility((l: any) => {
				// Hide set→diagram edges visually when the user turns off
				// "Direct diagram links" in the settings panel, BUT keep them
				// in the force simulation. The set→diagram link force
				// (distance 120 px) is what bloom-separates diagrams into
				// per-set petals, so removing it from the force calc
				// compresses every cluster toward the graph centre and kills
				// the galaxy effect. Purely-visual hiding here lets users
				// de-clutter without breaking the layout (ADR-119 /
				// SPEC-119-A).
				if (settings.edges['direct_diagram_links'] === false
					&& l.edge_type === 'set_membership'
					&& diagramsWithParent.has(
						typeof l.target === 'object' ? l.target.id : l.target,
					)
				) {
					return false;
				}
				return true;
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

		// Reconfigure forces when settings change
		const chargeForce = graphInstance.d3Force('charge');
		if (chargeForce?.strength) {
			const spacing = settings.node_spacing ?? 1.0;
			chargeForce.strength((n: any) => {
				const bases: Record<string, number> = { collection: -300, set: -200, package: -80, diagram: -40 };
				return (bases[n.node_type] ?? -30) * spacing;
			});
		}
		const linkForce = graphInstance.d3Force('link');
		if (linkForce?.distance) {
			const ll = settings.link_length ?? 1.0;
			linkForce.distance((l: any) => {
				const tgt = typeof l.target === 'object' ? l.target : null;
				const tgtType = tgt?.node_type;
				let base = 60;
				if (l.edge_type === 'collection_membership') base = 200;
				else if (l.edge_type === 'set_membership') {
					if (tgtType === 'package') base = 60;
					else if (tgtType === 'diagram') base = 120;
					else base = 80;
				} else if (l.edge_type === 'hierarchy') {
					base = tgtType === 'package' ? 25 : 40;
				} else if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') base = 40;
				return base * ll;
			});
		}
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
			const MAX_PER_TIER = settings.label_density ?? 10;

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
							ctx.textBaseline = 'middle';
							ctx.fillStyle = themeColors.fg;
							ctx.fillText(target.name || '', target.x, target.y);
						}
					}

					// Progressive labels with overlap suppression. Higher-
					// precedence tiers (collection > set > package > diagram >
					// element) suppress lower-precedence labels that would
					// overlap, AND same-tier labels suppress each other —
					// within a tier, nodes are drawn sorted by
					// relationship_count descending, so higher-relationship
					// labels win the space when two would collide.
					const labelled = new Set(hlId ? [hlId] : []);
					const drawnBoxes: { x: number; y: number; w: number; h: number; tier: number }[] = [];
					ctx.textAlign = 'center';
					ctx.textBaseline = 'middle';

					const tiers: { type: string; minZoom: number; bold: boolean; size: number }[] = [
						{ type: 'collection', minZoom: 0, bold: true, size: 22 },
						{ type: 'set', minZoom: 0, bold: true, size: 16 },
						{ type: 'package', minZoom: 0.3, bold: true, size: 12 },
						{ type: 'diagram', minZoom: 2.0, bold: false, size: 9 },
						{ type: 'element', minZoom: ELEMENT_ZOOM, bold: false, size: 7 },
					];

					for (let ti = 0; ti < tiers.length; ti++) {
						const tier = tiers[ti];
						if (globalScale < tier.minZoom) continue;
						const fontSize = tier.size / globalScale;
						ctx.font = `${tier.bold ? 'bold ' : ''}${fontSize}px sans-serif`;

						const tierNodes = visible
							.filter((n: any) => n.node_type === tier.type && !labelled.has(n.id))
							.sort((a: any, b: any) => (b.relationship_count || 0) - (a.relationship_count || 0))
							.slice(0, MAX_PER_TIER);

						for (const n of tierNodes) {
							const text = n.name || '';
							const tw = ctx.measureText(text).width;
							const th = fontSize;
							const lx = n.x - tw / 2;
							const ly = n.y - th / 2;

							// Check overlap against every already-drawn label —
							// both higher-precedence tiers AND earlier-drawn
							// same-tier labels. Same-tier draw order is
							// highest-relationship-first (see .sort above) so
							// the most-connected label keeps its space.
							const overlaps = drawnBoxes.some((b) =>
								lx < b.x + b.w && lx + tw > b.x &&
								ly < b.y + b.h && ly + th > b.y
							);
							if (overlaps) continue;

							const isFaded = focusActive && focusNeighbors && !focusNeighbors.has(n.id);
							ctx.globalAlpha = isFaded ? focusFade : 1.0;
							ctx.fillStyle = themeColors.fg;
							ctx.fillText(text, n.x, n.y);
							drawnBoxes.push({ x: lx, y: ly, w: tw, h: th, tier: ti });
							labelled.add(n.id);
						}
						ctx.globalAlpha = 1.0;
					}
				});

			graph = fg;
			// Debug hook: expose the force-graph instance for Playwright probes and
			// the multi-collection spread-slider regression test (SPEC-118-A).
			// Inlined at build time via VITE_IRIS_DEBUG=1; always absent in production.
			if (import.meta.env.VITE_IRIS_DEBUG === '1') {
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				(window as any).__irisGraph = fg;
			}

			// Custom cluster force: two-level hierarchical clustering.
			// Level 1: collection clusters — pushes entire collections apart
			// Level 2: set clusters — keeps each set's subtree cohesive and separated
			fg.d3Force('cluster', (alpha: number) => {
				const spread = settings.node_spacing ?? 1.0;
				const graphData = fg.graphData();
				if (!graphData.nodes.length) return;

				// Build node→set, set→collection, and child→parent mappings from edges
				const nodeSetMap = new Map<string, string>();
				const setCollectionMap = new Map<string, string>();
				const childParentMap = new Map<string, string>(); // hierarchy: target→source
				for (const l of graphData.links) {
					const src = typeof l.source === 'object' ? l.source.id : l.source;
					const tgt = typeof l.target === 'object' ? l.target.id : l.target;
					if (l.edge_type === 'set_membership') nodeSetMap.set(tgt, src);
					if (l.edge_type === 'collection_membership') setCollectionMap.set(tgt, src);
					if (l.edge_type === 'hierarchy') childParentMap.set(tgt, src);
				}
				// Walk hierarchy so children inherit the set
				for (const [tgt, src] of childParentMap) {
					const parentSet = nodeSetMap.get(src);
					if (parentSet && !nodeSetMap.has(tgt)) nodeSetMap.set(tgt, parentSet);
				}

				// Resolve each node's collection (node→set→collection). Sets with no
				// collection (e.g. the "default" set) get a synthetic __orphan_<sid>
				// group so the collection-layer bidirectional force still binds them
				// — otherwise only charge repulsion acts on orphan nodes and they
				// drift outward unboundedly as spread rises (ADR-118, SPEC-118-A).
				const nodeCollectionMap = new Map<string, string>();
				for (const n of graphData.nodes) {
					if (n.node_type === 'collection') { nodeCollectionMap.set(n.id, n.id); continue; }
					const sid = nodeSetMap.get(n.id) || (n.node_type === 'set' ? n.id : null);
					if (!sid) continue;
					const cid = setCollectionMap.get(sid);
					nodeCollectionMap.set(n.id, cid ?? `__orphan_${sid}`);
				}

				// Helper: compute centroids for a grouping
				type Centroid = { x: number; y: number; count: number };
				function computeCentroids(nodeGroupMap: Map<string, string>) {
					const centroids = new Map<string, Centroid>();
					for (const n of graphData.nodes) {
						const gid = nodeGroupMap.get(n.id);
						if (!gid) continue;
						let c = centroids.get(gid);
						if (!c) { c = { x: 0, y: 0, count: 0 }; centroids.set(gid, c); }
						c.x += n.x || 0;
						c.y += n.y || 0;
						c.count++;
					}
					for (const c of centroids.values()) {
						if (c.count > 0) { c.x /= c.count; c.y /= c.count; }
					}
					return centroids;
				}

				// Per-layer separation force (SPEC-118-A + SPEC-119-A). Two
				// modes share the pair loop, gating predicate, and unit-vector
				// application — only the push scalar differs:
				//   • 'bidirectional' (SPEC-118-A): target-distance force with
				//     -0.2 pull-back floor past target. Used at the COLLECTION
				//     layer — top-level compactness is a deliberate design
				//     choice and the pull-back anchors the orphan-set
				//     __orphan_<sid> contract.
				//   • 'inverseSq' (SPEC-119-A): self-decaying 1/dist² pure
				//     repulsion with no fixed target. Used at the SET and
				//     ROOT-PACKAGE layers because cluster equilibrium radius
				//     is data-driven — charge balance decides the spacing
				//     and the force self-decays at long range. Removes the
				//     density assumption baked into a fixed target distance;
				//     works whether a set has 5 members or 500.
				// Optional sameOuterGroup predicate gates cross-group firing
				// (cross-collection skipped above the collection layer).
				function applySeparation(
					centroids: Map<string, Centroid>,
					nodeGroupMap: Map<string, string>,
					strength: number,
					targetDist: number,
					mode: 'bidirectional' | 'inverseSq',
					sameOuterGroup?: (aId: string, bId: string) => boolean,
				) {
					const entries = [...centroids.entries()];
					for (let i = 0; i < entries.length; i++) {
						for (let j = i + 1; j < entries.length; j++) {
							const aId = entries[i][0];
							const bId = entries[j][0];
							if (sameOuterGroup && !sameOuterGroup(aId, bId)) continue;
							const a = entries[i][1];
							const b = entries[j][1];
							const dx = a.x - b.x;
							const dy = a.y - b.y;
							const dist = Math.sqrt(dx * dx + dy * dy) || 1;
							let push: number;
							if (mode === 'bidirectional') {
								const rawOverlap = (targetDist - dist) / targetDist;
								const overlap = Math.max(-0.2, Math.min(1, rawOverlap));
								push = strength * alpha * overlap;
							} else {
								push = (strength * alpha) / (dist * dist);
							}
							const fx = (dx / dist) * push;
							const fy = (dy / dist) * push;
							for (const n of graphData.nodes) {
								const gid = nodeGroupMap.get(n.id);
								if (gid === aId) { n.vx += fx; n.vy += fy; }
								else if (gid === bId) { n.vx -= fx; n.vy -= fy; }
							}
						}
					}
				}

				// Build set-level node map (includes set nodes themselves)
				const nodeSetFull = new Map<string, string>();
				for (const n of graphData.nodes) {
					const sid = nodeSetMap.get(n.id) || (n.node_type === 'set' ? n.id : null);
					if (sid) nodeSetFull.set(n.id, sid);
				}

				// Resolve each node's root package (walk up hierarchy to the top)
				function findRoot(id: string): string {
					let cur = id;
					const visited = new Set<string>();
					while (childParentMap.has(cur) && !visited.has(cur)) {
						visited.add(cur);
						cur = childParentMap.get(cur)!;
					}
					return cur;
				}
				const hierarchyNodes = new Set<string>();
				for (const [child, parent] of childParentMap) {
					hierarchyNodes.add(child);
					hierarchyNodes.add(parent);
				}
				const nodeRootPkgMap = new Map<string, string>();
				for (const n of graphData.nodes) {
					if (n.node_type === 'collection' || n.node_type === 'set') continue;
					if (hierarchyNodes.has(n.id)) {
						nodeRootPkgMap.set(n.id, findRoot(n.id));
					}
				}

				// Layer radii for per-galaxy radial ordering (SPEC-120-A).
				// Each node is pulled toward its layer's target radius from
				// its governing collection centroid, enforcing
				// collection < set < package < diagram < element as a radial
				// invariant rather than an emergent property of link tuning.
				// Constants are a simple arithmetic progression; global
				// scaling is via link_length × node_spacing so the existing
				// sliders keep full control of the visible layout.
				const LAYER_RADIUS: Record<string, number> = {
					collection: 0,
					set: 120,
					package: 240,
					diagram: 360,
					element: 480,
				};
				const linkLen = settings.link_length ?? 1.0;
				const radiusScale = linkLen * spread;
				const R_TOTAL = 480 * radiusScale;

				// 1. Collection separation — bidirectional, but with a
				// radius-aware target distance (2 × R_total + padding) so
				// inter-galaxy spacing tracks actual galaxy extent rather
				// than a fixed constant. Replaces SPEC-119-A's centroid-only
				// fixed-target call. Pull-back (-0.2 floor inside
				// applySeparation) anchors the orphan-set __orphan_<sid>
				// contract.
				const colCentroids =
					nodeCollectionMap.size > 0
						? computeCentroids(nodeCollectionMap)
						: new Map<string, Centroid>();
				if (colCentroids.size > 1) {
					const padding = 100 * radiusScale;
					const targetDist = 2 * R_TOTAL + padding;
					applySeparation(
						colCentroids, nodeCollectionMap,
						80, targetDist, 'bidirectional',
					);
				}

				// 2. Per-galaxy radial layer force (SPEC-120-A).
				// Each node is pulled toward its layer's target radius from
				// its own collection centroid. This enforces the hierarchy
				// ordering directionally — packages cannot visually escape
				// their children because they are mass-pulled to a smaller
				// target radius than diagrams. Intra-layer angular position
				// is still shaped by link + charge + cohesion.
				const radialStrength = 0.15 * alpha;
				for (const n of graphData.nodes) {
					const cid = nodeCollectionMap.get(n.id);
					if (!cid) continue;
					const targetR = (LAYER_RADIUS[n.node_type] ?? 0) * radiusScale;
					if (targetR === 0) continue;
					const col = colCentroids.get(cid);
					if (!col) continue;
					const dx = (n.x || 0) - col.x;
					const dy = (n.y || 0) - col.y;
					const r = Math.sqrt(dx * dx + dy * dy) || 1;
					const delta = targetR - r;
					const push = radialStrength * delta;
					n.vx += (dx / r) * push;
					n.vy += (dy / r) * push;
				}

				// 3. Cohesion: pull each node toward its finest-level cluster
				// centroid. Flat (not inverse-spread) — keeps cohesion stable
				// as spread grows. Unchanged from SPEC-119-A. Provides the
				// angular pull that clusters a set's children together; the
				// radial force (above) supplies the perpendicular radius
				// constraint.
				const setCentroids = computeCentroids(nodeSetFull);
				const pkgCentroids: Map<string, Centroid> | null =
					nodeRootPkgMap.size > 0 ? computeCentroids(nodeRootPkgMap) : null;
				const cohesion = 0.03 * alpha;
				for (const n of graphData.nodes) {
					const rpid = nodeRootPkgMap.get(n.id);
					if (rpid && pkgCentroids && pkgCentroids.size > 1) {
						const c = pkgCentroids.get(rpid);
						if (c) {
							n.vx += (c.x - (n.x || 0)) * cohesion;
							n.vy += (c.y - (n.y || 0)) * cohesion;
							continue;
						}
					}
					const sid = nodeSetFull.get(n.id);
					if (!sid) continue;
					const c = setCentroids.get(sid);
					if (!c) continue;
					n.vx += (c.x - (n.x || 0)) * cohesion;
					n.vy += (c.y - (n.y || 0)) * cohesion;
				}
			});

			// After initial layout settles, keep a tiny alpha target so nodes drift gently
			breatheInterval = setTimeout(() => {
				if (!destroyed && fg && typeof fg.d3AlphaTarget === 'function') {
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

	// Stable keys for visibility toggles — only changes when toggles change, not sliders
	let visibilityKey = $derived(
		JSON.stringify(settings.nodes) + JSON.stringify(settings.edges)
	);

	// Re-render when data or visibility toggles change (re-feeds graph data).
	// untrack prevents updateGraph's internal reads from subscribing this effect
	// to slider settings — only visibilityKey/nodes/edges trigger a data re-feed.
	$effect(() => {
		void visibilityKey;
		void nodes.length;
		void edges.length;
		if (graph) {
			untrack(() => {
				updateGraph(graph);
				const nodeCount = filteredNodes.length;
				if (nodeCount !== prevNodeCount && nodeCount > 0) {
					prevNodeCount = nodeCount;
					setTimeout(() => graph.zoomToFit(400, 40), 1500);
				}
			});
		}
	});

	// Reconfigure physics when sliders change (no data re-feed, keeps positions)
	$effect(() => {
		void settings.node_spacing;
		void settings.size_contrast;
		void settings.link_length;
		void settings.label_density;
		if (!graph) return;
		// Update node sizes based on hierarchy rank
		graph.nodeVal((n: any) => _computeNodeSize(n.node_type, settings));
		// Update charge
		const chargeForce = graph.d3Force('charge');
		if (chargeForce?.strength) {
			const spacing = settings.node_spacing ?? 1.0;
			chargeForce.strength((n: any) => {
				const bases: Record<string, number> = { collection: -300, set: -200, package: -80, diagram: -40 };
				return (bases[n.node_type] ?? -30) * spacing;
			});
		}
		// Update link distances
		const linkForce = graph.d3Force('link');
		if (linkForce?.distance) {
			const ll = settings.link_length ?? 1.0;
			linkForce.distance((l: any) => {
				const tgt = typeof l.target === 'object' ? l.target : null;
				const tgtType = tgt?.node_type;
				let base = 60;
				if (l.edge_type === 'collection_membership') base = 200;
				else if (l.edge_type === 'set_membership') {
					if (tgtType === 'package') base = 60;
					else if (tgtType === 'diagram') base = 120;
					else base = 80;
				} else if (l.edge_type === 'hierarchy') {
					base = tgtType === 'package' ? 25 : 40;
				} else if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') base = 40;
				return base * ll;
			});
		}
		// Reheat so forces take effect from current positions
		graph.d3ReheatSimulation();
	});

	// Resize graph when maximised state changes
	$effect(() => {
		void maximised;
		if (!graph || !container) return;
		setTimeout(() => {
			const r = container!.getBoundingClientRect();
			if (r.width > 0 && r.height > 0) {
				graph.width(r.width).height(r.height);
				graph.zoomToFit(400, 40);
			}
		}, 100);
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

<svelte:window onkeydown={(e) => { if (maximised && e.key === 'Escape') maximised = false; }} />
<div class="knowledge-graph-wrapper" class:knowledge-graph-maximised={maximised}>
	{#if legend.length > 0}
		<div
			style="position: absolute; bottom: 8px; right: 8px; z-index: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); font-size: 0.75rem; display: flex; flex-wrap: wrap; gap: 8px; max-width: 300px"
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

	<!-- Graph controls -->
	<div style="position: absolute; top: 8px; right: 8px; z-index: 1; display: flex; gap: 4px; align-items: stretch">
		{#if onSettingsChange}
			<div style="position: relative; display: flex">
				<button
					onclick={() => { showSettings = !showSettings; }}
					style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); cursor: pointer; display: flex; align-items: center; font-size: 0.7rem"
					title="Graph settings"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12">
						<path d="M40,88H73a32,32,0,0,0,62,0h81a8,8,0,0,0,0-16H135a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16Zm64-24a16,16,0,1,1-16,16A16,16,0,0,1,104,64ZM216,168H199a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16h97a32,32,0,0,0,62,0h17a8,8,0,0,0,0-16Zm-48,24a16,16,0,1,1,16-16A16,16,0,0,1,168,192Z"/>
					</svg>
				</button>
				{#if showSettings}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div style="position: fixed; inset: 0; z-index: 19" onclick={() => (showSettings = false)}></div>
					<KnowledgeGraphSettings
						{settings}
						onchange={(s) => { onSettingsChange(s); }}
						{isAdmin}
						{onSaveDefault}
						{onResetToDefaults}
					/>
				{/if}
			</div>
		{/if}
		<button
			onclick={() => {
				if (!graph) return;
				updateGraph(graph);
				setTimeout(() => graph.zoomToFit(400, 40), 1500);
			}}
			style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); font-size: 0.7rem; cursor: pointer"
			title="Reset graph to default layout"
		>
			Reset
		</button>
		<button
			onclick={() => { if (graph) graph.zoomToFit(400, 40); }}
			style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); font-size: 0.7rem; cursor: pointer"
			title="Zoom to fit all nodes"
		>
			Fit
		</button>
		<button
			onclick={() => { maximised = !maximised; }}
			style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); cursor: pointer; display: flex; align-items: center; font-size: 0.7rem"
			title={maximised ? 'Exit full screen' : 'Full screen'}
		>
			{#if maximised}
				<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"></polyline><polyline points="20 10 14 10 14 4"></polyline><polyline points="14 20 14 14 20 14"></polyline><polyline points="10 4 10 10 4 10"></polyline></svg>
			{:else}
				<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><polyline points="21 15 21 21 15 21"></polyline><polyline points="3 9 3 3 9 3"></polyline></svg>
			{/if}
		</button>
	</div>

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
	.knowledge-graph-maximised {
		position: fixed;
		inset: 0;
		z-index: 50;
		border: none;
		border-radius: 0;
		height: 100%;
		min-height: 0;
		background: var(--color-bg);
	}
	.knowledge-graph-exit {
		position: absolute;
		top: 8px;
		left: 8px;
		z-index: 2;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		background: var(--color-surface);
		color: var(--color-fg);
		font-size: 1.1rem;
		cursor: pointer;
	}
	.knowledge-graph-exit:hover {
		background: var(--color-border);
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
