<script lang="ts">
	/**
	 * SmartMarkdownSlashPicker (ADR-205 + ADR-206, issue #185).
	 *
	 * Two-mode popover for the Smart Markdown `/`-trigger.
	 *
	 * Browse mode (default):
	 *   - Recent chips (derived from existing `{{...}}` tokens in
	 *     the diagram source — no new state).
	 *   - Breadcrumb (Root → Collection → Set → Bucket) with reset.
	 *   - List of items at the current hierarchy depth via
	 *     /api/picker/browse. Typing a query falls through to
	 *     /api/search/entities scoped to the current breadcrumb.
	 *
	 * Drill mode (after entity selected):
	 *   - IDE-style autocomplete `[entity-chip].<field>`.
	 *   - Arrow Up/Down to navigate the open field menu.
	 *   - `.` or Tab drills into a container (dict / list /
	 *     list_of_named) and opens the next menu.
	 *   - On a primitive, `.` or Tab or Enter inserts the assembled
	 *     `{{type:id:attr:path/segs/...}}` token and closes.
	 *   - Backspace at start of segment pops one path step.
	 *   - Substring filter on the current menu via letter input.
	 *   - Mouse click → equivalent to highlight + Tab.
	 */
	import { apiFetch } from '$lib/utils/api';
	import { onMount, tick } from 'svelte';

	type EntityType = 'element' | 'package' | 'diagram' | 'set' | 'collection';

	interface EntitySearchResult {
		id: string;
		entity_type: EntityType;
		name: string;
	}

	interface BreadcrumbStep {
		label: string;
		scope?: 'collection' | 'set' | 'set_bucket' | 'package';
		id?: string;
		entity_type?: 'element' | 'package' | 'diagram';
	}

	interface BrowseCounts { packages: number; diagrams: number; elements: number }
	interface BrowseResponse {
		breadcrumb: BreadcrumbStep[];
		items: EntitySearchResult[];
		counts?: BrowseCounts;
	}

	type TreeKind = 'dict' | 'list_of_named' | 'list' | 'primitive' | 'empty';
	interface TreeDescriptor {
		kind: TreeKind;
		keys?: string[];
		names?: string[];
		length?: number;
		value?: string;
	}

	interface RecentChip { type: EntityType; id: string; name: string }

	interface Props {
		oninsert: (token: string) => void;
		onclose: () => void;
		existingSource?: string;
		/** ADR-207 follow-up: the set the calling view belongs to. The
		 *  picker opens at the *collection* containing that set (or at
		 *  the set itself when the set has no parent collection), so the
		 *  user lands at their current scope instead of at the global
		 *  root. Search "at this level" then matches the most likely
		 *  intent (`/Pork` while editing a Groceries view shows Groceries
		 *  results first). */
		contextSetId?: string | null;
	}

	let { oninsert, onclose, existingSource = '', contextSetId = null }: Props = $props();

	// ── Browse mode state ────────────────────────────────────────
	type Mode = 'browse' | 'drill';
	let mode = $state<Mode>('browse');
	let breadcrumb = $state<BreadcrumbStep[]>([{ label: 'Root' }]);
	let items = $state<EntitySearchResult[]>([]);
	let counts = $state<BrowseCounts | null>(null);
	let query = $state('');
	let listIdx = $state(0);
	let recentChips = $state<RecentChip[]>([]);
	let searchDebounce: ReturnType<typeof setTimeout> | undefined;
	let browseSeq = 0;

	// ── Drill mode state ─────────────────────────────────────────
	let chosenEntity = $state<EntitySearchResult | null>(null);
	let drillPath = $state<string[]>([]);
	let drillNode = $state<TreeDescriptor | null>(null);
	let drillFilter = $state('');
	let drillIdx = $state(0);
	let drillSeq = 0;
	// ADR-207 v6.16.1: non-element entities are navigated via BROWSE
	// (root → collection → set → package or set_bucket), not drill.
	// Drill mode is reserved for element data-tree picking + the
	// name/description shortcut for any entity type.
	// containerChildren and drillParentStack are retained as no-op
	// fields for compatibility with the existing derived; they are
	// always empty.
	let containerChildren = $state<EntitySearchResult[]>([]);
	let drillParentStack = $state<EntitySearchResult[]>([]);
	const NON_ELEMENT_FIELDS = ['name', 'description'];

	// ADR-209 (v6.17.0): images attached to the drilled entity, surfaced
	// as picker items above name/description. Clicking an image opens
	// the sizing chooser.
	interface EntityImage {
		id: string;
		image_id: string;
		image_mime: string;
		image_size_bytes: number;
		display_order: number;
	}
	let attachedImages = $state<EntityImage[]>([]);
	type ImagePickerState = {
		chosen: EntityImage;
		axis: 'original' | 'width' | 'height';
		value: number;
		unit: '%' | 'px';
	} | null;
	let imageSizer = $state<ImagePickerState>(null);

	let rootEl = $state<HTMLDivElement | undefined>(undefined);
	let inputEl = $state<HTMLInputElement | undefined>(undefined);
	let drillInputEl = $state<HTMLInputElement | undefined>(undefined);

	const TOKEN_RE = /\{\{(element|package|diagram|set|collection):([^:}]+):[^}]+\}\}/g;

	// ADR-207: backend still uses 'diagram' internally; the picker displays
	// 'view' to match the user-facing term elsewhere in Iris.
	function displayType(t: EntityType): string {
		return t === 'diagram' ? 'view' : t;
	}

	// ADR-207: at non-root browse levels, expose a "Pick this {entity}"
	// shortcut so the breadcrumb-leaf collection/set is itself selectable
	// (otherwise the user has to navigate up a level to pick it).
	const browseLeafEntity = $derived.by((): EntitySearchResult | null => {
		const last = breadcrumb[breadcrumb.length - 1];
		if (!last.scope || !last.id) return null;
		if (last.scope === 'collection' || last.scope === 'set' || last.scope === 'package') {
			return {
				id: last.id,
				entity_type: last.scope,
				name: last.label,
			};
		}
		return null;
	});

	// ── Derived menu for drill mode ──────────────────────────────
	type DrillItem =
		| { kind: 'primitive'; label: string }
		| { kind: 'container'; label: string }
		| { kind: 'image'; label: string; image: EntityImage };
	const drillMenuItems = $derived.by((): DrillItem[] => {
		// ADR-209 (v6.17.0): images attached to the chosen entity are
		// surfaced as `image` items at the top of the menu. Clicking
		// them opens the sizing chooser.
		const imageItems: DrillItem[] = attachedImages.map((img, idx) => ({
			kind: 'image' as const,
			label: `Image ${idx + 1}`,
			image: img,
		}));
		// ADR-207 v6.16.1: non-element drill exposes name + description
		// only. Their children are reachable via browse mode at the
		// parent breadcrumb level (a package now appears as a browse
		// scope, not a drill).
		if (chosenEntity && chosenEntity.entity_type !== 'element') {
			const items: DrillItem[] = [
				...imageItems,
				{ kind: 'primitive' as const, label: 'name' },
				{ kind: 'primitive' as const, label: 'description' },
			];
			const filt = drillFilter.toLowerCase();
			if (!filt) return items;
			return items.filter((it) => it.label.toLowerCase().includes(filt));
		}
		if (!drillNode) return [];
		const raw: DrillItem[] = (() => {
			if (drillNode.kind === 'dict') {
				return (drillNode.keys ?? []).map((k) => ({
					label: k, kind: 'container' as const,
				}));
			}
			if (drillNode.kind === 'list_of_named') {
				return (drillNode.names ?? []).map((n) => ({
					label: n, kind: 'container' as const,
				}));
			}
			if (drillNode.kind === 'list') {
				return Array.from({ length: drillNode.length ?? 0 }, (_, i) => ({
					label: String(i), kind: 'container' as const,
				}));
			}
			if (drillNode.kind === 'primitive') {
				return [{ label: `= ${drillNode.value}`, kind: 'primitive' as const }];
			}
			return [];
		})();
		// At the root of an element drill, also expose name + description
		// as "shortcut" primitives so the user can pick them without
		// drilling. Images (ADR-209) sit above them. For non-elements
		// only the shortcuts apply (handled above).
		const withTopShortcuts: DrillItem[] = (drillPath.length === 0)
			? [
				...imageItems,
				...NON_ELEMENT_FIELDS.map((f) => ({
					label: f, kind: 'primitive' as const,
				})),
				...raw,
			]
			: raw;
		const filt = drillFilter.toLowerCase();
		if (!filt) return withTopShortcuts;
		return withTopShortcuts.filter((it) => it.label.toLowerCase().includes(filt));
	});

	// ── Lifecycle ────────────────────────────────────────────────
	onMount(async () => {
		recentChips = await deriveRecent(existingSource);
		await seedBreadcrumbFromContext();
		await loadBrowse();
		inputEl?.focus();
	});

	async function seedBreadcrumbFromContext() {
		// ADR-207 follow-up: open the picker at the calling view's parent
		// collection (or at the set when the set has no collection). The
		// initial breadcrumb is set BEFORE loadBrowse() so the first fetch
		// uses the right scope.
		if (!contextSetId) return;
		try {
			const setData = await apiFetch<{
				id: string;
				name: string;
				collection_id?: string | null;
				collection_name?: string | null;
			}>(`/api/sets/${encodeURIComponent(contextSetId)}`);
			if (setData.collection_id && setData.collection_name) {
				breadcrumb = [
					{ label: 'Root' },
					{
						label: setData.collection_name,
						scope: 'collection',
						id: setData.collection_id,
					},
				];
				return;
			}
			breadcrumb = [
				{ label: 'Root' },
				{ label: setData.name || 'Set', scope: 'set', id: setData.id },
			];
		} catch {
			// On error, fall back to the root view. Best effort.
		}
	}

	async function deriveRecent(source: string): Promise<RecentChip[]> {
		const seen = new Set<string>();
		const refs: { type: EntityType; id: string }[] = [];
		for (const m of source.matchAll(TOKEN_RE)) {
			const key = `${m[1]}:${m[2]}`;
			if (!seen.has(key)) {
				seen.add(key);
				refs.push({ type: m[1] as EntityType, id: m[2] });
			}
		}
		// Cap at 10 to keep the chip bar small.
		const capped = refs.slice(0, 10);
		const results = await Promise.all(capped.map(async (r) => {
			const name = await resolveName(r.type, r.id);
			return name ? { type: r.type, id: r.id, name } : null;
		}));
		return results.filter((x): x is RecentChip => x !== null);
	}

	async function resolveName(type: EntityType, id: string): Promise<string | null> {
		try {
			if (type === 'element') {
				const r = await apiFetch<{ name?: string }>(`/api/elements/${encodeURIComponent(id)}`);
				return r.name ?? null;
			}
			if (type === 'package') {
				const r = await apiFetch<{ name?: string }>(`/api/packages/${encodeURIComponent(id)}`);
				return r.name ?? null;
			}
			if (type === 'diagram') {
				const r = await apiFetch<{ name?: string }>(`/api/diagrams/${encodeURIComponent(id)}`);
				return r.name ?? null;
			}
			if (type === 'set') {
				const r = await apiFetch<{ name?: string }>(`/api/sets/${encodeURIComponent(id)}`);
				return r.name ?? null;
			}
			// collection
			const r = await apiFetch<{ name?: string }>(`/api/collections/${encodeURIComponent(id)}`);
			return r.name ?? null;
		} catch {
			return null;
		}
	}

	// ── Browse mode behaviour ────────────────────────────────────
	function currentScopeQuery(): string {
		const last = breadcrumb[breadcrumb.length - 1];
		if (!last.scope) return 'scope=root';
		if (last.scope === 'collection') return `scope=collection&collection_id=${encodeURIComponent(last.id ?? '')}`;
		if (last.scope === 'set') return `scope=set&set_id=${encodeURIComponent(last.id ?? '')}`;
		if (last.scope === 'package') return `scope=package&package_id=${encodeURIComponent(last.id ?? '')}`;
		// set_bucket
		return `scope=set_bucket&set_id=${encodeURIComponent(last.id ?? '')}&entity_type=${last.entity_type}`;
	}

	async function loadBrowse() {
		const mySeq = ++browseSeq;
		try {
			const r = await apiFetch<BrowseResponse>(`/api/picker/browse?${currentScopeQuery()}`);
			if (mySeq !== browseSeq) return;
			items = r.items ?? [];
			counts = r.counts ?? null;
			listIdx = 0;
		} catch {
			if (mySeq !== browseSeq) return;
			items = [];
			counts = null;
		}
	}

	function scopeParamsForSearch(): string {
		// Find the deepest collection/set in the breadcrumb to scope search.
		let setId: string | undefined;
		let collectionId: string | undefined;
		for (const step of breadcrumb) {
			if (step.scope === 'collection' && step.id) collectionId = step.id;
			if (step.scope === 'set' && step.id) setId = step.id;
		}
		const parts: string[] = [];
		if (setId) parts.push(`set_id=${encodeURIComponent(setId)}`);
		else if (collectionId) parts.push(`collection_id=${encodeURIComponent(collectionId)}`);
		return parts.join('&');
	}

	async function runSearch() {
		const q = query.trim();
		if (!q) { await loadBrowse(); return; }
		const mySeq = ++browseSeq;
		const params = scopeParamsForSearch();
		const url = `/api/search/entities?q=${encodeURIComponent(q)}&limit=50${params ? '&' + params : ''}`;
		try {
			const rows = await apiFetch<EntitySearchResult[]>(url);
			if (mySeq !== browseSeq) return;
			items = rows;
			counts = null;
			listIdx = 0;
		} catch {
			if (mySeq !== browseSeq) return;
			items = [];
		}
	}

	function scheduleSearch() {
		clearTimeout(searchDebounce);
		searchDebounce = setTimeout(runSearch, 150);
	}

	async function clickBucket(entity_type: 'element' | 'package' | 'diagram') {
		const setStep = [...breadcrumb].reverse().find((s) => s.scope === 'set');
		if (!setStep || !setStep.id) return;
		const labels = { element: 'Elements', package: 'Packages', diagram: 'Views' };
		breadcrumb = [
			...breadcrumb,
			{ label: labels[entity_type], scope: 'set_bucket', id: setStep.id, entity_type },
		];
		query = '';
		await loadBrowse();
	}

	async function clickItem(item: EntitySearchResult) {
		// ADR-207 follow-up: containers (collection, set, package) navigate
		// browse one level deeper so the breadcrumb-leaf entity is reachable
		// via "Pick this {entity}" and its children render with the same
		// browse-mode look at every level. Drill mode is reserved for
		// elements (data-tree picking) and "Pick this" shortcuts.
		if (item.entity_type === 'collection') {
			breadcrumb = [
				...breadcrumb,
				{ label: item.name, scope: 'collection', id: item.id },
			];
			query = '';
			await loadBrowse();
			return;
		}
		if (item.entity_type === 'set') {
			breadcrumb = [...breadcrumb, { label: item.name, scope: 'set', id: item.id }];
			query = '';
			await loadBrowse();
			return;
		}
		if (item.entity_type === 'package') {
			breadcrumb = [...breadcrumb, { label: item.name, scope: 'package', id: item.id }];
			query = '';
			await loadBrowse();
			return;
		}
		// element / diagram (view) → drill (data-tree picking for elements;
		// name/description for views which have no data tree).
		await enterDrill(item);
	}

	async function clickChip(chip: RecentChip) {
		await enterDrill({ id: chip.id, entity_type: chip.type, name: chip.name });
	}

	async function clickReset() {
		breadcrumb = [{ label: 'Root' }];
		query = '';
		await loadBrowse();
	}

	async function clickBreadcrumbStep(idx: number) {
		breadcrumb = breadcrumb.slice(0, idx + 1);
		query = '';
		await loadBrowse();
	}

	// ── Drill mode behaviour ─────────────────────────────────────
	// ADR-207 follow-up (v6.16.1): drill mode is for ELEMENT field
	// picking only (data-tree + name/description). Non-elements are
	// navigated via browse mode (root → collection → set → package or
	// set_bucket); their own name/description is picked via the
	// "Pick this {entity}" shortcut, which lands here in drill mode
	// with no children to show.
	// ADR-209 (v6.17.0): also fetch attached images so they appear as
	// pick-this-image items at the top of the menu.
	async function enterDrill(entity: EntitySearchResult, opts: { resetStack?: boolean } = {}) {
		const { resetStack = true } = opts;
		if (resetStack) drillParentStack = [];
		chosenEntity = entity;
		drillPath = [];
		drillFilter = '';
		drillIdx = 0;
		mode = 'drill';
		drillNode = null;
		containerChildren = [];
		imageSizer = null;
		// Fetch attached images for the entity (parallel with drill node fetch).
		attachedImages = [];
		void fetchAttachedImages(entity);
		if (entity.entity_type === 'element') {
			await fetchDrillNode();
		} else {
			// Non-elements expose name + description only; their
			// children are reachable via browse mode at the parent
			// level (no drill children, no clutter).
			drillNode = { kind: 'empty' };
		}
		await tick();
		drillInputEl?.focus();
	}

	async function fetchAttachedImages(entity: EntitySearchResult) {
		try {
			const rows = await apiFetch<EntityImage[]>(
				`/api/${entity.entity_type}/${encodeURIComponent(entity.id)}/images`,
			);
			// Only apply if still drilling into the same entity.
			if (chosenEntity?.id === entity.id) {
				attachedImages = rows ?? [];
			}
		} catch {
			if (chosenEntity?.id === entity.id) attachedImages = [];
		}
	}

	function openImageSizer(image: EntityImage) {
		imageSizer = {
			chosen: image,
			axis: 'original',
			value: 100,
			unit: '%',
		};
	}

	function confirmImageSizing() {
		if (!imageSizer) return;
		const { chosen, axis, value, unit } = imageSizer;
		let token: string;
		if (axis === 'original') {
			token = `{{image:${chosen.image_id}}}`;
		} else {
			token = `{{image:${chosen.image_id}:${axis}:${value}${unit}}}`;
		}
		imageSizer = null;
		oninsert(token);
	}

	async function fetchDrillNode() {
		if (!chosenEntity) return;
		const mySeq = ++drillSeq;
		const pathParam = drillPath.length
			? `?path=${encodeURIComponent(drillPath.join('/'))}`
			: '';
		try {
			const node = await apiFetch<TreeDescriptor>(
				`/api/elements/${encodeURIComponent(chosenEntity.id)}/data-tree${pathParam}`,
			);
			if (mySeq !== drillSeq) return;
			drillNode = node;
			drillIdx = 0;
		} catch {
			if (mySeq !== drillSeq) return;
			drillNode = { kind: 'empty' };
		}
	}

	function emitToken(terminalSeg?: string) {
		if (!chosenEntity) return;
		// terminalSeg = the literal `name`/`description` shortcut or
		// an explicit primitive picked at the current path level.
		if (terminalSeg === 'name' || terminalSeg === 'description') {
			oninsert(`{{${chosenEntity.entity_type}:${chosenEntity.id}:${terminalSeg}}}`);
			return;
		}
		if (chosenEntity.entity_type !== 'element' && terminalSeg) {
			oninsert(`{{${chosenEntity.entity_type}:${chosenEntity.id}:${terminalSeg}}}`);
			return;
		}
		// Element path:
		const path = [...drillPath, ...(terminalSeg ? [terminalSeg] : [])];
		if (path.length === 0) return;
		oninsert(`{{element:${chosenEntity.id}:attr:${path.join('/')}}}`);
	}

	async function chooseDrillItem(item: DrillItem) {
		// ADR-209: image item → open sizing chooser (does not emit yet).
		if (item.kind === 'image') {
			openImageSizer(item.image);
			return;
		}
		if (item.kind === 'primitive') {
			// Top-level name/description shortcuts
			if (drillPath.length === 0 && NON_ELEMENT_FIELDS.includes(item.label)) {
				emitToken(item.label);
				return;
			}
			// Terminal primitive at this path level (current path resolved
			// to a primitive value).
			emitToken();
			return;
		}
		// Element data drill: container item → push the segment.
		drillPath = [...drillPath, item.label];
		drillFilter = '';
		await fetchDrillNode();
		await tick();
		drillInputEl?.focus();
	}

	async function drillBackspace() {
		if (drillFilter.length > 0) {
			drillFilter = drillFilter.slice(0, -1);
			return;
		}
		if (drillPath.length === 0) {
			// ADR-207: if we drilled into a child entity, pop back to the
			// parent entity's drill instead of going all the way back to
			// browse mode.
			if (drillParentStack.length > 0) {
				const parent = drillParentStack[drillParentStack.length - 1];
				drillParentStack = drillParentStack.slice(0, -1);
				await enterDrill(parent, { resetStack: false });
				return;
			}
			// Pop entity selection — back to browse.
			mode = 'browse';
			chosenEntity = null;
			drillNode = null;
			containerChildren = [];
			await tick();
			inputEl?.focus();
			return;
		}
		drillPath = drillPath.slice(0, -1);
		await fetchDrillNode();
	}

	// ── Keyboard handling ────────────────────────────────────────
	function handleBrowseKey(e: KeyboardEvent) {
		if (e.key === 'Escape') { e.preventDefault(); onclose(); return; }
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (items.length > 0) listIdx = (listIdx + 1) % items.length;
			return;
		}
		if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (items.length > 0) listIdx = (listIdx - 1 + items.length) % items.length;
			return;
		}
		// ADR-207 v6.16.1: IDE-style — Tab and `.` commit the highlighted
		// item and navigate/drill, same as Enter or mouse-click. Tab
		// always preventDefault so focus stays in the picker.
		if (e.key === 'Tab' || e.key === '.') {
			e.preventDefault();
			if (items.length > 0) {
				clickItem(items[listIdx]);
			}
			return;
		}
		if (e.key === 'Enter' && items.length > 0) {
			e.preventDefault();
			clickItem(items[listIdx]);
		}
	}

	function handleDrillKey(e: KeyboardEvent) {
		if (e.key === 'Escape') { e.preventDefault(); onclose(); return; }
		const menu = drillMenuItems;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (menu.length > 0) drillIdx = (drillIdx + 1) % menu.length;
			return;
		}
		if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (menu.length > 0) drillIdx = (drillIdx - 1 + menu.length) % menu.length;
			return;
		}
		if (e.key === 'Backspace' && drillFilter.length === 0) {
			e.preventDefault();
			drillBackspace();
			return;
		}
		// ADR-207 fix: Tab and `.` must ALWAYS preventDefault. Tab without
		// preventDefault tabs focus out of the picker entirely; `.` without
		// preventDefault gets inserted as a literal character into the filter.
		// Enter keeps the menu-non-empty gate so a stray Enter on an empty
		// menu doesn't no-op an Esc-like dismissal pattern.
		if (e.key === '.' || e.key === 'Tab') {
			e.preventDefault();
			if (menu.length > 0) {
				chooseDrillItem(menu[Math.min(drillIdx, menu.length - 1)]);
			}
			return;
		}
		if (e.key === 'Enter') {
			if (menu.length > 0) {
				e.preventDefault();
				chooseDrillItem(menu[Math.min(drillIdx, menu.length - 1)]);
			}
			return;
		}
		// Letter/digit input narrows the menu via bind:value={drillFilter}.
	}

	// ADR-207 fix: the v6.15.0 $effect tracked `mode` but not `query`, so
	// typing in the input never re-fired the search. The browse input now
	// uses an explicit `oninput={scheduleSearch}` handler instead — see
	// the input element below.

	$effect(() => {
		// When the menu shrinks, clamp the highlight index.
		const len = drillMenuItems.length;
		if (drillIdx >= len) drillIdx = Math.max(0, len - 1);
	});
