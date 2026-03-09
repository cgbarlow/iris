<script lang="ts">
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { exportToSvg, exportToPng, exportToPdf } from '$lib/utils/export';
	import type { Diagram, DiagramVersion, Bookmark } from '$lib/types/api';
	import UnifiedCanvas from '$lib/canvas/UnifiedCanvas.svelte';
	import SequenceDiagram from '$lib/canvas/sequence/SequenceDiagram.svelte';
	import SequenceToolbar from '$lib/canvas/sequence/SequenceToolbar.svelte';
	import ParticipantDialog from '$lib/canvas/sequence/ParticipantDialog.svelte';
	import MessageDialog from '$lib/canvas/sequence/MessageDialog.svelte';
	import { createSequenceViewport } from '$lib/canvas/sequence/useSequenceViewport.svelte';
	import type { SequenceDiagramData, Participant, SequenceMessage } from '$lib/canvas/sequence/types';
	import { SEQUENCE_LAYOUT as L } from '$lib/canvas/sequence/types';
	import FocusView from '$lib/components/FocusView.svelte';
	import DiagramDialog from '$lib/components/DiagramDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import RelationshipDialog from '$lib/canvas/controls/RelationshipDialog.svelte';
	import EdgeStylePanel from '$lib/canvas/controls/EdgeStylePanel.svelte';
	import NodeStylePanel from '$lib/canvas/controls/NodeStylePanel.svelte';
	import ElementEditPanel from '$lib/canvas/controls/ElementEditPanel.svelte';
	import EntityDetailPanel from '$lib/canvas/controls/EntityDetailPanel.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel.svelte';
	import ElementPicker from '$lib/components/ElementPicker.svelte';
	import DiagramPicker from '$lib/components/DiagramPicker.svelte';
	import PackagePicker from '$lib/components/PackagePicker.svelte';
	import NodeDeleteDialog from '$lib/components/NodeDeleteDialog.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import VersionHistory from '$lib/components/VersionHistory.svelte';
	import TagInput from '$lib/components/TagInput.svelte';
	import ThemeSelector from '$lib/components/ThemeSelector.svelte';
	import { getActiveThemeId, loadThemes, areThemesLoaded } from '$lib/stores/themeStore.svelte';
	import { Accordion } from 'bits-ui';
	import { createCanvasHistory } from '$lib/canvas/useCanvasHistory.svelte';
	import { createLockManager } from '$lib/utils/locks.svelte';
	import DOMPurify from 'dompurify';
	import type { Element, DiagramHierarchyNode, Package } from '$lib/types/api';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';
	import type { SimpleEntityType, SimpleRelationshipType, EdgeRoutingType, NotationType } from '$lib/types/canvas';
	import {
		SIMPLE_ENTITY_TYPES,
		UML_ENTITY_TYPES,
		ARCHIMATE_ENTITY_TYPES,
		SIMPLE_RELATIONSHIP_TYPES,
		UML_RELATIONSHIP_TYPES,
		ARCHIMATE_RELATIONSHIP_TYPES,
	} from '$lib/types/canvas';
	import type { UmlEntityType, ArchimateEntityType } from '$lib/types/canvas';

	let diagram = $state<Diagram | null>(null);
	let versions = $state<DiagramVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'canvas' | 'relationships' | 'versions'>('canvas');
	let userSelectedTab = $state(false);
	let versionsLoading = $state(false);

	// Diagram relationships state
	interface DiagramRelationship {
		id: string;
		source_package_id: string;
		target_package_id: string;
		relationship_type: string;
		label: string | null;
		description: string | null;
		created_by: string;
		created_at: string;
		source_name: string;
		target_name: string;
	}
	interface ElementRelationship {
		id: string;
		source_element_id: string;
		target_element_id: string;
		relationship_type: string;
		label: string | null;
		description: string | null;
		created_by: string;
		created_at: string;
		source_name: string;
		target_name: string;
	}
	let diagramRelationships = $state<DiagramRelationship[]>([]);
	let elementRelationships = $state<ElementRelationship[]>([]);
	let relationshipsLoading = $state(false);
	const hasRelationships = $derived(diagramRelationships.length > 0 || elementRelationships.length > 0);

	let showDeleteDialog = $state(false);
	let showCloneDialog = $state(false);
	let inheritedTags = $state<string[]>([]);
	let allTags = $state<string[]>([]);

	// Inline metadata editing state
	let editingOverview = $state(false);
	let overviewDirty = $state(false);
	let savingOverview = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editTags = $state<string[]>([]);
	let editIsTemplate = $state(false);

	// Template designation (derived from tags)
	const isTemplate = $derived((diagram?.tags ?? []).includes('template'));

	// Bookmark state
	let isBookmarked = $state(false);
	let bookmarkLoading = $state(false);

	// Canvas state
	let canvasNodes = $state.raw<CanvasNode[]>([]);
	let canvasEdges = $state.raw<CanvasEdge[]>([]);
	let editing = $state(false);
	let showAddElement = $state(false);
	let canvasDirty = $state(false);
	let saving = $state(false);
	let selectedEdgeId = $state<string | null>(null);

	// Edit element state (WP-15)
	let selectedEditNodeId = $state<string | null>(null);
	let showEditElement = $state(false);
	let editElementData = $state<Element | null>(null);

	// Canvas undo/redo history
	const history = createCanvasHistory();

	// Edit lock manager (ADR-080/086)
	let lockManager = $state<ReturnType<typeof createLockManager> | null>(null);
	let lockConflictUser = $state<string | null>(null);

	// RelationshipDialog state
	let showRelationshipDialog = $state(false);
	let pendingConnection = $state<{ sourceId: string; targetId: string } | null>(null);

	// Browse mode element detail panel state
	let selectedBrowseNode = $state<CanvasNode | null>(null);

	// Sequence diagram state
	let sequenceData = $state<SequenceDiagramData>({
		participants: [],
		messages: [],
		activations: [],
	});
	let selectedMessageId = $state<string | null>(null);
	let showAddParticipant = $state(false);
	let showAddMessage = $state(false);

	// Hierarchy breadcrumb state
	let ancestors = $state<{ id: string; name: string; diagram_type: string }[]>([]);

	// Focus view state
	let focusMode = $state(false);

	/** True when the windowed browse sidebar should be visible (shifts page content). */
	const windowedBrowseSidebar = $derived(!editing && !focusMode && !!selectedBrowseNode);

	// Comments sidebar state
	let showCommentsSidebar = $state(false);
	let commentCount = $state(0);

	/** True when the comments sidebar should shift page content (windowed, non-edit). */
	const windowedCommentsSidebar = $derived(!editing && !focusMode && showCommentsSidebar);

	// Unsaved changes confirmation state
	let showUnsavedChangesDialog = $state(false);
	let pendingModeAction = $state<(() => void) | null>(null);

	/** Toggle from edit to browse mode, prompting to save if dirty. */
	function handleToggleToBrowseMode() {
		if (canvasDirty) {
			pendingModeAction = () => { discardChanges(); };
			showUnsavedChangesDialog = true;
		} else {
			discardChanges();
		}
	}

	/** Save and then execute the pending mode switch. */
	function handleUnsavedSave() {
		showUnsavedChangesDialog = false;
		pendingModeAction = null;
		if (canvasType === 'sequence') {
			saveSequence();
		} else {
			saveCanvas();
		}
	}

	/** Discard and execute the pending mode switch. */
	function handleUnsavedDiscard() {
		showUnsavedChangesDialog = false;
		const action = pendingModeAction;
		pendingModeAction = null;
		action?.();
	}

	/** Cancel the mode switch. */
	function handleUnsavedCancel() {
		showUnsavedChangesDialog = false;
		pendingModeAction = null;
	}

	// Hierarchy tree sidebar state
	let sidebarOpen = $state(
		typeof localStorage !== 'undefined' && localStorage.getItem('iris-hierarchy-sidebar-open') === 'true'
	);
	let hierarchyTree = $state<DiagramHierarchyNode[]>([]);
	let hierarchyLoading = $state(false);
	let treeSearchQuery = $state('');
	let showCreateChildDialog = $state(false);
	let showCreateChildPackageDialog = $state(false);
	let showChildMenu = $state(false);
	let childPackageName = $state('');
	let childPackageDescription = $state('');
	let showParentPicker = $state(false);
	let treeDiagramsOnly = $state(false);
	let treeExpandedIds = $state(new Set<string>());
	let sidebarScrollTop = $state(0);

	/** Save sidebar scroll position before navigating away. */
	function saveSidebarScroll() {
		const el = document.querySelector('[data-hierarchy-sidebar]');
		if (el) {
			sessionStorage.setItem('iris-hierarchy-scroll', String(el.scrollTop));
		}
	}

	/** Restore sidebar scroll position after sidebar renders. */
	function restoreSidebarScroll(node: HTMLElement) {
		const saved = sessionStorage.getItem('iris-hierarchy-scroll');
		if (saved) {
			requestAnimationFrame(() => {
				node.scrollTop = parseFloat(saved);
			});
		}
	}

	// Export menu state
	let showExportMenu = $state(false);

	// Element picker state (link existing element)
	let showElementPicker = $state(false);

	// Diagram picker state (insert diagram as component)
	let showDiagramPicker = $state(false);

	// Node delete dialog state
	let showNodeDeleteDialog = $state(false);
	let deleteNodeId = $state<string | null>(null);
	let deleteNodeName = $state('');
	let deleteNodeIsDiagramRef = $state(false);

	// Add element relationship from tab state
	let addElementRelStep = $state<'source' | 'target' | 'details' | null>(null);
	let addElementRelSource = $state<Element | null>(null);
	let addElementRelTarget = $state<Element | null>(null);

	// Add diagram relationship from tab state
	let showAddDiagramRelPicker = $state(false);
	let showAddDiagramRelDialog = $state(false);
	let addDiagramRelTarget = $state<{ id: string; name: string } | null>(null);

	// "Add to canvas?" prompt state
	let showAddToCanvasPrompt = $state(false);
	let addToCanvasRelType = $state<'element' | 'diagram'>('element');
	let addToCanvasRelData = $state<{
		sourceElementId?: string; targetElementId?: string;
		sourceName?: string; targetName?: string;
		targetDiagramId?: string; targetDiagramName?: string;
		relationshipType?: string;
	} | null>(null);

	async function handleDiagramRollback(version: number) {
		if (!diagram) return;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}/rollback`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'If-Match': String(diagram.current_version) },
				body: JSON.stringify({ target_version: version }),
			});
			await loadDiagram(diagram.id);
			await loadVersions(diagram.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Rollback failed';
		}
	}

	let prevSetId = $state<string | undefined>(undefined);

	$effect(() => {
		const id = page.params.id;
		if (id) {
			userSelectedTab = false;
			loadDiagram(id);
		}
	});

	// Reload hierarchy tree when navigating to a diagram with a different set_id
	$effect(() => {
		if (diagram && sidebarOpen && diagram.set_id !== prevSetId) {
			prevSetId = diagram.set_id;
			treeExpandedIds = new Set<string>();
			loadHierarchyTree();
		}
	});

	// Listen for edge label edit events from EdgeLabel component (WP-3)
	$effect(() => {
		function onEdgeLabelEdit(e: Event) {
			const { edgeId, label } = (e as CustomEvent).detail;
			if (editing) handleEdgeLabelEdit(edgeId, label);
		}
		document.addEventListener('edgelabeledit', onEdgeLabelEdit);
		return () => document.removeEventListener('edgelabeledit', onEdgeLabelEdit);
	});

	// Listen for edge label move events from EdgeLabel component (WP-4)
	$effect(() => {
		function onEdgeLabelMove(e: Event) {
			const { edgeId, offsetX, offsetY } = (e as CustomEvent).detail;
			if (editing) handleEdgeLabelMove(edgeId, offsetX, offsetY);
		}
		document.addEventListener('edgelabelmove', onEdgeLabelMove);
		return () => document.removeEventListener('edgelabelmove', onEdgeLabelMove);
	});

	// Listen for edge style change events from EdgeStylePanel (ADR-086)
	$effect(() => {
		function onEdgeStyleChange(e: Event) {
			const { edgeId, data: updatedData } = (e as CustomEvent).detail;
			if (!editing) return;
			history.pushState(canvasNodes, canvasEdges);
			canvasEdges = canvasEdges.map((edge) =>
				edge.id === edgeId
					? { ...edge, data: { ...edge.data!, ...updatedData } }
					: edge,
			);
			canvasDirty = true;
		}
		document.addEventListener('edgestylechange', onEdgeStyleChange);
		return () => document.removeEventListener('edgestylechange', onEdgeStyleChange);
	});

	// Listen for node style change events from NodeStylePanel (ADR-091-A)
	$effect(() => {
		function onNodeStyleChange(e: Event) {
			const { nodeId, visual: updatedVisual } = (e as CustomEvent).detail;
			if (!editing) return;
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = canvasNodes.map((node) =>
				node.id === nodeId
					? { ...node, data: { ...node.data, visual: updatedVisual } }
					: node,
			);
			canvasDirty = true;
		}
		function onNodeDataChange(e: Event) {
			const { nodeId, field, value } = (e as CustomEvent).detail;
			if (!editing) return;
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = canvasNodes.map((node) => {
				if (node.id !== nodeId) return node;
				const updated = { ...node, data: { ...node.data, [field]: value } };
				// When entityType changes, also update node.type so SvelteFlow picks the right renderer
				if (field === 'entityType') updated.type = value;
				return updated;
			});
			canvasDirty = true;
		}
		document.addEventListener('nodestylechange', onNodeStyleChange);
		document.addEventListener('nodedatachange', onNodeDataChange);
		return () => {
			document.removeEventListener('nodestylechange', onNodeStyleChange);
			document.removeEventListener('nodedatachange', onNodeDataChange);
		};
	});

	// Listen for element edit saved events from ElementEditPanel
	$effect(() => {
		function onElementEditSaved(e: Event) {
			const { nodeId, name, description, elementType } = (e as CustomEvent).detail;
			if (!editing) return;
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = canvasNodes.map((node) => {
				if (node.id !== nodeId) return node;
				const updated = { ...node, data: { ...node.data, label: name, description, entityType: elementType } };
				updated.type = elementType;
				return updated;
			});
			canvasDirty = true;
		}
		document.addEventListener('elementeditsaved', onElementEditSaved);
		return () => document.removeEventListener('elementeditsaved', onElementEditSaved);
	});

	// Live preview: reflect ElementEditPanel changes on canvas instantly (no history/dirty)
	$effect(() => {
		function onElementEditPreview(e: Event) {
			const { nodeId, name, description, elementType } = (e as CustomEvent).detail;
			if (!editing) return;
			canvasNodes = canvasNodes.map((node) => {
				if (node.id !== nodeId) return node;
				return { ...node, data: { ...node.data, label: name, description, entityType: elementType }, type: elementType };
			});
		}
		document.addEventListener('elementeditpreview', onElementEditPreview);
		return () => document.removeEventListener('elementeditpreview', onElementEditPreview);
	});

	// Listen for node resize end events from NodeResizer (ADR-091-A)
	$effect(() => {
		function onNodeResizeEnd(e: Event) {
			if (!editing || !selectedEditNodeId) return;
			const { width, height } = (e as CustomEvent).detail;
			history.pushState(canvasNodes, canvasEdges);
			const w = Math.round(width);
			const h = Math.round(height);
			canvasNodes = canvasNodes.map((node) =>
				node.id === selectedEditNodeId
					? { ...node, width: w, height: h, data: { ...node.data, visual: { ...node.data.visual, width: w, height: h } } }
					: node,
			);
			canvasDirty = true;
		}
		document.addEventListener('noderesizeend', onNodeResizeEnd);
		return () => document.removeEventListener('noderesizeend', onNodeResizeEnd);
	});

	// Release lock on navigation and component destroy (ADR-080/086)
	beforeNavigate(() => {
		saveSidebarScroll();
		if (lockManager && lockManager.isOwner) {
			lockManager.releaseLock();
			editing = false;
		}
	});

	onDestroy(() => {
		if (lockManager) {
			lockManager.destroy();
		}
	});

	/** Determine which canvas component to render based on diagram notation/type. */
	const canvasType = $derived.by(() => {
		if (!diagram) return 'simple';
		if (diagram.diagram_type === 'sequence') return 'sequence';
		// Use notation from registry (ADR-079)
		const n = diagram.notation ?? 'simple';
		if (n === 'uml') return 'uml';
		if (n === 'archimate') return 'archimate';
		if (n === 'c4') return 'c4';
		return 'simple';
	});

	/** Notation for UnifiedCanvas context. */
	const notation = $derived<NotationType>(canvasType === 'sequence' ? 'simple' : canvasType as NotationType);

	/** Preferred theme from diagram metadata (e.g. Sparx EA imports set theme_id). */
	const preferredThemeId = $derived(diagram?.metadata?.theme_id as string | undefined);

	/** Source node name for RelationshipDialog display. */
	const pendingSourceName = $derived.by(() => {
		const pc = pendingConnection;
		if (!pc) return '';
		return canvasNodes.find((n) => n.id === pc.sourceId)?.data.label ?? 'Source';
	});

	/** Target node name for RelationshipDialog display. */
	const pendingTargetName = $derived.by(() => {
		const pc = pendingConnection;
		if (!pc) return '';
		return canvasNodes.find((n) => n.id === pc.targetId)?.data.label ?? 'Target';
	});

	async function loadDiagram(id: string) {
		loading = true;
		error = null;
		try {
			// Load themes in parallel with diagram data to prevent flash
			const [diagramResult] = await Promise.all([
				apiFetch<Diagram>(`/api/diagrams/${id}`),
				areThemesLoaded() ? Promise.resolve() : loadThemes(),
			]);
			diagram = diagramResult;
			parseCanvasData();
			// Smart default tab: show details if no canvas content
			if (!userSelectedTab) {
				const hasContent = diagram.diagram_type === 'sequence'
					? sequenceData.participants.length > 0
					: canvasNodes.length > 0;
				activeTab = hasContent ? 'canvas' : 'details';
			}
			refreshNodeDescriptions();
			loadVersions(id);
			loadBookmarkStatus(id);
			loadInheritedTags();
			loadAllTags();
			loadAncestors(id);
			loadDiagramRelationships(id);
			loadCommentCount(id);
			// Initialize lock manager for this diagram (ADR-080/086)
			if (lockManager) {
				lockManager.destroy();
			}
			lockManager = createLockManager('diagram', id);
			lockConflictUser = null;
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Diagram not found'
				: 'Failed to load diagram';
		}
		loading = false;
	}

	/** Sync node descriptions from linked elements (WP-5). */
	async function refreshNodeDescriptions() {
		let updated = false;
		const refreshed = await Promise.all(
			canvasNodes.map(async (node) => {
				const entityId = node.data?.entityId;
				if (!entityId) return node;
				try {
					const element = await apiFetch<Element>(`/api/elements/${entityId}`);
					const rawDesc = element.description ?? '';
					const desc = rawDesc.startsWith(node.data.label) ? rawDesc.slice(rawDesc.indexOf('\n') + 1).replace(/^\r?\n/, '') : rawDesc;
					if (desc !== node.data.description || element.name !== node.data.label) {
						updated = true;
						return {
							...node,
							data: {
								...node.data,
								label: element.name,
								description: desc,
							},
						};
					}
				} catch { /* element may be deleted */ }
				return node;
			}),
		);
		if (updated) {
			canvasNodes = refreshed;
		}
	}

	async function loadInheritedTags() {
		// Compute inherited tags from elements placed on this diagram's canvas
		const elementTags = new Set<string>();
		for (const node of canvasNodes) {
			const entityId = node.data?.entityId;
			if (!entityId) continue;
			try {
				const e = await apiFetch<{ tags?: string[] }>(`/api/elements/${entityId}`);
				if (e.tags) e.tags.forEach((t) => elementTags.add(t));
			} catch { /* skip inaccessible elements */ }
		}
		const ownTags = new Set(diagram?.tags ?? []);
		inheritedTags = [...elementTags].filter((t) => !ownTags.has(t)).sort();
	}

	async function loadAllTags() {
		try {
			allTags = await apiFetch<string[]>('/api/elements/tags/all');
		} catch {
			allTags = [];
		}
	}

	async function loadAncestors(id: string) {
		try {
			ancestors = await apiFetch<{ id: string; name: string; diagram_type: string }[]>(
				`/api/diagrams/${id}/ancestors`
			);
		} catch {
			ancestors = [];
		}
	}

	async function loadHierarchyTree() {
		if (!diagram?.set_id) return;
		hierarchyLoading = true;
		try {
			hierarchyTree = await apiFetch<DiagramHierarchyNode[]>(
				`/api/diagrams/hierarchy?set_id=${diagram.set_id}`
			);
		} catch {
			hierarchyTree = [];
		}
		hierarchyLoading = false;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
		localStorage.setItem('iris-hierarchy-sidebar-open', String(sidebarOpen));
		if (sidebarOpen && hierarchyTree.length === 0) {
			loadHierarchyTree();
		}
	}

	async function handleCreateChild(name: string, diagramType: string, description: string, _tags?: string[], _isTemplate?: boolean, childNotation?: string) {
		if (!diagram) return;
		try {
			const body: Record<string, unknown> = {
				diagram_type: diagramType,
				name,
				description,
				data: {},
				parent_package_id: diagram.id,
				set_id: diagram.set_id,
			};
			if (childNotation) body.notation = childNotation;
			const created = await apiFetch<Diagram>('/api/diagrams', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateChildDialog = false;
			await loadHierarchyTree();
			await goto(`/diagrams/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create child diagram';
		}
	}

	async function handleCreateChildPackage() {
		if (!diagram || !childPackageName.trim()) return;
		try {
			const created = await apiFetch<{ id: string }>('/api/packages', {
				method: 'POST',
				body: JSON.stringify({
					name: childPackageName.trim(),
					description: childPackageDescription.trim() || null,
					parent_package_id: diagram.parent_package_id,
					set_id: diagram.set_id,
				}),
			});
			showCreateChildPackageDialog = false;
			childPackageName = '';
			childPackageDescription = '';
			await loadHierarchyTree();
			await goto(`/packages/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create child package';
		}
	}

	async function handleSetParent(parentPkg: Package) {
		if (!diagram) return;
		showParentPicker = false;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_package_id: parentPkg.id }),
			});
			await loadDiagram(diagram.id);
			if (sidebarOpen) await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to set parent';
		}
	}

	async function handleRemoveParent() {
		if (!diagram) return;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_package_id: null }),
			});
			await loadDiagram(diagram.id);
			if (sidebarOpen) await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove parent';
		}
	}

	function parseCanvasData() {
		if (!diagram?.data) {
			canvasNodes = [];
			canvasEdges = [];
			sequenceData = { participants: [], messages: [], activations: [] };
			return;
		}
		// Deep-clone to break shared references — prevents edits from
		// mutating the original diagram.data (needed for discard to work).
		const data = JSON.parse(JSON.stringify(diagram.data)) as Record<string, unknown>;

		if (diagram.diagram_type === 'sequence') {
			sequenceData = {
				participants: Array.isArray(data.participants) ? data.participants : [],
				messages: Array.isArray(data.messages) ? data.messages : [],
				activations: Array.isArray(data.activations) ? data.activations : [],
			} as SequenceDiagramData;
		} else {
			canvasNodes = ((Array.isArray(data.nodes) ? data.nodes : []) as CanvasNode[]).map((n) => {
				const vw = n.data?.visual?.width ?? n.measured?.width ?? 200;
				// Don't set explicit height — let SvelteFlow auto-measure from content
				// so descriptions are fully visible and resize handles are correctly positioned.
				const { height: _h, measured: _m, ...rest } = n;
				return { ...rest, width: n.width ?? vw };
			});
			canvasEdges = (Array.isArray(data.edges) ? data.edges : []) as CanvasEdge[];
		}
		canvasDirty = false;
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<DiagramVersion[]>(`/api/diagrams/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	async function loadDiagramRelationships(id: string) {
		relationshipsLoading = true;
		try {
			const result = await apiFetch<{
				diagram_relationships: DiagramRelationship[];
				element_relationships: ElementRelationship[];
			}>(`/api/diagrams/${id}/relationships`);
			diagramRelationships = result.diagram_relationships;
			elementRelationships = result.element_relationships;
		} catch {
			diagramRelationships = [];
			elementRelationships = [];
		}
		relationshipsLoading = false;
	}

	async function loadCommentCount(id: string) {
		try {
			const result = await apiFetch<unknown[]>(`/api/diagrams/${id}/comments`);
			commentCount = result.length;
		} catch {
			commentCount = 0;
		}
	}

	function toggleCommentsSidebar() {
		showCommentsSidebar = !showCommentsSidebar;
		if (showCommentsSidebar) {
			selectedBrowseNode = null;
		}
	}

	async function deleteDiagramRelationship(relId: string) {
		if (!diagram) return;
		try {
			await apiFetch(`/api/diagram-relationships/${relId}`, { method: 'DELETE' });
			diagramRelationships = diagramRelationships.filter((r) => r.id !== relId);
		} catch {
			// ignore
		}
	}

	async function loadBookmarkStatus(id: string) {
		try {
			const bookmarks = await apiFetch<Bookmark[]>('/api/bookmarks');
			isBookmarked = bookmarks.some((b) => b.diagram_id === id);
		} catch {
			isBookmarked = false;
		}
	}

	async function toggleBookmark() {
		if (!diagram || bookmarkLoading) return;
		bookmarkLoading = true;
		try {
			if (isBookmarked) {
				await apiFetch(`/api/diagrams/${diagram.id}/bookmark`, { method: 'DELETE' });
				isBookmarked = false;
			} else {
				await apiFetch(`/api/diagrams/${diagram.id}/bookmark`, { method: 'POST' });
				isBookmarked = true;
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update bookmark';
		}
		bookmarkLoading = false;
	}

	function enterOverviewEdit() {
		if (!diagram) return;
		editName = diagram.name;
		editDescription = diagram.description ?? '';
		editTags = (diagram.tags ?? []).filter(t => t !== 'template');
		editIsTemplate = isTemplate;
		editingOverview = true;
		overviewDirty = false;
	}

	// Track dirty state for inline editing
	$effect(() => {
		if (!editingOverview || !diagram) return;
		const nameChanged = editName !== diagram.name;
		const descChanged = editDescription !== (diagram.description ?? '');
		const origTags = (diagram.tags ?? []).filter(t => t !== 'template');
		const tagsChanged = JSON.stringify(editTags.slice().sort()) !== JSON.stringify(origTags.slice().sort());
		const templateChanged = editIsTemplate !== isTemplate;
		overviewDirty = nameChanged || descChanged || tagsChanged || templateChanged;
	});

	async function saveMetadata() {
		if (!diagram) return;
		savingOverview = true;
		error = null;
		try {
			const sanitizedName = DOMPurify.sanitize(editName).trim();
			const sanitizedDesc = DOMPurify.sanitize(editDescription).trim();
			if (!sanitizedName) {
				error = 'Name is required';
				savingOverview = false;
				return;
			}
			await apiFetch(`/api/diagrams/${diagram.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(diagram.current_version) },
				body: JSON.stringify({
					name: sanitizedName,
					description: sanitizedDesc,
					data: diagram.data,
					change_summary: 'Updated diagram details',
				}),
			});

			// Sync tags
			const oldTags = diagram.tags ?? [];
			const newTags = [...editTags];

			// Handle template toggle via tags
			if (editIsTemplate && !newTags.includes('template')) {
				newTags.push('template');
			}
			const fullOldTags = oldTags;
			const toAdd = newTags.filter((t) => !fullOldTags.includes(t));
			const toRemove = fullOldTags.filter((t) => !newTags.includes(t));
			if (!editIsTemplate && oldTags.includes('template') && !toRemove.includes('template')) {
				toRemove.push('template');
			}

			for (const tag of toAdd) {
				await apiFetch(`/api/diagrams/${diagram.id}/tags`, {
					method: 'POST',
					body: JSON.stringify({ tag }),
				});
			}
			for (const tag of toRemove) {
				await apiFetch(`/api/diagrams/${diagram.id}/tags/${encodeURIComponent(tag)}`, {
					method: 'DELETE',
				});
			}

			editingOverview = false;
			overviewDirty = false;
			await loadDiagram(diagram.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update diagram';
		}
		savingOverview = false;
	}

	function discardOverviewChanges() {
		editingOverview = false;
		overviewDirty = false;
	}

	async function handleDelete() {
		if (!diagram) return;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(diagram.current_version) },
			});
			showDeleteDialog = false;
			await goto('/diagrams');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete diagram';
		}
	}

	async function handleClone(name: string, diagramType: string, description: string, _tags?: string[], _isTemplate?: boolean, cloneNotation?: string) {
		if (!diagram) return;
		try {
			const body: Record<string, unknown> = {
				diagram_type: diagramType,
				name,
				description,
				data: diagram.data ?? {},
			};
			if (cloneNotation) body.notation = cloneNotation;
			const created = await apiFetch<Diagram>('/api/diagrams', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCloneDialog = false;
			await goto(`/diagrams/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to clone diagram';
		}
	}

	// Canvas editing

	/** Standard node dimensions for overlap detection. */
	const NODE_WIDTH = 220;
	const NODE_HEIGHT = 100;
	const NODE_GAP = 30;

	/** Find a position that doesn't overlap existing nodes. */
	function findOpenPosition(): { x: number; y: number } {
		const cols = 4;
		const cellW = NODE_WIDTH + NODE_GAP;
		const cellH = NODE_HEIGHT + NODE_GAP;
		for (let i = 0; i < 200; i++) {
			const col = i % cols;
			const row = Math.floor(i / cols);
			const x = 60 + col * cellW;
			const y = 60 + row * cellH;
			const overlaps = canvasNodes.some((n) => {
				const nx = n.position.x;
				const ny = n.position.y;
				return (
					Math.abs(nx - x) < NODE_WIDTH + NODE_GAP / 2 &&
					Math.abs(ny - y) < NODE_HEIGHT + NODE_GAP / 2
				);
			});
			if (!overlaps) return { x, y };
		}
		return { x: 60, y: 60 };
	}

	async function handleAddElement(name: string, elementType: SimpleEntityType, description: string, _tags?: string[], elementNotation?: string) {
		try {
			const effectiveNotation = elementNotation ?? notation ?? 'simple';
			const created = await apiFetch<Element>('/api/elements', {
				method: 'POST',
				body: JSON.stringify({
					element_type: elementType,
					name,
					description,
					data: {},
					notation: effectiveNotation,
				}),
			});
			const id = crypto.randomUUID();
			const newNode: CanvasNode = {
				id,
				type: elementType,
				position: findOpenPosition(),
				width: 200,
				data: {
					label: name,
					entityType: elementType,
					description,
					entityId: created.id,
					notation: effectiveNotation,
				},
			};
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = [...canvasNodes, newNode];
			canvasDirty = true;
			showAddElement = false;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create element';
		}
	}

	function handleDeleteNode(nodeId: string) {
		const node = canvasNodes.find((n) => n.id === nodeId);
		if (!node) return;
		deleteNodeId = nodeId;
		deleteNodeName = node.data?.label ?? 'Unknown';
		deleteNodeIsDiagramRef = !!node.data?.linkedModelId;
		showNodeDeleteDialog = true;
	}

	function handleRemoveNodeFromCanvas() {
		if (!deleteNodeId) return;
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = canvasNodes.filter((n) => n.id !== deleteNodeId);
		canvasEdges = canvasEdges.filter((e) => e.source !== deleteNodeId && e.target !== deleteNodeId);
		canvasDirty = true;
		showNodeDeleteDialog = false;
		deleteNodeId = null;
	}

	async function handleCascadeDeleteElement() {
		if (!deleteNodeId) return;
		const node = canvasNodes.find((n) => n.id === deleteNodeId);
		const entityId = node?.data?.entityId;
		if (!entityId) return;

		try {
			// Fetch element to get current version for OCC
			const element = await apiFetch<Element>(`/api/elements/${entityId}`);
			await apiFetch(`/api/elements/${entityId}?cascade=true`, {
				method: 'DELETE',
				headers: { 'If-Match': String(element.current_version) },
			});
			// Remove node from local canvas state
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = canvasNodes.filter((n) => n.id !== deleteNodeId);
			canvasEdges = canvasEdges.filter((e) => e.source !== deleteNodeId && e.target !== deleteNodeId);
			canvasDirty = true;
			showNodeDeleteDialog = false;
			deleteNodeId = null;
			// Reload diagram (canvas data may have changed server-side)
			if (diagram) await loadDiagram(diagram.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete element';
			showNodeDeleteDialog = false;
		}
	}

	function handleDeleteEdge(edgeId: string) {
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.filter((e) => e.id !== edgeId);
		selectedEdgeId = null;
		canvasDirty = true;
	}

	function handleReconnectEdge() {
		history.pushState(canvasNodes, canvasEdges);
		canvasDirty = true;
	}

	function handleEdgeSelect(edgeId: string | null) {
		selectedEdgeId = edgeId;
	}

	function handleEdgeLabelEdit(edgeId: string, newLabel: string) {
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.map((e) =>
			e.id === edgeId
				? { ...e, data: { ...e.data!, label: newLabel || undefined } }
				: e,
		);
		canvasDirty = true;
	}

	function handleEdgeLabelMove(edgeId: string, offsetX: number, offsetY: number) {
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.map((e) =>
			e.id === edgeId
				? { ...e, data: { ...e.data!, labelOffsetX: offsetX, labelOffsetY: offsetY } }
				: e,
		);
		canvasDirty = true;
	}

	function handleNodeSelect(nodeId: string | null) {
		selectedEditNodeId = nodeId;
	}

	/** Whether the currently selected node in edit mode is a linked element (has entityId). */
	const selectedNodeIsLinkedElement = $derived.by(() => {
		if (!selectedEditNodeId) return false;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return !!node?.data?.entityId;
	});

	/** Navigate to the element page in edit mode. */
	function handleEditElementClick() {
		if (!selectedEditNodeId) return;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		if (!node?.data?.entityId) return;
		goto(`/elements/${node.data.entityId}?edit=true`);
	}

	/** Save the edited element via PUT, then update the canvas node. */
	async function handleEditElementSave(name: string, elementType: SimpleEntityType, description: string, _tags?: string[], _notation?: string) {
		if (!editElementData || !selectedEditNodeId) return;
		try {
			await apiFetch(`/api/elements/${editElementData.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(editElementData.current_version) },
				body: JSON.stringify({
					name,
					element_type: elementType,
					description,
					change_summary: 'Updated element from diagram editor',
				}),
			});
			// Update the canvas node's label and description to reflect the edit
			canvasNodes = canvasNodes.map((n) =>
				n.id === selectedEditNodeId
					? { ...n, type: elementType, data: { ...n.data, label: name, entityType: elementType, description } }
					: n,
			);
			canvasDirty = true;
			showEditElement = false;
			editElementData = null;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update element';
		}
	}

	/** Derived routing type for the currently selected edge. */
	const selectedEdgeData = $derived.by(() => {
		if (!selectedEdgeId) return null;
		const edge = canvasEdges.find((e) => e.id === selectedEdgeId);
		return edge?.data ?? null;
	});

	/** Derived visual overrides for the currently selected node in edit mode. */
	const selectedNodeVisual = $derived.by(() => {
		if (!selectedEditNodeId) return null;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return node?.data?.visual ?? {};
	});

	/** Derived entity type for the currently selected node. */
	const selectedNodeEntityType = $derived.by(() => {
		if (!selectedEditNodeId) return 'component' as SimpleEntityType;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return (node?.data?.entityType ?? 'component') as SimpleEntityType;
	});

	/** Derived entityId for the currently selected node (null if not linked). */
	const selectedNodeEntityId = $derived.by(() => {
		if (!selectedEditNodeId) return null;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return node?.data?.entityId ?? null;
	});

	/** Derived label for the currently selected node (for unlinked ElementEditPanel). */
	const selectedNodeLabel = $derived.by(() => {
		if (!selectedEditNodeId) return '';
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return node?.data?.label ?? '';
	});

	/** Derived description for the currently selected node (for unlinked ElementEditPanel). */
	const selectedNodeDescription = $derived.by(() => {
		if (!selectedEditNodeId) return '';
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return node?.data?.description ?? '';
	});

	function handleConnectNodes(sourceId: string, targetId: string) {
		pendingConnection = { sourceId, targetId };
		showRelationshipDialog = true;
	}

	async function handleRelationshipSave(type: SimpleRelationshipType, label: string, extras?: { sourceCardinality?: string; targetCardinality?: string; sourceRole?: string; targetRole?: string; stereotype?: string }) {
		if (!pendingConnection) return;
		const { sourceId, targetId } = pendingConnection;

		// Resolve element IDs from the connected nodes
		const sourceNode = canvasNodes.find((n) => n.id === sourceId);
		const targetNode = canvasNodes.find((n) => n.id === targetId);
		const sourceEntityId = sourceNode?.data?.entityId;
		const targetEntityId = targetNode?.data?.entityId;

		let relationshipId: string | undefined;

		// Create a real relationship record if both nodes are linked to elements
		let diagramRelationshipId: string | undefined;
		if (sourceEntityId && targetEntityId) {
			try {
				const rel = await apiFetch<{ id: string }>('/api/relationships', {
					method: 'POST',
					body: JSON.stringify({
						source_element_id: sourceEntityId,
						target_element_id: targetEntityId,
						relationship_type: type,
						label: label || type,
						description: '',
					}),
				});
				relationshipId = rel.id;
			} catch {
				// Non-fatal: edge still works visually without a DB relationship
			}
		} else if (sourceNode?.data?.linkedModelId && targetNode?.data?.linkedModelId && diagram) {
			// Both nodes are diagramrefs — create a diagram relationship
			try {
				const rel = await apiFetch<{ id: string }>(`/api/diagrams/${sourceNode.data.linkedModelId}/relationships`, {
					method: 'POST',
					body: JSON.stringify({
						target_package_id: targetNode.data.linkedModelId,
						relationship_type: type,
						label: label || undefined,
					}),
				});
				diagramRelationshipId = rel.id;
			} catch {
				// Non-fatal: edge still works visually
			}
		}

		const newEdge: CanvasEdge = {
			id: `e-${sourceId}-${targetId}`,
			source: sourceId,
			target: targetId,
			type,
			data: {
				relationshipType: type,
				label: label || undefined,
				relationshipId,
				diagramRelationshipId,
				...extras,
			},
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = [...canvasEdges, newEdge];
		canvasDirty = true;
		showRelationshipDialog = false;
		pendingConnection = null;
	}

	function handleRelationshipCancel() {
		showRelationshipDialog = false;
		pendingConnection = null;
	}

	function handleBrowseNodeSelect(nodeId: string) {
		const node = canvasNodes.find((n) => n.id === nodeId) ?? null;
		// If the node is a diagram reference, navigate to it
		if (node?.data?.linkedModelId) {
			goto(`/diagrams/${node.data.linkedModelId}`);
			return;
		}
		selectedBrowseNode = node;
		if (node) showCommentsSidebar = false;
	}

	function handleSequenceParticipantSelect(participant: Participant) {
		if (!participant.entityId) return;
		selectedBrowseNode = {
			id: `seq-participant-${participant.id}`,
			type: 'default',
			position: { x: 0, y: 0 },
			data: {
				label: participant.name,
				entityType: participant.type,
				entityId: participant.entityId,
			},
		};
	}

	async function saveCanvas() {
		if (!diagram) return;
		saving = true;
		error = null;
		try {
			// Persist active theme to diagram metadata if user has one set
			const activeTheme = getActiveThemeId(notation);
			const metadata = activeTheme && !diagram.metadata?.theme_id
				? { ...(diagram.metadata ?? {}), theme_id: activeTheme }
				: diagram.metadata;
			await apiFetch(`/api/diagrams/${diagram.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(diagram.current_version) },
				body: JSON.stringify({
					name: diagram.name,
					description: diagram.description ?? '',
					data: { nodes: canvasNodes, edges: canvasEdges },
					metadata,
					change_summary: 'Updated diagram',
				}),
			});
			canvasDirty = false;
			history.clear();
			editing = false;
			if (lockManager) {
				await lockManager.releaseLock();
			}
			lockConflictUser = null;
			await loadDiagram(diagram.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save canvas';
		}
		saving = false;
	}

	function handleLinkElement(element: Element) {
		const id = crypto.randomUUID();
		const elementType = element.element_type as SimpleEntityType;
		const newNode: CanvasNode = {
			id,
			type: elementType,
			position: findOpenPosition(),
			width: 200,
			data: {
				label: element.name,
				entityType: elementType,
				description: element.description ?? '',
				entityId: element.id,
				notation: element.notation ?? 'simple',
			},
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = [...canvasNodes, newNode];
		canvasDirty = true;
		showElementPicker = false;
	}

	function handleInsertDiagram(linkedDiagram: Diagram) {
		const id = crypto.randomUUID();
		const newNode: CanvasNode = {
			id,
			type: 'modelref',
			position: findOpenPosition(),
			width: 200,
			data: {
				label: linkedDiagram.name,
				entityType: 'component' as SimpleEntityType,
				description: linkedDiagram.description ?? '',
				linkedModelId: linkedDiagram.id,
			},
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = [...canvasNodes, newNode];
		canvasDirty = true;
		showDiagramPicker = false;
	}

	// --- Add element relationship from tab ---
	function handleStartAddElementRel() {
		addElementRelStep = 'source';
		addElementRelSource = null;
		addElementRelTarget = null;
	}

	function handleElementRelSourceSelected(element: Element) {
		addElementRelSource = element;
		addElementRelStep = 'target';
	}

	function handleElementRelTargetSelected(element: Element) {
		addElementRelTarget = element;
		addElementRelStep = 'details';
	}

	async function handleElementRelSave(type: SimpleRelationshipType, label: string) {
		if (!addElementRelSource || !addElementRelTarget || !diagram) return;
		try {
			await apiFetch('/api/relationships', {
				method: 'POST',
				body: JSON.stringify({
					source_element_id: addElementRelSource.id,
					target_element_id: addElementRelTarget.id,
					relationship_type: type,
					label: label || type,
					description: '',
				}),
			});
			addElementRelStep = null;
			loadDiagramRelationships(diagram.id);
			// Prompt to add to canvas
			addToCanvasRelType = 'element';
			addToCanvasRelData = {
				sourceElementId: addElementRelSource.id,
				targetElementId: addElementRelTarget.id,
				sourceName: addElementRelSource.name,
				targetName: addElementRelTarget.name,
				relationshipType: type,
			};
			showAddToCanvasPrompt = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create relationship';
			addElementRelStep = null;
		}
	}

	// --- Add diagram relationship from tab ---
	function handleStartAddDiagramRel() {
		showAddDiagramRelPicker = true;
		addDiagramRelTarget = null;
	}

	function handleDiagramRelTargetSelected(selectedDiagram: Diagram) {
		addDiagramRelTarget = { id: selectedDiagram.id, name: selectedDiagram.name };
		showAddDiagramRelPicker = false;
		showAddDiagramRelDialog = true;
	}

	async function handleDiagramRelSave(type: SimpleRelationshipType, label: string) {
		if (!addDiagramRelTarget || !diagram) return;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}/relationships`, {
				method: 'POST',
				body: JSON.stringify({
					target_package_id: addDiagramRelTarget.id,
					relationship_type: type,
					label: label || undefined,
				}),
			});
			showAddDiagramRelDialog = false;
			loadDiagramRelationships(diagram.id);
			// Prompt to add to canvas
			addToCanvasRelType = 'diagram';
			addToCanvasRelData = {
				targetDiagramId: addDiagramRelTarget.id,
				targetDiagramName: addDiagramRelTarget.name,
			};
			showAddToCanvasPrompt = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create diagram relationship';
			showAddDiagramRelDialog = false;
		}
	}

	// --- "Add to canvas?" prompt ---
	function handleAddToCanvas() {
		if (!addToCanvasRelData) return;
		if (addToCanvasRelType === 'element') {
			const { sourceElementId, targetElementId, sourceName, targetName, relationshipType } = addToCanvasRelData;
			if (!sourceElementId || !targetElementId) return;

			history.pushState(canvasNodes, canvasEdges);

			// Find or create source node
			let sourceNodeId = canvasNodes.find((n) => n.data?.entityId === sourceElementId)?.id;
			if (!sourceNodeId) {
				sourceNodeId = crypto.randomUUID();
				canvasNodes = [...canvasNodes, {
					id: sourceNodeId,
					type: 'component',
					position: findOpenPosition(),
					width: 200,
					data: { label: sourceName ?? 'Source', entityType: 'component' as SimpleEntityType, entityId: sourceElementId },
				}];
			}

			// Find or create target node
			let targetNodeId = canvasNodes.find((n) => n.data?.entityId === targetElementId)?.id;
			if (!targetNodeId) {
				targetNodeId = crypto.randomUUID();
				canvasNodes = [...canvasNodes, {
					id: targetNodeId,
					type: 'component',
					position: findOpenPosition(),
					width: 200,
					data: { label: targetName ?? 'Target', entityType: 'component' as SimpleEntityType, entityId: targetElementId },
				}];
			}

			// Add edge
			const edgeType = (relationshipType ?? 'uses') as SimpleRelationshipType;
			canvasEdges = [...canvasEdges, {
				id: `e-${sourceNodeId}-${targetNodeId}`,
				source: sourceNodeId,
				target: targetNodeId,
				type: edgeType,
				data: { relationshipType: edgeType },
			}];

			canvasDirty = true;
			activeTab = 'canvas';
		} else if (addToCanvasRelType === 'diagram') {
			const { targetDiagramId, targetDiagramName } = addToCanvasRelData;
			if (!targetDiagramId) return;

			// Only add target diagram as modelref node if not already present
			const existing = canvasNodes.find((n) => n.data?.linkedModelId === targetDiagramId);
			if (!existing) {
				history.pushState(canvasNodes, canvasEdges);
				canvasNodes = [...canvasNodes, {
					id: crypto.randomUUID(),
					type: 'modelref',
					position: findOpenPosition(),
					width: 200,
					data: { label: targetDiagramName ?? 'Diagram', entityType: 'component' as SimpleEntityType, linkedModelId: targetDiagramId },
				}];
				canvasDirty = true;
			}
			activeTab = 'canvas';
		}
		showAddToCanvasPrompt = false;
		addToCanvasRelData = null;
	}

	function handleDismissAddToCanvas() {
		showAddToCanvasPrompt = false;
		addToCanvasRelData = null;
	}

	function handleNodeDragStart() {
		history.pushState(canvasNodes, canvasEdges);
		canvasDirty = true;
	}

	function handleUndo() {
		const state = history.undo(canvasNodes, canvasEdges);
		if (state) {
			canvasNodes = state.nodes;
			canvasEdges = state.edges;
			canvasDirty = true;
		}
	}

	function handleRedo() {
		const state = history.redo(canvasNodes, canvasEdges);
		if (state) {
			canvasNodes = state.nodes;
			canvasEdges = state.edges;
			canvasDirty = true;
		}
	}

	async function discardChanges() {
		editing = false;
		history.clear();
		lockConflictUser = null;
		if (lockManager) {
			lockManager.releaseLock();
		}
		// Reload from API to guarantee clean state — eliminates any
		// possibility of stale data from SvelteFlow's bind:nodes writeback.
		if (diagram) {
			await loadDiagram(diagram.id);
		}
	}

	async function handleStartEditing() {
		if (lockManager) {
			const acquired = await lockManager.acquireLock();
			if (acquired) {
				editing = true;
				lockConflictUser = null;
			} else {
				lockConflictUser = lockManager.lockHolder;
			}
		} else {
			editing = true;
		}
		showCommentsSidebar = false;
	}

	// Export handlers
	function getFlowElement(): HTMLElement | null {
		return document.querySelector('.svelte-flow') as HTMLElement | null;
	}

	async function handleExportSvg() {
		const el = getFlowElement();
		if (el && diagram) {
			await exportToSvg(el, diagram.name);
			showExportMenu = false;
		}
	}

	async function handleExportPng() {
		const el = getFlowElement();
		if (el && diagram) {
			await exportToPng(el, diagram.name);
			showExportMenu = false;
		}
	}

	async function handleExportPdf() {
		const el = getFlowElement();
		if (el && diagram) {
			await exportToPdf(el, diagram.name, diagram.name);
			showExportMenu = false;
		}
	}

	// Sequence diagram viewport
	const seqContentWidth = $derived(
		sequenceData.participants.length > 0
			? sequenceData.participants.length * (L.participantWidth + L.participantGap) - L.participantGap + L.padding * 2
			: 400,
	);
	const seqContentHeight = $derived(
		sequenceData.participants.length > 0
			? L.messageStartY + (sequenceData.messages.length + 1) * L.messageGap + L.participantHeight + L.padding
			: 300,
	);
	const seqViewport = $derived(createSequenceViewport(seqContentWidth, seqContentHeight));

	// Sequence editing

	function handleAddParticipant(name: string, type: Participant['type']) {
		const id = crypto.randomUUID();
		sequenceData = {
			...sequenceData,
			participants: [...sequenceData.participants, { id, name, type }],
		};
		canvasDirty = true;
		showAddParticipant = false;
	}

	function handleAddMessage(from: string, to: string, label: string, type: SequenceMessage['type']) {
		const id = crypto.randomUUID();
		const order = sequenceData.messages.length;
		sequenceData = {
			...sequenceData,
			messages: [...sequenceData.messages, { id, from, to, label, type, order }],
		};
		canvasDirty = true;
		showAddMessage = false;
	}

	function handleDeleteSelected() {
		if (selectedMessageId) {
			sequenceData = {
				...sequenceData,
				messages: sequenceData.messages
					.filter((m) => m.id !== selectedMessageId)
					.map((m, i) => ({ ...m, order: i })),
				activations: sequenceData.activations.filter(
					(a) => !sequenceData.messages.some(
						(m) => m.id === selectedMessageId &&
							(a.startOrder === m.order || a.endOrder === m.order),
					),
				),
			};
			selectedMessageId = null;
			canvasDirty = true;
		}
	}

	async function saveSequence() {
		if (!diagram) return;
		saving = true;
		error = null;
		try {
			await apiFetch(`/api/diagrams/${diagram.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(diagram.current_version) },
				body: JSON.stringify({
					name: diagram.name,
					description: diagram.description ?? '',
					data: {
						participants: sequenceData.participants,
						messages: sequenceData.messages,
						activations: sequenceData.activations,
					},
					change_summary: 'Updated sequence diagram',
				}),
			});
			canvasDirty = false;
			editing = false;
			if (lockManager) {
				await lockManager.releaseLock();
			}
			lockConflictUser = null;
			await loadDiagram(diagram.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save sequence';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>{diagram?.name ?? 'Diagram Detail'} — Iris</title>
</svelte:head>

{#if loading}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex flex-wrap items-baseline gap-1">
			<li><a href="/diagrams" style="color: var(--color-primary)">Diagrams</a></li>
			<li aria-hidden="true">/</li>
			<li aria-current="page">{page.params.id}</li>
		</ol>
	</nav>
	<p style="color: var(--color-muted)">Loading diagram...</p>
{:else if error}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex flex-wrap items-baseline gap-1">
			<li><a href="/diagrams" style="color: var(--color-primary)">Diagrams</a></li>
			<li aria-hidden="true">/</li>
			<li aria-current="page">{page.params.id}</li>
		</ol>
	</nav>
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if diagram}
	<!-- Windowed browse sidebar: fixed right panel + margin on page content -->
	{#if windowedBrowseSidebar && selectedBrowseNode}
		<div
			style="position: fixed; top: 0; right: 0; bottom: 0; width: 316px; z-index: 40; padding: 8px; overflow-y: auto; background: var(--color-bg); border-left: 1px solid var(--color-border);"
		>
			<EntityDetailPanel
				entity={selectedBrowseNode.data}
				onclose={() => (selectedBrowseNode = null)}
				currentDiagramId={diagram?.id}
			/>
		</div>
	{/if}
	<!-- Windowed comments sidebar -->
	{#if windowedCommentsSidebar}
		<div
			style="position: fixed; top: 0; right: 0; bottom: 0; width: 316px; z-index: 40; padding: 8px; overflow-y: auto; background: var(--color-bg); border-left: 1px solid var(--color-border);"
		>
			<CommentsPanel
				targetType="diagram"
				targetId={diagram.id}
				onclose={() => (showCommentsSidebar = false)}
				oncount={(c) => (commentCount = c)}
			/>
		</div>
	{/if}
	<div style={(windowedBrowseSidebar || windowedCommentsSidebar) ? 'margin-right: 316px; margin-bottom: -24px; transition: margin-right 0.15s ease;' : 'margin-bottom: -24px; transition: margin-right 0.15s ease;'}>
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex flex-wrap items-baseline gap-1">
			<li><a href="/diagrams" style="color: var(--color-primary)">Diagrams</a></li>
			{#each ancestors as ancestor}
				<li class="flex items-baseline gap-1">
					<span aria-hidden="true">/</span>
					<a href="/diagrams/{ancestor.id}" style="color: var(--color-primary)">{ancestor.name}</a>
				</li>
			{/each}
			<li class="flex items-baseline gap-1">
				<span aria-hidden="true">/</span>
				<span aria-current="page">{diagram.name}</span>
			</li>
		</ol>
	</nav>
	<div class="flex items-center justify-between">
		<div>
			<div class="flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{diagram.name}</h1>
				{#if diagram.set_name}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-muted); border: 1px solid var(--color-border)">{diagram.set_name}</span>
				{/if}
			</div>
			<p class="mt-1 text-sm flex items-center gap-2 flex-wrap" style="color: var(--color-muted)">
				<span>{diagram.diagram_type}</span>
				{#if diagram.detected_notations && diagram.detected_notations.length > 0}
					{#each diagram.detected_notations as dn}
						<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">{dn}</span>
					{/each}
				{:else if diagram.notation}
					<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">{diagram.notation}</span>
				{/if}
			</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={toggleBookmark}
				disabled={bookmarkLoading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid {isBookmarked ? 'var(--color-primary)' : 'var(--color-border)'}; color: {isBookmarked ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {isBookmarked ? 'var(--color-surface, transparent)' : 'transparent'}"
			>
				{isBookmarked ? 'Bookmarked' : 'Bookmark'}
			</button>
			<button
				onclick={() => (showCloneDialog = true)}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Clone
			</button>
			<button
				onclick={() => (showDeleteDialog = true)}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
		</div>
	</div>

	<div class="mt-6 flex gap-4">
	<!-- Collapsible hierarchy sidebar -->
	{#if sidebarOpen}
		<aside
			data-hierarchy-sidebar
			style="width: 280px; max-height: calc(100vh - 216px); flex-shrink: 0; border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; position: sticky; top: 16px; align-self: flex-start"
			class="rounded-md border"
			style:border-color="var(--color-border)"
			style:background-color="var(--color-surface)"
			aria-label="Diagram hierarchy"
		>
			<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border); flex-shrink: 0">
				<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
				<div class="flex items-center gap-1">
					<button
						onclick={() => (treeDiagramsOnly = !treeDiagramsOnly)}
						class="rounded px-2 py-1 text-xs"
						style="border: 1px solid {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {treeDiagramsOnly ? 'var(--color-surface, transparent)' : 'transparent'}"
						title="Show only items with child diagrams"
						aria-pressed={treeDiagramsOnly}
					>
						Diagrams
					</button>
					<div style="position: relative">
						<button
							onclick={() => (showChildMenu = !showChildMenu)}
							class="rounded px-2 py-1 text-xs"
							style="background: var(--color-primary); color: white; border: 1px solid var(--color-primary)"
							title="Create child item"
						>
							+ Child
						</button>
						{#if showChildMenu}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								style="position: fixed; inset: 0; z-index: 9"
								onclick={() => (showChildMenu = false)}
								onkeydown={(e) => { if (e.key === 'Escape') showChildMenu = false; }}
							></div>
							<div
								style="position: absolute; top: 100%; right: 0; z-index: 10; min-width: 120px"
								class="mt-1 rounded border shadow-md"
								style:border-color="var(--color-border)"
								style:background-color="var(--color-surface)"
							>
								<button
									onclick={() => { showCreateChildDialog = true; showChildMenu = false; }}
									class="block w-full px-3 py-2 text-left text-xs hover:opacity-80"
									style="color: var(--color-fg)"
								>
									Diagram
								</button>
								<button
									onclick={() => { showCreateChildPackageDialog = true; showChildMenu = false; }}
									class="block w-full px-3 py-2 text-left text-xs hover:opacity-80"
									style="color: var(--color-fg); border-top: 1px solid var(--color-border)"
								>
									Package
								</button>
							</div>
						{/if}
					</div>
					<button
						onclick={() => { sidebarOpen = false; localStorage.setItem('iris-hierarchy-sidebar-open', 'false'); }}
						class="rounded p-1 text-xs"
						style="color: var(--color-muted)"
						aria-label="Close sidebar"
					>
						✕
					</button>
				</div>
			</div>
			<div class="p-2" style="flex-shrink: 0; border-bottom: 1px solid var(--color-border)">
				<input
					type="search"
					placeholder="Search tree..."
					bind:value={treeSearchQuery}
					class="w-full rounded border px-2 py-1 text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					aria-label="Search hierarchy"
				/>
			</div>
			<div use:restoreSidebarScroll class="px-2 pb-2" style="overflow-y: auto; flex: 1; min-height: 0">
				{#if hierarchyLoading}
					<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
				{:else if hierarchyTree.length === 0}
					<p class="p-2 text-xs" style="color: var(--color-muted)">No diagrams in this set.</p>
				{:else}
					<ul role="tree">
						{#each hierarchyTree as node (node.id)}
							<TreeNode {node} currentDiagramId={diagram.id} searchQuery={treeSearchQuery} showDiagramsOnly={treeDiagramsOnly} expandedIds={treeExpandedIds} />
						{/each}
					</ul>
				{/if}
			</div>
		</aside>
	{/if}

	<!-- Main content -->
	<div class="min-w-0 flex-1">
	<!-- Tab navigation with hierarchy toggle -->
	<div class="flex items-center gap-1 border-b" style="border-color: var(--color-border)">
		<button onclick={toggleSidebar} aria-label="Toggle hierarchy sidebar" aria-pressed={sidebarOpen} class="rounded p-1">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
				style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
				<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
			</svg>
		</button>
		<div class="flex gap-1" role="tablist" aria-label="Diagram sections">
			<button
				role="tab"
				aria-selected={activeTab === 'details'}
				onclick={() => { activeTab = 'details'; userSelectedTab = true; }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'details' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'details' ? 'var(--color-primary)' : 'transparent'}"
			>
				Details
			</button>
			<button
				role="tab"
				aria-selected={activeTab === 'canvas'}
				onclick={() => { activeTab = 'canvas'; userSelectedTab = true; }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'canvas' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'canvas' ? 'var(--color-primary)' : 'transparent'}"
			>
				Canvas
			</button>
			<button
				role="tab"
				aria-selected={activeTab === 'relationships'}
				onclick={() => { activeTab = 'relationships'; userSelectedTab = true; if (diagram) loadDiagramRelationships(diagram.id); }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'relationships' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'relationships' ? 'var(--color-primary)' : 'transparent'}"
			>
				Relationships
				{#if hasRelationships}
					<span
						style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-primary); margin-left: 4px; vertical-align: middle;"
						aria-label="{diagramRelationships.length + elementRelationships.length} relationship{diagramRelationships.length + elementRelationships.length === 1 ? '' : 's'}"
					></span>
				{/if}
			</button>
			<button
				role="tab"
				aria-selected={activeTab === 'versions'}
				onclick={() => { activeTab = 'versions'; userSelectedTab = true; }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
			>
				Version History
			</button>
		</div>
	</div>

	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			{@const modifiedByUsername = versions.length > 0 ? (versions[0].created_by_username ?? versions[0].created_by) : (diagram.created_by_username ?? diagram.created_by)}
			<!-- Inline edit toolbar -->
			<div class="mb-3 flex items-center gap-2">
				{#if editingOverview}
					<button
						onclick={saveMetadata}
						disabled={!overviewDirty || savingOverview}
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-success, #16a34a)"
					>
						{savingOverview ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={discardOverviewChanges}
						class="rounded px-3 py-1.5 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Discard
					</button>
					{#if overviewDirty}
						<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
					{/if}
				{:else}
					<button
						onclick={enterOverviewEdit}
						class="rounded px-3 py-1.5 text-sm text-white"
						style="background-color: var(--color-primary)"
					>
						Edit Details
					</button>
				{/if}
			</div>

			<Accordion.Root type="single" value="summary">
				<!-- Overview group (open by default) -->
				<Accordion.Item value="summary" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Overview
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">Name</dt>
							<dd>
								{#if editingOverview}
									<input
										type="text"
										bind:value={editName}
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									/>
								{:else}
									<span style="color: var(--color-fg)">{diagram.name}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
							<dd>
								{#if editingOverview}
									<textarea
										bind:value={editDescription}
										rows="3"
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									></textarea>
								{:else}
									<span style="color: var(--color-fg)">{diagram.description ?? 'No description'}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
							<dd style="color: var(--color-fg)">{diagram.diagram_type}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Notation</dt>
							<dd style="color: var(--color-fg)">{diagram.notation ?? 'simple'}</dd>

							{#if diagram.detected_notations && diagram.detected_notations.length > 0}
								<dt class="text-sm font-medium" style="color: var(--color-muted)">Detected Notations</dt>
								<dd>
									<div class="flex flex-wrap gap-1">
										{#each diagram.detected_notations as dn}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">{dn}</span>
										{/each}
									</div>
								</dd>
							{/if}

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Set</dt>
							<dd>
								<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg)">
									{diagram.set_name ?? 'Default'}
								</span>
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Tags</dt>
							<dd>
								{#if editingOverview}
									<TagInput
										tags={editTags}
										onaddtag={(tag) => { editTags = [...editTags, tag]; }}
										onremovetag={(tag) => { editTags = editTags.filter(t => t !== tag); }}
										{inheritedTags}
										suggestions={allTags}
									/>
								{:else if (diagram.tags ?? []).length > 0 || inheritedTags.length > 0}
									<div class="flex flex-wrap gap-1">
										{#each (diagram.tags ?? []) as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
										{#each inheritedTags as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-muted); color: white; opacity: 0.5" title="Inherited tag">{tag}</span>
										{/each}
									</div>
								{:else}
									<span style="color: var(--color-muted)">None</span>
								{/if}
							</dd>
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Details group (collapsed) -->
				<Accordion.Item value="diagram-details" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Details
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
							<dd class="text-sm" style="color: var(--color-fg)">{diagram.id}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
							<dd style="color: var(--color-fg)">{diagram.current_version ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Status</dt>
							<dd style="color: var(--color-fg)">{(diagram.metadata?.status as string) ?? '—'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Parent</dt>
							<dd class="flex items-center gap-2">
								{#if diagram.parent_package_id}
									{@const parentAncestor = ancestors.length > 0 ? ancestors[ancestors.length - 1] : null}
									{#if parentAncestor}
										<a href="/packages/{parentAncestor.id}" style="color: var(--color-primary)" class="text-sm">{parentAncestor.name}</a>
									{:else}
										<span class="text-sm" style="color: var(--color-fg)">{diagram.parent_package_id.slice(0, 8)}...</span>
									{/if}
								{:else}
									<span class="text-sm" style="color: var(--color-muted)">None — root diagram</span>
								{/if}
								<button
									onclick={() => (showParentPicker = true)}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-primary)"
								>
									Change
								</button>
								{#if diagram.parent_package_id}
									<button
										onclick={handleRemoveParent}
										class="rounded px-2 py-0.5 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-danger)"
									>
										Remove
									</button>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
							<dd style="color: var(--color-fg)">{diagram.created_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
							<dd style="color: var(--color-fg)">{diagram.created_by_username ?? diagram.created_by}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
							<dd style="color: var(--color-fg)">{diagram.updated_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified By</dt>
							<dd style="color: var(--color-fg)">{modifiedByUsername}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Template</dt>
							<dd>
								{#if editingOverview}
									<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
										<input type="checkbox" bind:checked={editIsTemplate} />
										{editIsTemplate ? 'Yes' : 'No'}
									</label>
								{:else}
									<span style="color: var(--color-fg)">{isTemplate ? 'Yes' : 'No'}</span>
								{/if}
							</dd>
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Extended group (collapsed) -->
				<Accordion.Item value="extended" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Extended
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						{#if diagram.metadata?.stereotype || (Array.isArray(diagram.metadata?.tagged_values) && (diagram.metadata.tagged_values as unknown[]).length > 0)}
							<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
								{#if diagram.metadata?.stereotype}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Stereotype</dt>
									<dd style="color: var(--color-fg)">{diagram.metadata.stereotype}</dd>
								{/if}

								{#if Array.isArray(diagram.metadata?.tagged_values) && (diagram.metadata.tagged_values as unknown[]).length > 0}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Tagged Values</dt>
									<dd>
										<table class="w-full text-sm" style="color: var(--color-fg)">
											<thead>
												<tr style="border-bottom: 1px solid var(--color-border)">
													<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Property</th>
													<th class="py-1 text-left font-medium" style="color: var(--color-muted)">Value</th>
												</tr>
											</thead>
											<tbody>
												{#each diagram.metadata.tagged_values as tv}
													{@const tvObj = tv as {property?: string; value?: string}}
													<tr style="border-bottom: 1px solid var(--color-border)">
														<td class="py-1 pr-4">{tvObj.property ?? ''}</td>
														<td class="py-1">{tvObj.value ?? ''}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</dd>
								{/if}
							</dl>
						{:else}
							<p class="text-sm" style="color: var(--color-muted)">No extended metadata available.</p>
						{/if}
					</Accordion.Content>
				</Accordion.Item>
			</Accordion.Root>
		{:else if activeTab === 'canvas'}
			{#if lockConflictUser}
				<div class="mb-3 flex items-center gap-2 rounded border px-4 py-2 text-sm" style="border-color: var(--color-warning, #f59e0b); background: rgba(245, 158, 11, 0.1); color: var(--color-fg)">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; color: var(--color-warning, #f59e0b)"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
					This diagram is being edited by <strong>{lockConflictUser}</strong>. Try again later.
					<button onclick={() => (lockConflictUser = null)} class="ml-auto text-xs" style="color: var(--color-muted)">Dismiss</button>
				</div>
			{/if}
			{#if canvasType === 'sequence'}
				<!-- Sequence diagram toolbar -->
				<div class="mb-3 flex flex-wrap items-center gap-2 gap-y-2">
					{#if editing}
						<!-- Create group -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => (showAddParticipant = true)}
								class="rounded px-3 py-1.5 text-sm text-white"
								style="background-color: var(--color-primary)"
							>
								Add Participant
							</button>
							<button
								onclick={() => (showAddMessage = true)}
								disabled={sequenceData.participants.length < 2}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-primary)"
							>
								Add Message
							</button>
						</div>
						<!-- Edit group -->
						<div class="flex items-center gap-2">
							<button
								onclick={handleDeleteSelected}
								disabled={!selectedMessageId}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Delete Selected
							</button>
						</div>
						<!-- Persist group -->
						<div class="flex items-center gap-2">
							<button
								onclick={saveSequence}
								disabled={saving || !canvasDirty}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-success, #16a34a)"
							>
								{saving ? 'Saving...' : 'Save'}
							</button>
							<button
								onclick={discardChanges}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Discard
							</button>
							{#if canvasDirty}
								<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
							{/if}
						</div>
					{:else}
						<button
							onclick={handleStartEditing}
							class="rounded px-3 py-1.5 text-sm"
							style="background-color: var(--color-primary); color: white"
						>
							Edit Canvas
						</button>
					{/if}
					<!-- View group (always visible) -->
					<div class="ml-auto flex items-center gap-2">
						{#if notation}
							<ThemeSelector {notation} />
						{/if}
						<div class="relative">
							<button
								onclick={() => (showExportMenu = !showExportMenu)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-haspopup="true"
								aria-expanded={showExportMenu}
							>
								Export
							</button>
							{#if showExportMenu}
								<div
									class="absolute right-0 z-50 mt-1 min-w-[140px] rounded border py-1 shadow-lg"
									style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
									role="menu"
								>
									<button onclick={handleExportSvg} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">SVG</button>
									<button onclick={handleExportPng} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PNG</button>
									<button onclick={handleExportPdf} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PDF</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Visio</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Draw.io</button>
								</div>
							{/if}
						</div>
						{#if !editing}
							<button
								onclick={toggleCommentsSidebar}
								class="rounded px-3 py-1.5 text-sm flex items-center gap-1.5"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-pressed={showCommentsSidebar}
							>
								Comments
								<span class="inline-flex items-center justify-center rounded text-xs font-medium" style="min-width: 20px; height: 20px; padding: 0 5px; background: var(--color-muted); color: white">{commentCount}</span>
							</button>
						{/if}
						<button
							onclick={() => (focusMode = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="border: 1px solid var(--color-border); color: var(--color-fg)"
							aria-label="Full screen"
							title="Full screen"
						>
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle">
								<polyline points="15 3 21 3 21 9"></polyline>
								<polyline points="9 21 3 21 3 15"></polyline>
								<polyline points="21 15 21 21 15 21"></polyline>
								<polyline points="3 9 3 3 9 3"></polyline>
							</svg>
						</button>
					</div>
				</div>

				<!-- Sequence diagram rendering -->
				{#if sequenceData.participants.length === 0 && !editing}
					<div class="flex flex-col items-center justify-center gap-3 rounded border p-8" style="border-color: var(--color-border); min-height: 300px">
						<p style="color: var(--color-muted)">This sequence diagram has no participants yet.</p>
						<button
							onclick={handleStartEditing}
							class="rounded px-4 py-2 text-sm text-white"
							style="background-color: var(--color-primary)"
						>
							Start Building
						</button>
					</div>
				{:else}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)}>
							<div style="display: flex; width: 100%; height: 100%;">
								{#if sidebarOpen}
									<aside
										data-hierarchy-sidebar
										style="width: 280px; max-height: calc(100% - 16px); flex-shrink: 0; overflow: hidden; display: flex; flex-direction: column; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; margin: 8px 0 8px 8px; align-self: flex-start;"
									>
										<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border); flex-shrink: 0">
											<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
											<div class="flex items-center gap-1">
												<button
													onclick={() => (treeDiagramsOnly = !treeDiagramsOnly)}
													class="rounded px-2 py-1 text-xs"
													style="border: 1px solid {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}"
													title="Show only items with child diagrams"
													aria-pressed={treeDiagramsOnly}
												>Diagrams</button>
												<button
													onclick={() => { sidebarOpen = false; localStorage.setItem('iris-hierarchy-sidebar-open', 'false'); }}
													class="rounded p-1 text-xs"
													style="color: var(--color-muted)"
													aria-label="Close sidebar"
												>✕</button>
											</div>
										</div>
										<div class="p-2" style="flex-shrink: 0; border-bottom: 1px solid var(--color-border)">
											<input type="search" placeholder="Search tree..." bind:value={treeSearchQuery}
												class="w-full rounded border px-2 py-1 text-xs"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
												aria-label="Search hierarchy" />
										</div>
										<div class="px-2 py-2" style="overflow-y: auto; flex: 1; min-height: 0">
											{#if hierarchyLoading}
												<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
											{:else if hierarchyTree.length === 0}
												<p class="p-2 text-xs" style="color: var(--color-muted)">No diagrams in this set.</p>
											{:else}
												<ul role="tree">
													{#each hierarchyTree as node (node.id)}
														<TreeNode {node} currentDiagramId={diagram.id} searchQuery={treeSearchQuery} showDiagramsOnly={treeDiagramsOnly} expandedIds={treeExpandedIds} />
													{/each}
												</ul>
											{/if}
																					</div>
									</aside>
								{/if}
							<div style="flex: 1; min-width: 0; overflow: hidden; position: relative">
								<button
									onclick={toggleSidebar}
									aria-label="Toggle hierarchy sidebar"
									aria-pressed={sidebarOpen}
									style="position: absolute; top: 12px; left: 12px; z-index: 10; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer;"
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
										style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
										<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
									</svg>
								</button>
								{#if !editing}
									<button
										onclick={toggleCommentsSidebar}
										aria-label="Toggle comments"
										aria-pressed={showCommentsSidebar}
										style="position: absolute; top: 12px; left: 56px; z-index: 10; height: 36px; display: flex; align-items: center; gap: 6px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer; font-size: 13px; color: var(--color-fg);"
									>
										Comments
										<span class="inline-flex items-center justify-center rounded text-xs font-medium" style="min-width: 20px; height: 20px; padding: 0 5px; background: var(--color-muted); color: white">{commentCount}</span>
									</button>
								{/if}
								<SequenceDiagram
									data={sequenceData}
									{selectedMessageId}
									onmessageselect={(id) => (selectedMessageId = id)}
									onparticipantselect={!editing ? handleSequenceParticipantSelect : undefined}
									viewBox={seqViewport.viewBox}
									onwheel={seqViewport.handleWheel}
									onpointerdown={seqViewport.handlePointerDown}
									onpointermove={seqViewport.handlePointerMove}
									onpointerup={seqViewport.handlePointerUp}
								/>
								<SequenceToolbar
									onzoomin={seqViewport.zoomIn}
									onzoomout={seqViewport.zoomOut}
									onfitview={seqViewport.fitView}
								/>
								<div class="canvas-mode-badge{editing ? ' canvas-mode-badge--edit' : ''}" aria-live="polite">{editing ? 'Edit Mode' : 'Browse Mode'}</div>
							</div>
							{#if !editing && showCommentsSidebar}
								<div style="width: 300px; flex-shrink: 0; margin: 8px 8px 8px 0; overflow-y: auto; max-height: calc(100% - 16px); align-self: flex-start; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; padding: 12px;">
									<CommentsPanel
										targetType="diagram"
										targetId={diagram.id}
										onclose={() => (showCommentsSidebar = false)}
										oncount={(c) => (commentCount = c)}
									/>
								</div>
							{/if}
							</div>
						</FocusView>
					{:else}
					<div style="height: calc(100vh - 317px); border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden; position: relative">
						<SequenceDiagram
							data={sequenceData}
							{selectedMessageId}
							onmessageselect={(id) => (selectedMessageId = id)}
							onparticipantselect={!editing ? handleSequenceParticipantSelect : undefined}
							viewBox={seqViewport.viewBox}
							onwheel={seqViewport.handleWheel}
							onpointerdown={seqViewport.handlePointerDown}
							onpointermove={seqViewport.handlePointerMove}
							onpointerup={seqViewport.handlePointerUp}
						/>
						<SequenceToolbar
							onzoomin={seqViewport.zoomIn}
							onzoomout={seqViewport.zoomOut}
							onfitview={seqViewport.fitView}
						/>
						<div class="canvas-mode-badge{editing ? ' canvas-mode-badge--edit' : ''}" aria-live="polite">{editing ? 'Edit Mode' : 'Browse Mode'}</div>
					</div>
					{/if}
				{/if}
			{:else}
				<!-- Canvas toolbar -->
				<div class="mb-3 flex flex-wrap items-center gap-2 gap-y-2">
					{#if editing}
						<!-- Create group -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => (showAddElement = true)}
								class="rounded px-3 py-1.5 text-sm text-white"
								style="background-color: var(--color-primary)"
							>
								Add Element
							</button>
							<button
								onclick={() => (showElementPicker = true)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Link Element
							</button>
							<button
								onclick={() => (showDiagramPicker = true)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Add Diagram
							</button>
						</div>
						<!-- Edit group -->
						<div class="flex items-center gap-2">
							{#if selectedNodeIsLinkedElement}
								<button
									onclick={handleEditElementClick}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-primary); color: var(--color-primary)"
								>
									Edit Element
								</button>
							{/if}
							{#if selectedEditNodeId}
								<button
									onclick={() => selectedEditNodeId && handleDeleteNode(selectedEditNodeId)}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-danger); color: var(--color-danger)"
								>
									Remove
								</button>
							{/if}
							<button
								onclick={() => selectedEdgeId && handleDeleteEdge(selectedEdgeId)}
								disabled={!selectedEdgeId}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Delete Edge
							</button>
								<button
								onclick={handleUndo}
								disabled={!history.canUndo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Undo"
								title="Undo (Ctrl/Cmd+Z)"
							>
								Undo
							</button>
							<button
								onclick={handleRedo}
								disabled={!history.canRedo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Redo"
								title="Redo (Ctrl/Cmd+Y)"
							>
								Redo
							</button>
						</div>
						<!-- Persist group -->
						<div class="flex items-center gap-2">
							<button
								onclick={saveCanvas}
								disabled={saving || !canvasDirty}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-success, #16a34a)"
							>
								{saving ? 'Saving...' : 'Save'}
							</button>
							<button
								onclick={discardChanges}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Discard
							</button>
							{#if canvasDirty}
								<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
							{/if}
						</div>
					{:else}
						<button
							onclick={handleStartEditing}
							class="rounded px-3 py-1.5 text-sm"
							style="background-color: var(--color-primary); color: white"
						>
							Edit Canvas
						</button>
					{/if}
					<!-- View group (always visible) -->
					<div class="ml-auto flex items-center gap-2">
						{#if notation}
							<ThemeSelector {notation} />
						{/if}
						<div class="relative">
							<button
								onclick={() => (showExportMenu = !showExportMenu)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-haspopup="true"
								aria-expanded={showExportMenu}
							>
								Export
							</button>
							{#if showExportMenu}
								<div
									class="absolute right-0 z-50 mt-1 min-w-[140px] rounded border py-1 shadow-lg"
									style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
									role="menu"
								>
									<button onclick={handleExportSvg} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">SVG</button>
									<button onclick={handleExportPng} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PNG</button>
									<button onclick={handleExportPdf} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PDF</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Visio</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Draw.io</button>
								</div>
							{/if}
						</div>
						{#if !editing}
							<button
								onclick={toggleCommentsSidebar}
								class="rounded px-3 py-1.5 text-sm flex items-center gap-1.5"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-pressed={showCommentsSidebar}
							>
								Comments
								<span class="inline-flex items-center justify-center rounded text-xs font-medium" style="min-width: 20px; height: 20px; padding: 0 5px; background: var(--color-muted); color: white">{commentCount}</span>
							</button>
						{/if}
						<button
							onclick={() => (focusMode = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="border: 1px solid var(--color-border); color: var(--color-fg)"
							aria-label="Full screen"
							title="Full screen"
						>
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle">
								<polyline points="15 3 21 3 21 9"></polyline>
								<polyline points="9 21 3 21 3 15"></polyline>
								<polyline points="21 15 21 21 15 21"></polyline>
								<polyline points="3 9 3 3 9 3"></polyline>
							</svg>
						</button>
					</div>
				</div>

				<!-- Canvas area -->
				{#if editing}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)}>
							<div style="display: flex; flex-direction: column; width: 100%; height: 100%;">
								<!-- Toolbar inside FocusView so edit controls are visible -->
								<div class="flex items-center gap-4 p-2" style="border-bottom: 1px solid var(--color-border); background: var(--color-surface); flex-shrink: 0;">
									<button onclick={toggleSidebar} aria-label="Toggle hierarchy sidebar" aria-pressed={sidebarOpen} class="rounded p-1">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
											style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
											<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
										</svg>
									</button>
									<div class="flex items-center gap-2">
										<button onclick={() => (showAddElement = true)} class="rounded px-3 py-1.5 text-sm text-white" style="background-color: var(--color-primary)">Add Element</button>
										<button onclick={() => (showElementPicker = true)} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Link Element</button>
										<button onclick={() => (showDiagramPicker = true)} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Add Diagram</button>
									</div>
									<div class="flex items-center gap-2">
										<button onclick={handleUndo} disabled={!history.canUndo} class="rounded px-3 py-1.5 text-sm disabled:opacity-50" style="border: 1px solid var(--color-border); color: var(--color-fg)" aria-label="Undo">Undo</button>
										<button onclick={handleRedo} disabled={!history.canRedo} class="rounded px-3 py-1.5 text-sm disabled:opacity-50" style="border: 1px solid var(--color-border); color: var(--color-fg)" aria-label="Redo">Redo</button>
									</div>
									<div class="flex items-center gap-2">
										<button onclick={saveCanvas} disabled={saving || !canvasDirty} class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50" style="background-color: var(--color-success, #16a34a)">{saving ? 'Saving...' : 'Save'}</button>
										<button onclick={discardChanges} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Discard</button>
										{#if canvasDirty}
											<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
										{/if}
									</div>
								</div>
								<div style="display: flex; flex: 1; min-height: 0;">
									{#if sidebarOpen}
										<aside
											data-hierarchy-sidebar
											style="width: 280px; max-height: calc(100% - 16px); flex-shrink: 0; overflow: hidden; display: flex; flex-direction: column; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; margin: 8px 0 8px 8px; align-self: flex-start;"
										>
											<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border); flex-shrink: 0">
												<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
												<div class="flex items-center gap-1">
													<button
														onclick={() => (treeDiagramsOnly = !treeDiagramsOnly)}
														class="rounded px-2 py-1 text-xs"
														style="border: 1px solid {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}"
														title="Show only items with child diagrams"
														aria-pressed={treeDiagramsOnly}
													>Diagrams</button>
													<button
														onclick={() => { sidebarOpen = false; localStorage.setItem('iris-hierarchy-sidebar-open', 'false'); }}
														class="rounded p-1 text-xs"
														style="color: var(--color-muted)"
														aria-label="Close sidebar"
													>✕</button>
												</div>
											</div>
											<div class="p-2" style="flex-shrink: 0; border-bottom: 1px solid var(--color-border)">
												<input type="search" placeholder="Search tree..." bind:value={treeSearchQuery}
													class="w-full rounded border px-2 py-1 text-xs"
													style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
													aria-label="Search hierarchy" />
											</div>
											<div class="px-2 py-2" style="overflow-y: auto; flex: 1; min-height: 0">
												{#if hierarchyLoading}
													<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
												{:else if hierarchyTree.length === 0}
													<p class="p-2 text-xs" style="color: var(--color-muted)">No diagrams in this set.</p>
												{:else}
													<ul role="tree">
														{#each hierarchyTree as node (node.id)}
															<TreeNode {node} currentDiagramId={diagram.id} searchQuery={treeSearchQuery} showDiagramsOnly={treeDiagramsOnly} expandedIds={treeExpandedIds} />
														{/each}
													</ul>
												{/if}
																							</div>
										</aside>
									{/if}
									<div style="flex: 1; min-width: 0; overflow: hidden">
										<UnifiedCanvas
											{notation}
											{preferredThemeId}
												bind:nodes={canvasNodes}
											bind:edges={canvasEdges}
											oncreatenode={() => (showAddElement = true)}
											ondeletenode={handleDeleteNode}
											onconnectnodes={handleConnectNodes}
											ondeleteedge={handleDeleteEdge}
											onreconnectedge={handleReconnectEdge}
											onedgeselect={handleEdgeSelect}
											onnodeselect={handleNodeSelect}
											onundo={handleUndo}
											onredo={handleRedo}
											onnodedragstart={handleNodeDragStart}
											ontogglemode={handleToggleToBrowseMode}
											panX={selectedEditNodeId && selectedNodeVisual ? -308 : 0}
										/>
									</div>
									{#if selectedEditNodeId && selectedNodeVisual}
										<div style="width: 300px; flex-shrink: 0; margin: 8px 8px 8px 0; overflow-y: auto; max-height: calc(100% - 16px); align-self: flex-start; display: flex; flex-direction: column; gap: 8px;">
											<ElementEditPanel entityId={selectedNodeEntityId} nodeId={selectedEditNodeId} {notation} nodeLabel={selectedNodeLabel} nodeDescription={selectedNodeDescription} nodeEntityType={selectedNodeEntityType} />
											<NodeStylePanel nodeId={selectedEditNodeId} visual={selectedNodeVisual} {notation} entityType={selectedNodeEntityType} />
										</div>
									{/if}
								</div>
							</div>
						</FocusView>
					{:else}
					<div class="flex gap-4">
						<div class="flex-1" style="height: calc(100vh - 317px); border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
							<UnifiedCanvas
								{notation}
								{preferredThemeId}
									bind:nodes={canvasNodes}
								bind:edges={canvasEdges}
								oncreatenode={() => (showAddElement = true)}
								ondeletenode={handleDeleteNode}
								onconnectnodes={handleConnectNodes}
								ondeleteedge={handleDeleteEdge}
								onreconnectedge={handleReconnectEdge}
								onedgeselect={handleEdgeSelect}
								onnodeselect={handleNodeSelect}
								onundo={handleUndo}
								onredo={handleRedo}
								onnodedragstart={handleNodeDragStart}
								ontogglemode={handleToggleToBrowseMode}
								panX={selectedEditNodeId && selectedNodeVisual ? -308 : 0}
							/>
						</div>
						{#if selectedEditNodeId && selectedNodeVisual}
							<div style="width: 300px; display: flex; flex-direction: column; gap: 8px;">
								<ElementEditPanel entityId={selectedNodeEntityId} nodeId={selectedEditNodeId} {notation} nodeLabel={selectedNodeLabel} nodeDescription={selectedNodeDescription} nodeEntityType={selectedNodeEntityType} />
								<NodeStylePanel nodeId={selectedEditNodeId} visual={selectedNodeVisual} {notation} entityType={selectedNodeEntityType} />
							</div>
						{/if}
					</div>
					{#if selectedEdgeId && selectedEdgeData}
						<div class="mt-2">
							<EdgeStylePanel edgeId={selectedEdgeId} data={selectedEdgeData} />
						</div>
					{/if}
					{/if}
				{:else if canvasNodes.length === 0}
					<div class="flex flex-col items-center justify-center gap-3 rounded border p-8" style="border-color: var(--color-border); min-height: 300px">
						<p style="color: var(--color-muted)">This diagram has no canvas content yet.</p>
						<button
							onclick={handleStartEditing}
							class="rounded px-4 py-2 text-sm text-white"
							style="background-color: var(--color-primary)"
						>
							Start Building
						</button>
					</div>
				{:else}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)} hideExit={!!selectedBrowseNode || showCommentsSidebar}>
							<div style="display: flex; width: 100%; height: 100%;">
								{#if sidebarOpen}
									<aside
										data-hierarchy-sidebar
										style="width: 280px; max-height: calc(100% - 16px); flex-shrink: 0; overflow: hidden; display: flex; flex-direction: column; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; margin: 8px 0 8px 8px; align-self: flex-start;"
									>
										<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border); flex-shrink: 0">
											<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
											<div class="flex items-center gap-1">
												<button
													onclick={() => (treeDiagramsOnly = !treeDiagramsOnly)}
													class="rounded px-2 py-1 text-xs"
													style="border: 1px solid {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}"
													title="Show only items with child diagrams"
													aria-pressed={treeDiagramsOnly}
												>Diagrams</button>
												<button
													onclick={() => { sidebarOpen = false; localStorage.setItem('iris-hierarchy-sidebar-open', 'false'); }}
													class="rounded p-1 text-xs"
													style="color: var(--color-muted)"
													aria-label="Close sidebar"
												>✕</button>
											</div>
										</div>
										<div class="p-2" style="flex-shrink: 0; border-bottom: 1px solid var(--color-border)">
											<input type="search" placeholder="Search tree..." bind:value={treeSearchQuery}
												class="w-full rounded border px-2 py-1 text-xs"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
												aria-label="Search hierarchy" />
										</div>
										<div class="px-2 py-2" style="overflow-y: auto; flex: 1; min-height: 0">
											{#if hierarchyLoading}
												<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
											{:else if hierarchyTree.length === 0}
												<p class="p-2 text-xs" style="color: var(--color-muted)">No diagrams in this set.</p>
											{:else}
												<ul role="tree">
													{#each hierarchyTree as node (node.id)}
														<TreeNode {node} currentDiagramId={diagram.id} searchQuery={treeSearchQuery} showDiagramsOnly={treeDiagramsOnly} expandedIds={treeExpandedIds} />
													{/each}
												</ul>
											{/if}
																					</div>
									</aside>
								{/if}
								<div style="flex: 1; min-width: 0; position: relative; overflow: hidden">
									<button
										onclick={toggleSidebar}
										aria-label="Toggle hierarchy sidebar"
										aria-pressed={sidebarOpen}
										style="position: absolute; top: 12px; left: 12px; z-index: 10; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer;"
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
											style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
											<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
										</svg>
									</button>
									<button
										onclick={toggleCommentsSidebar}
										aria-label="Toggle comments"
										aria-pressed={showCommentsSidebar}
										style="position: absolute; top: 12px; left: 56px; z-index: 10; height: 36px; display: flex; align-items: center; gap: 6px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer; font-size: 13px; color: var(--color-fg);"
									>
										Comments
										<span class="inline-flex items-center justify-center rounded text-xs font-medium" style="min-width: 20px; height: 20px; padding: 0 5px; background: var(--color-muted); color: white">{commentCount}</span>
									</button>
									<UnifiedCanvas
										{notation}
										{preferredThemeId}
										nodes={canvasNodes}
										edges={canvasEdges}
										browseMode={true}
										onnodeselect={handleBrowseNodeSelect}
										ontogglemode={handleStartEditing}
										panX={(selectedBrowseNode || showCommentsSidebar) ? -308 : 0}
									/>
								</div>
								{#if selectedBrowseNode}
									<div style="width: 300px; flex-shrink: 0; margin: 8px 8px 8px 0; overflow-y: auto; max-height: calc(100% - 16px); align-self: flex-start; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px;">
										<EntityDetailPanel
											entity={selectedBrowseNode.data}
											onclose={() => (selectedBrowseNode = null)}
											currentDiagramId={diagram?.id}
										/>
									</div>
								{:else if showCommentsSidebar}
									<div style="width: 300px; flex-shrink: 0; margin: 8px 8px 8px 0; overflow-y: auto; max-height: calc(100% - 16px); align-self: flex-start; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; padding: 12px;">
										<CommentsPanel
											targetType="diagram"
											targetId={diagram.id}
											onclose={() => (showCommentsSidebar = false)}
											oncount={(c) => (commentCount = c)}
										/>
									</div>
								{/if}
							</div>
						</FocusView>
					{:else}
					<div style="height: calc(100vh - 317px); border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
						<UnifiedCanvas
							{notation}
							{preferredThemeId}
							nodes={canvasNodes}
							edges={canvasEdges}
							browseMode={true}
							onnodeselect={handleBrowseNodeSelect}
							ontogglemode={handleStartEditing}
							panX={(selectedBrowseNode || showCommentsSidebar) ? -316 : 0}
						/>
					</div>
					{/if}
				{/if}
			{/if}
		{:else if activeTab === 'relationships'}
			<!-- Add relationship buttons -->
			<div class="mb-4 flex gap-2">
				<button
					onclick={handleStartAddElementRel}
					class="rounded px-3 py-1.5 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Add Element Relationship
				</button>
				<button
					onclick={handleStartAddDiagramRel}
					class="rounded px-3 py-1.5 text-sm"
					style="border: 1px solid var(--color-primary); color: var(--color-primary)"
				>
					Add Diagram Relationship
				</button>
			</div>

			{#if relationshipsLoading}
				<p style="color: var(--color-muted)">Loading relationships...</p>
			{:else if diagramRelationships.length === 0 && elementRelationships.length === 0}
				<p style="color: var(--color-muted)">No relationships found.</p>
			{:else}
				<!-- Element relationships (within this diagram's canvas) -->
				{#if elementRelationships.length > 0}
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Element Relationships ({elementRelationships.length})</h3>
					<table class="mb-6 w-full text-sm">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="py-2 text-left" style="color: var(--color-muted)">Source</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Target</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
							</tr>
						</thead>
						<tbody>
							{#each elementRelationships as rel}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="py-2">
										<a href="/elements/{rel.source_element_id}" style="color: var(--color-primary)">{rel.source_name || rel.source_element_id}</a>
									</td>
									<td class="py-2">
										<a href="/elements/{rel.target_element_id}" style="color: var(--color-primary)">{rel.target_name || rel.target_element_id}</a>
									</td>
									<td class="py-2">
										<span class="inline-block rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg)">
											{rel.relationship_type}
										</span>
									</td>
									<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}

				<!-- Diagram-to-diagram relationships -->
				{#if diagramRelationships.length > 0}
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Diagram Relationships ({diagramRelationships.length})</h3>
					<table class="w-full text-sm">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="py-2 text-left" style="color: var(--color-muted)">Direction</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Related Diagram</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each diagramRelationships as rel}
								{@const isSource = rel.source_package_id === diagram.id}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="py-2" style="color: var(--color-fg)">{isSource ? 'Outgoing' : 'Incoming'}</td>
									<td class="py-2">
										<a
											href="/diagrams/{isSource ? rel.target_package_id : rel.source_package_id}"
											style="color: var(--color-primary)"
										>
											{isSource ? rel.target_name : rel.source_name}
										</a>
									</td>
									<td class="py-2">
										<span class="inline-block rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg)">
											{rel.relationship_type}
										</span>
									</td>
									<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
									<td class="py-2">
										{#if editing}
											<button
												onclick={() => deleteDiagramRelationship(rel.id)}
												class="text-xs"
												style="color: var(--color-danger, #dc2626)"
											>
												Delete
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			{/if}
		{:else if activeTab === 'versions'}
			<VersionHistory {versions} loading={versionsLoading} currentVersion={diagram?.current_version} onrollback={handleDiagramRollback} />
		{/if}
	</div>

	</div><!-- end main content flex-1 -->
	</div><!-- end sidebar + content flex wrapper -->
	</div><!-- end windowed browse sidebar margin wrapper -->

	<DiagramDialog
		open={showCreateChildDialog}
		mode="create"
		initialName=""
		initialType={diagram.diagram_type}
		initialDescription=""
		onsave={handleCreateChild}
		oncancel={() => (showCreateChildDialog = false)}
	/>

	{#if showCreateChildPackageDialog}
		<div style="position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4)">
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="rounded-lg p-6 shadow-lg"
				style="background: var(--color-bg); border: 1px solid var(--color-border); width: 400px; max-width: 90vw"
				onkeydown={(e) => { if (e.key === 'Escape') { showCreateChildPackageDialog = false; childPackageName = ''; childPackageDescription = ''; } }}
			>
				<h3 class="mb-4 text-lg font-semibold" style="color: var(--color-fg)">Create Package</h3>
				<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Name
					<input
						type="text"
						bind:value={childPackageName}
						class="mt-1 block w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
						placeholder="Package name"
					/>
				</label>
				<label class="mb-4 mt-3 block text-sm font-medium" style="color: var(--color-fg)">
					Description
					<textarea
						bind:value={childPackageDescription}
						rows="3"
						class="mt-1 block w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
						placeholder="Optional description"
					></textarea>
				</label>
				<div class="flex justify-end gap-2">
					<button
						onclick={() => { showCreateChildPackageDialog = false; childPackageName = ''; childPackageDescription = ''; }}
						class="rounded px-4 py-2 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Cancel
					</button>
					<button
						onclick={handleCreateChildPackage}
						disabled={!childPackageName.trim()}
						class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
						style="background: var(--color-primary)"
					>
						Create
					</button>
				</div>
			</div>
		</div>
	{/if}

	<PackagePicker
		open={showParentPicker}
		onselect={handleSetParent}
		oncancel={() => (showParentPicker = false)}
		title="Select Parent Package"
		subtitle="Choose a package to contain this diagram."
	/>

	<DiagramDialog
		open={showCloneDialog}
		mode="create"
		initialName="{diagram.name} (Copy)"
		initialType={diagram.diagram_type}
		initialDescription={diagram.description ?? ''}
		onsave={handleClone}
		oncancel={() => (showCloneDialog = false)}
	/>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Diagram"
		message="Are you sure you want to delete '{diagram.name}'? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>

	<EntityDialog
		open={showAddElement}
		mode="create"
		notation={notation}
		diagramType={diagram?.diagram_type}
		onsave={handleAddElement}
		oncancel={() => (showAddElement = false)}
	/>

	<EntityDialog
		open={showEditElement}
		mode="edit"
		notation={notation}
		diagramType={diagram?.diagram_type}
		initialName={editElementData?.name ?? ''}
		initialType={(editElementData?.element_type ?? 'component') as SimpleEntityType}
		initialDescription={editElementData?.description ?? ''}
		onsave={handleEditElementSave}
		oncancel={() => { showEditElement = false; editElementData = null; }}
	/>

	<RelationshipDialog
		open={showRelationshipDialog}
		sourceName={pendingSourceName}
		targetName={pendingTargetName}
		{notation}
		onsave={handleRelationshipSave}
		oncancel={handleRelationshipCancel}
	/>

	<ElementPicker
		open={showElementPicker}
		onselect={handleLinkElement}
		oncancel={() => (showElementPicker = false)}
	/>

	<DiagramPicker
		open={showDiagramPicker}
		onselect={handleInsertDiagram}
		oncancel={() => (showDiagramPicker = false)}
		excludeDiagramId={diagram?.id}
	/>

	<ParticipantDialog
		open={showAddParticipant}
		onsave={handleAddParticipant}
		oncancel={() => (showAddParticipant = false)}
	/>

	<MessageDialog
		open={showAddMessage}
		participants={sequenceData.participants}
		onsave={handleAddMessage}
		oncancel={() => (showAddMessage = false)}
	/>

	<NodeDeleteDialog
		open={showNodeDeleteDialog}
		nodeName={deleteNodeName}
		isModelRef={deleteNodeIsDiagramRef}
		onremove={handleRemoveNodeFromCanvas}
		ondelete={handleCascadeDeleteElement}
		oncancel={() => { showNodeDeleteDialog = false; deleteNodeId = null; }}
	/>

	<!-- Add element relationship from tab: source picker -->
	<ElementPicker
		open={addElementRelStep === 'source'}
		title="Select Source Element"
		subtitle="Choose the source element for the relationship."
		onselect={handleElementRelSourceSelected}
		oncancel={() => (addElementRelStep = null)}
	/>

	<!-- Add element relationship from tab: target picker -->
	<ElementPicker
		open={addElementRelStep === 'target'}
		title="Select Target Element"
		subtitle="Choose the target element for the relationship."
		onselect={handleElementRelTargetSelected}
		oncancel={() => (addElementRelStep = null)}
	/>

	<!-- Add element relationship from tab: details dialog -->
	<RelationshipDialog
		open={addElementRelStep === 'details'}
		sourceName={addElementRelSource?.name ?? ''}
		targetName={addElementRelTarget?.name ?? ''}
		onsave={handleElementRelSave}
		oncancel={() => (addElementRelStep = null)}
	/>

	<!-- Add diagram relationship from tab: diagram picker -->
	<DiagramPicker
		open={showAddDiagramRelPicker}
		title="Select Target Diagram"
		onselect={handleDiagramRelTargetSelected}
		oncancel={() => (showAddDiagramRelPicker = false)}
		excludeDiagramId={diagram?.id}
	/>

	<!-- Add diagram relationship from tab: details dialog -->
	<RelationshipDialog
		open={showAddDiagramRelDialog}
		sourceName={diagram?.name ?? ''}
		targetName={addDiagramRelTarget?.name ?? ''}
		onsave={handleDiagramRelSave}
		oncancel={() => (showAddDiagramRelDialog = false)}
	/>

	<!-- Unsaved changes confirmation -->
	{#if showUnsavedChangesDialog}
		<dialog
			open
			class="fixed inset-0 z-50 flex items-center justify-center rounded-lg p-6 shadow-lg backdrop:bg-black/50"
			style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
			aria-labelledby="unsaved-changes-title"
		>
			<h2 id="unsaved-changes-title" class="text-lg font-bold">Unsaved Changes</h2>
			<p class="mt-2 text-sm" style="color: var(--color-muted)">
				You have unsaved changes. Would you like to save or discard them?
			</p>
			<div class="mt-4 flex justify-end gap-3">
				<button
					onclick={handleUnsavedCancel}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Cancel
				</button>
				<button
					onclick={handleUnsavedDiscard}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-danger); color: var(--color-danger)"
				>
					Discard
				</button>
				<button
					onclick={handleUnsavedSave}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-success, #16a34a)"
				>
					Save
				</button>
			</div>
		</dialog>
	{/if}

	<!-- "Add to canvas?" prompt -->
	{#if showAddToCanvasPrompt}
		<dialog
			open
			class="fixed inset-0 z-50 flex items-center justify-center rounded-lg p-6 shadow-lg backdrop:bg-black/50"
			style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 320px"
			aria-labelledby="add-to-canvas-title"
		>
			<h2 id="add-to-canvas-title" class="text-lg font-bold">Add to Canvas?</h2>
			<p class="mt-2 text-sm" style="color: var(--color-muted)">
				{#if addToCanvasRelType === 'element'}
					Would you like to add the elements and relationship to the canvas?
				{:else}
					Would you like to add the target diagram as a reference on the canvas?
				{/if}
			</p>
			<div class="mt-4 flex justify-end gap-3">
				<button
					onclick={handleDismissAddToCanvas}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					No
				</button>
				<button
					onclick={handleAddToCanvas}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Yes
				</button>
			</div>
		</dialog>
	{/if}

{/if}