</script>

<div
	bind:this={rootEl}
	class="slash-picker"
	role="dialog"
	aria-label="Insert reference"
	tabindex="-1"
>
	{#if mode === 'browse'}
		<div class="slash-picker__header">
			Insert reference
			<button class="slash-picker__back" onclick={onclose} aria-label="Close">✕</button>
		</div>

		{#if recentChips.length > 0}
			<div class="slash-picker__chips" aria-label="Recently referenced">
				<span class="slash-picker__chips-label">Recent:</span>
				{#each recentChips as chip (chip.type + chip.id)}
					<button
						class="slash-picker__chip slash-picker__badge--{chip.type}"
						onclick={() => clickChip(chip)}
						title="{displayType(chip.type)} · {chip.name}"
					>{chip.name}</button>
				{/each}
			</div>
		{/if}

		<div class="slash-picker__breadcrumb" aria-label="Breadcrumb">
			{#each breadcrumb as step, i (i + (step.id ?? step.label))}
				{#if i > 0}<span class="slash-picker__crumb-sep">›</span>{/if}
				<button
					class="slash-picker__crumb"
					class:active={i === breadcrumb.length - 1}
					onclick={() => clickBreadcrumbStep(i)}
					disabled={i === breadcrumb.length - 1}
				>{step.label}</button>
			{/each}
			{#if breadcrumb.length > 1}
				<button
					class="slash-picker__reset"
					onclick={clickReset}
					aria-label="Reset to root"
				>Reset</button>
			{/if}
		</div>

		<input
			bind:this={inputEl}
			type="text"
			class="slash-picker__input"
			placeholder="Search at this level…"
			bind:value={query}
			oninput={scheduleSearch}
			onkeydown={handleBrowseKey}
		/>

		{#if browseLeafEntity && !query.trim()}
			<!-- ADR-207: 'Pick this {entity}' shortcut at non-root browse levels. -->
			<button
				class="slash-picker__item slash-picker__pick-this"
				type="button"
				onclick={() => clickItem(browseLeafEntity!)}
				title="Open drill for this {displayType(browseLeafEntity.entity_type)}"
			>
				<span class="slash-picker__badge slash-picker__badge--{browseLeafEntity.entity_type}">{displayType(browseLeafEntity.entity_type)}</span>
				<span class="slash-picker__name">Pick this {displayType(browseLeafEntity.entity_type)}: <strong>{browseLeafEntity.name}</strong></span>
			</button>
		{/if}

		{#if counts}
			<!-- ADR-207 v6.16.1: bucket order Packages → Views → Elements
				 per user direction. -->
			<ul class="slash-picker__list" role="listbox" aria-label="Buckets">
				{#if counts.packages > 0}
					<li
						role="option"
						aria-selected="false"
						class="slash-picker__item"
						onclick={() => clickBucket('package')}
						onkeydown={(e) => { if (e.key === 'Enter') clickBucket('package'); }}
						tabindex="-1"
					>
						<span class="slash-picker__badge slash-picker__badge--package">packages</span>
						<span class="slash-picker__name">Packages ({counts.packages})</span>
					</li>
				{/if}
				{#if counts.diagrams > 0}
					<li
						role="option"
						aria-selected="false"
						class="slash-picker__item"
						onclick={() => clickBucket('diagram')}
						onkeydown={(e) => { if (e.key === 'Enter') clickBucket('diagram'); }}
						tabindex="-1"
					>
						<span class="slash-picker__badge slash-picker__badge--diagram">views</span>
						<span class="slash-picker__name">Views ({counts.diagrams})</span>
					</li>
				{/if}
				{#if counts.elements > 0}
					<li
						role="option"
						aria-selected="false"
						class="slash-picker__item"
						onclick={() => clickBucket('element')}
						onkeydown={(e) => { if (e.key === 'Enter') clickBucket('element'); }}
						tabindex="-1"
					>
						<span class="slash-picker__badge slash-picker__badge--element">elements</span>
						<span class="slash-picker__name">Elements ({counts.elements})</span>
					</li>
				{/if}
				{#if counts.elements === 0 && counts.packages === 0 && counts.diagrams === 0}
					<li class="slash-picker__empty">Nothing in this set yet.</li>
				{/if}
			</ul>
		{:else}
			<ul class="slash-picker__list" role="listbox" aria-label="Items">
				{#each items as item, i (item.entity_type + item.id)}
					<li
						role="option"
						aria-selected={i === listIdx}
						class="slash-picker__item"
						class:active={i === listIdx}
						onclick={() => clickItem(item)}
						onkeydown={(e) => { if (e.key === 'Enter') clickItem(item); }}
						tabindex="-1"
					>
						<span class="slash-picker__badge slash-picker__badge--{item.entity_type}">{displayType(item.entity_type)}</span>
						<span class="slash-picker__name">{item.name}</span>
					</li>
				{/each}
				{#if items.length === 0}
					<li class="slash-picker__empty">
						{query.trim() ? 'No matches.' : 'No items here.'}
					</li>
				{/if}
			</ul>
		{/if}
	{:else}
		<!-- drill mode -->
		<div class="slash-picker__header">
			<button class="slash-picker__back" onclick={drillBackspace} aria-label="Back">‹</button>
			<span
				class="slash-picker__badge slash-picker__badge--{chosenEntity?.entity_type}"
			>{chosenEntity ? displayType(chosenEntity.entity_type) : ''}</span>
			<strong class="slash-picker__name">{chosenEntity?.name}</strong>
			{#if drillPath.length > 0}
				<span class="slash-picker__drill-path">.{drillPath.join('.')}</span>
			{/if}
			<button class="slash-picker__back" onclick={onclose} aria-label="Close">✕</button>
		</div>

		{#if imageSizer}
			<!-- ADR-209 (v6.17.0): image sizing chooser. -->
			<div class="slash-picker__sizer">
				<div class="slash-picker__sizer-preview">
					<img
						src="/api/images/{imageSizer.chosen.image_id}"
						alt=""
						style="max-width: 100%; max-height: 120px; object-fit: contain;"
					/>
				</div>
				<fieldset class="slash-picker__sizer-axis">
					<label>
						<input type="radio" bind:group={imageSizer.axis} value="original" />
						Original size
					</label>
					<label>
						<input type="radio" bind:group={imageSizer.axis} value="width" />
						Width
					</label>
					<label>
						<input type="radio" bind:group={imageSizer.axis} value="height" />
						Height
					</label>
				</fieldset>
				{#if imageSizer.axis !== 'original'}
					<div class="slash-picker__sizer-value">
						<input
							type="number"
							min="1"
							max="9999"
							bind:value={imageSizer.value}
							aria-label="Sizing value"
						/>
						<select bind:value={imageSizer.unit} aria-label="Sizing unit">
							<option value="%">%</option>
							<option value="px">px</option>
						</select>
					</div>
				{/if}
				<div class="slash-picker__sizer-actions">
					<button type="button" onclick={() => (imageSizer = null)}>Cancel</button>
					<button
						type="button"
						class="slash-picker__sizer-confirm"
						onclick={confirmImageSizing}
					>Insert image</button>
				</div>
			</div>
		{:else}
			<input
				bind:this={drillInputEl}
				type="text"
				class="slash-picker__input slash-picker__input--drill"
				placeholder="Type . or Tab to drill, Enter to insert"
				bind:value={drillFilter}
				onkeydown={handleDrillKey}
			/>
			<ul class="slash-picker__list" role="listbox" aria-label="Fields">
				{#each drillMenuItems as menuItem, i (i + menuItem.label)}
					<li
						role="option"
						aria-selected={i === drillIdx}
						class="slash-picker__item"
						class:active={i === drillIdx}
						onclick={() => chooseDrillItem(menuItem)}
						onkeydown={(e) => { if (e.key === 'Enter') chooseDrillItem(menuItem); }}
						tabindex="-1"
					>
						{#if menuItem.kind === 'image'}
							<img
								src="/api/images/{menuItem.image.image_id}"
								alt=""
								class="slash-picker__image-thumb"
							/>
						{/if}
						<span class="slash-picker__field">{menuItem.label}</span>
						{#if menuItem.kind === 'container'}
							<span class="slash-picker__chevron" aria-hidden="true">›</span>
						{/if}
					</li>
				{/each}
				{#if drillMenuItems.length === 0}
					<li class="slash-picker__empty">No fields.</li>
				{/if}
			</ul>
		{/if}
	{/if}
</div>

<style>
	.slash-picker {
		position: absolute;
		top: 56px; left: 16px;
		width: 360px;
		max-height: 440px;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 6px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
		display: flex; flex-direction: column;
		z-index: 50;
		outline: none;
	}
	.slash-picker__header {
		display: flex; justify-content: space-between; align-items: center;
		gap: 6px;
		padding: 8px 12px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
		color: var(--color-muted, #6b7280);
	}
	.slash-picker__back {
		background: transparent;
		border: 0;
		color: var(--color-primary, #2563eb);
		font-size: 14px;
		cursor: pointer;
		padding: 2px 6px;
	}
	.slash-picker__chips {
		display: flex; flex-wrap: wrap; gap: 4px;
		padding: 6px 12px;
		border-bottom: 1px solid var(--color-border, #f0f0f0);
		font-size: 11px;
	}
	.slash-picker__chips-label {
		color: var(--color-muted, #6b7280);
		font-size: 11px;
		margin-right: 4px;
		align-self: center;
	}
	.slash-picker__chip {
		border: 0;
		padding: 2px 8px;
		border-radius: 10px;
		font-size: 11px;
		cursor: pointer;
	}
	.slash-picker__breadcrumb {
		display: flex; flex-wrap: wrap; align-items: center; gap: 4px;
		padding: 6px 12px;
		font-size: 12px;
		color: var(--color-muted, #6b7280);
		border-bottom: 1px solid var(--color-border, #f0f0f0);
	}
	.slash-picker__crumb {
		background: transparent; border: 0; padding: 2px 4px;
		font-size: 12px;
		cursor: pointer;
		color: var(--color-primary, #2563eb);
	}
	.slash-picker__crumb.active {
		color: var(--color-fg, #111827);
		cursor: default;
		font-weight: 600;
	}
	.slash-picker__crumb-sep {
		color: var(--color-muted, #9ca3af);
	}
	.slash-picker__reset {
		margin-left: auto;
		background: transparent; border: 0;
		font-size: 11px;
		color: var(--color-muted, #6b7280);
		cursor: pointer;
		text-decoration: underline;
	}
	.slash-picker__input {
		margin: 8px 12px;
		padding: 6px 8px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 13px;
		outline: none;
		background: var(--color-bg, #ffffff);
		color: var(--color-fg, #111827);
	}
	.slash-picker__input--drill {
		font-family: ui-monospace, monospace;
	}
	.slash-picker__list {
		list-style: none;
		margin: 0; padding: 4px 0;
		overflow-y: auto;
		flex: 1;
	}
	.slash-picker__item {
		display: flex; align-items: center; gap: 8px;
		padding: 6px 12px;
		cursor: pointer;
		font-size: 13px;
		color: var(--color-fg, #111827);
	}
	.slash-picker__item.active,
	.slash-picker__item:hover {
		background: var(--color-hover, #f3f4f6);
	}
	.slash-picker__empty {
		padding: 8px 12px;
		color: var(--color-muted, #9ca3af);
		font-size: 12px;
		font-style: italic;
	}
	.slash-picker__badge {
		display: inline-block;
		padding: 1px 6px;
		border-radius: 10px;
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		background: var(--color-muted-bg, #e5e7eb);
		color: var(--color-muted, #4b5563);
	}
	/* ADR-207: badge palette rotated so each type matches its KG
	   colour key (frontend/src/lib/utils/graphColors.ts): collection=red,
	   set=violet, package=amber, diagram=green, element=blue. */
	.slash-picker__badge--element { background: #dbeafe; color: #1e3a8a; }
	.slash-picker__badge--package { background: #fef3c7; color: #92400e; }
	.slash-picker__badge--diagram { background: #dcfce7; color: #14532d; }
	.slash-picker__badge--set { background: #f3e8ff; color: #581c87; }
	.slash-picker__badge--collection { background: #fce7f3; color: #831843; }
	.slash-picker__name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.slash-picker__field {
		font-family: ui-monospace, monospace;
		font-size: 12px;
		flex: 1;
	}
	.slash-picker__chevron {
		color: var(--color-muted, #9ca3af);
		font-size: 13px;
	}
	.slash-picker__pick-this {
		display: flex; align-items: center; gap: 8px;
		width: calc(100% - 24px);
		margin: 0 12px 4px 12px;
		padding: 6px 12px;
		background: var(--color-hover, #f3f4f6);
		border: 1px dashed var(--color-border, #d1d5db);
		border-radius: 4px;
		cursor: pointer;
		font-size: 13px;
		color: var(--color-fg, #111827);
		text-align: left;
	}
	.slash-picker__pick-this:hover {
		background: var(--color-surface, #ffffff);
		border-style: solid;
	}
	.slash-picker__drill-path {
		font-family: ui-monospace, monospace;
		font-size: 11px;
		color: var(--color-muted, #6b7280);
	}
	/* ADR-209: image thumb in drill menu + sizing chooser. */
	.slash-picker__image-thumb {
		width: 22px; height: 22px;
		border-radius: 3px;
		object-fit: cover;
		border: 1px solid var(--color-border, #d1d5db);
		margin-right: 4px;
	}
	.slash-picker__sizer {
		padding: 8px 12px;
		display: flex; flex-direction: column; gap: 8px;
	}
	.slash-picker__sizer-preview {
		display: flex; justify-content: center;
		padding: 6px;
		background: var(--color-surface, #f3f4f6);
		border-radius: 4px;
	}
	.slash-picker__sizer-axis {
		border: 0; padding: 0; margin: 0;
		display: flex; flex-direction: column; gap: 4px;
		font-size: 12px;
	}
	.slash-picker__sizer-value {
		display: flex; gap: 4px;
	}
	.slash-picker__sizer-value input,
	.slash-picker__sizer-value select {
		padding: 4px 6px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 3px;
		font-size: 12px;
	}
	.slash-picker__sizer-value input { flex: 1; }
	.slash-picker__sizer-actions {
		display: flex; justify-content: flex-end; gap: 6px;
	}
	.slash-picker__sizer-actions button {
		padding: 4px 10px;
		font-size: 12px;
		border: 1px solid var(--color-border, #d1d5db);
		background: var(--color-bg, #ffffff);
		border-radius: 3px;
		cursor: pointer;
	}
	.slash-picker__sizer-confirm {
		background: var(--color-primary, #2563eb) !important;
		color: white !important;
		border-color: var(--color-primary, #2563eb) !important;
	}
</style>
