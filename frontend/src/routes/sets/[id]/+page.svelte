<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import { API_BASE_URL } from '$lib/config.js';
	import type {
		IrisSet,
		IrisCollection,
		Diagram,
		PaginatedResponse,
		HierarchySort,
		PackageTabDefault,
		ViewTabDefault,
		ElementTabDefault,
	} from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EntityImagesEditor from '$lib/components/EntityImagesEditor.svelte';
	import CollectionSelector from '$lib/components/CollectionSelector.svelte';
	import NamedPromptsSection from '$lib/components/NamedPromptsSection.svelte';
	import DOMPurify from 'dompurify';

	let set = $state<IrisSet | null>(null);
	let diagrams = $state<Diagram[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	let name = $state('');
	let description = $state('');
	let thumbnailSource = $state<'model' | 'diagram' | 'image' | null>(null);
	let thumbnailDiagramId = $state<string | null>(null);
	let thumbnailFile = $state<File | null>(null);
	let collectionId = $state<string | null>(null);
	let systemPrompt = $state('');
	let mcpSystemContext = $state('');
	// ADR-202 (v6.13.0): per-set hierarchy sort preference.
	let hierarchySort = $state<HierarchySort>('manual');
	// ADR-204 (v6.14.0): per-set tab defaults for Packages/Views screens.
	let packageTabDefault = $state<PackageTabDefault>('relationships');
	let viewTabDefault = $state<ViewTabDefault>('canvas');
	// ADR-208 (v6.16.0): per-set element tab default.
	let elementTabDefault = $state<ElementTabDefault>('relationships');

	let showDeleteDialog = $state(false);
	let deleting = $state(false);

	let setId = $derived(page.params.id);

	$effect(() => {
		loadSet();
	});

	async function loadSet() {
		loading = true;
		error = null;
		try {
			const [setData, diagramsData] = await Promise.all([
				apiFetch<IrisSet>(`/api/sets/${setId}`),
				apiFetch<PaginatedResponse<Diagram>>(`/api/diagrams?set_id=${setId}&page_size=100`),
			]);
			set = setData;
			diagrams = diagramsData.items;

			// Initialize form state
			name = setData.name;
			description = setData.description ?? '';
			thumbnailSource = setData.thumbnail_source;
			thumbnailDiagramId = setData.thumbnail_diagram_id;
			collectionId = setData.collection_id ?? null;
			systemPrompt = setData.system_prompt ?? '';
			mcpSystemContext = (setData as IrisSet & { mcp_system_context?: string | null }).mcp_system_context ?? '';
			hierarchySort = setData.hierarchy_sort ?? 'manual';
			packageTabDefault = setData.package_tab_default ?? 'relationships';
			viewTabDefault = setData.view_tab_default ?? 'canvas';
			elementTabDefault = (setData.element_tab_default as ElementTabDefault | undefined) ?? 'relationships';
		} catch {
			error = 'Failed to load set';
		}
		loading = false;
	}

	async function handleSave() {
		saving = true;
		error = null;
		successMsg = null;
		try {
			const sanitizedName = DOMPurify.sanitize(name.trim());
			const sanitizedDesc = description.trim()
				? DOMPurify.sanitize(description.trim())
				: null;
			const sanitizedPrompt = systemPrompt.trim()
				? DOMPurify.sanitize(systemPrompt.trim())
				: null;
			const sanitizedMcpSystemContext = mcpSystemContext.trim()
				? DOMPurify.sanitize(mcpSystemContext.trim())
				: null;

			await apiFetch<IrisSet>(`/api/sets/${setId}`, {
				method: 'PUT',
				body: JSON.stringify({
					name: sanitizedName,
					description: sanitizedDesc,
					thumbnail_source: thumbnailSource,
					thumbnail_diagram_id: thumbnailSource === 'model' ? thumbnailDiagramId : null,
					collection_id: collectionId,
					system_prompt: sanitizedPrompt,
					mcp_system_context: sanitizedMcpSystemContext,
					hierarchy_sort: hierarchySort,
					package_tab_default: packageTabDefault,
					view_tab_default: viewTabDefault,
					element_tab_default: elementTabDefault,
				}),
			});

			// Upload image if user selected one and source is 'image'
			if (thumbnailSource === 'image' && thumbnailFile) {
				const formData = new FormData();
				formData.append('file', thumbnailFile);

				const token = getAccessToken();
				const resp = await fetch(`${API_BASE_URL}/api/sets/${setId}/thumbnail`, {
					method: 'POST',
					headers: token ? { Authorization: `Bearer ${token}` } : {},
					body: formData,
				});
				if (!resp.ok) {
					const detail = await resp.json().catch(() => ({ detail: 'Upload failed' }));
					throw new Error(detail.detail || 'Upload failed');
				}
			}

			successMsg = 'Set saved successfully';
			await loadSet();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save set';
		}
		saving = false;
	}

	async function handleForceDelete() {
		deleting = true;
		error = null;
		try {
			await apiFetch<{ diagrams_deleted: number; elements_deleted: number }>(
				`/api/sets/${setId}?force=true`,
				{ method: 'DELETE' }
			);
			await goto('/sets');
		} catch {
			error = 'Failed to delete set';
		}
		deleting = false;
		showDeleteDialog = false;
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0] ?? null;
		if (file) {
			if (file.size > 2 * 1024 * 1024) {
				error = 'Image must be under 2 MB';
				return;
			}
			if (!['image/png', 'image/jpeg'].includes(file.type)) {
				error = 'Only PNG and JPEG images are accepted';
				return;
			}
			thumbnailFile = file;
			error = null;
		}
	}
</script>

<svelte:head>
	<title>{set?.name ?? 'Set'} — Iris</title>
</svelte:head>

{#if loading}
	<p style="color: var(--color-muted)">Loading set...</p>
{:else if error && !set}
	<div role="alert" style="color: var(--color-danger)">{error}</div>
{:else if set}
	<div class="flex items-center gap-3">
		<a href="/sets" class="text-sm" style="color: var(--color-primary)">Sets</a>
		<span style="color: var(--color-muted)">/</span>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{set.name}</h1>
	</div>

	{#if error}
		<div role="alert" class="mt-3" style="color: var(--color-danger)">{error}</div>
	{/if}
	{#if successMsg}
		<div class="mt-3" style="color: var(--color-primary)" role="status">{successMsg}</div>
	{/if}

	<form
		onsubmit={(e) => { e.preventDefault(); handleSave(); }}
		class="mt-6"
		style="max-width: 600px"
	>
		<!-- Name -->
		<div>
			<label for="set-edit-name" class="text-sm font-medium" style="color: var(--color-fg)">
				Name <span style="color: var(--color-danger)">*</span>
			</label>
			<input
				id="set-edit-name"
				bind:value={name}
				type="text"
				required
				maxlength="255"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<!-- Description -->
		<div class="mt-4">
			<label for="set-edit-description" class="text-sm font-medium" style="color: var(--color-fg)">
				Description
			</label>
			<textarea
				id="set-edit-description"
				bind:value={description}
				rows="3"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			></textarea>
		</div>

		<!-- Collection -->
		<div class="mt-4">
			<CollectionSelector
				value={collectionId || ''}
				onchange={(id) => { collectionId = id || null; }}
				showAll={true}
				label="Collection"
			/>
		</div>

		<!-- Hierarchy sort (ADR-202, v6.13.0) -->
		<div class="mt-4">
			<label for="set-edit-hierarchy-sort" class="text-sm font-medium" style="color: var(--color-fg)">
				Hierarchy sort
			</label>
			<select
				id="set-edit-hierarchy-sort"
				bind:value={hierarchySort}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<option value="manual">Manual (drag-and-drop)</option>
				<option value="alpha">Alphabetical (A → Z)</option>
				<option value="newest">Newest first</option>
				<option value="oldest">Oldest first</option>
			</select>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Controls how packages and diagrams are ordered in the dashboard tree, the packages-page sidebar, and the views-page tree for this set.
			</p>
		</div>

		<!-- Package tab default (ADR-204, v6.14.0) -->
		<div class="mt-4">
			<label for="set-edit-package-tab-default" class="text-sm font-medium" style="color: var(--color-fg)">
				Package tab default
			</label>
			<select
				id="set-edit-package-tab-default"
				bind:value={packageTabDefault}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<option value="relationships">Relationships</option>
				<option value="details">Details</option>
			</select>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Which tab opens by default when a user visits a package in this set.
			</p>
		</div>

		<!-- View tab default (ADR-204, v6.14.0) -->
		<div class="mt-4">
			<label for="set-edit-view-tab-default" class="text-sm font-medium" style="color: var(--color-fg)">
				View tab default
			</label>
			<select
				id="set-edit-view-tab-default"
				bind:value={viewTabDefault}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<option value="canvas">Canvas</option>
				<option value="relationships">Relationships</option>
				<option value="details">Details</option>
			</select>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Which tab opens by default when a user visits a view (diagram) in this set.
			</p>
		</div>

		<!-- Element tab default (ADR-208, v6.16.0) -->
		<div class="mt-4">
			<label for="set-edit-element-tab-default" class="text-sm font-medium" style="color: var(--color-fg)">
				Element tab default
			</label>
			<select
				id="set-edit-element-tab-default"
				bind:value={elementTabDefault}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<option value="relationships">Relationships</option>
				<option value="details">Details</option>
				<option value="versions">Version History</option>
			</select>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Which tab opens by default when a user visits an element in this set.
			</p>
		</div>

		<!-- System prompt (ADR-150) -->
		<div class="mt-4">
			<label for="set-edit-system-prompt" class="text-sm font-medium" style="color: var(--color-fg)">
				System prompt
			</label>
			<textarea
				id="set-edit-system-prompt"
				bind:value={systemPrompt}
				rows="6"
				maxlength="20000"
				placeholder="Optional. Prepended to every AI question about this Set."
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); font-family: var(--font-mono, monospace)"
			></textarea>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Applied in addition to the parent Collection's system prompt. Used by Iris's internal AI flows (discuss / creation). Not sent through MCP.
			</p>
		</div>

		<!-- MCP system context (ADR-156, v5.11.0): data passthrough on get_set -->
		<div class="mt-4">
			<label for="set-edit-mcp-system-context" class="text-sm font-medium" style="color: var(--color-fg)">
				MCP system context
			</label>
			<textarea
				id="set-edit-mcp-system-context"
				bind:value={mcpSystemContext}
				rows="6"
				maxlength="20000"
				placeholder="Optional. Passed through as data on MCP get_set responses, so it lands as initial context when an MCP client is browsing this Set. Not applied in Iris AI."
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); font-family: var(--font-mono, monospace)"
			></textarea>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Initial context for MCP clients (Claude Desktop / Claude Code) when retrieving this Set via the iris MCP server. Does NOT auto-apply in Iris AI and is NOT a slash-command prompt.
			</p>
		</div>

		<!-- Named prompts (ADR-154) -->
		{#if set}
			<NamedPromptsSection scope_type="set" scope_id={set.id} />
		{/if}

		<!-- Thumbnail -->
		<fieldset class="mt-6">
			<legend class="text-sm font-medium" style="color: var(--color-fg)">Thumbnail</legend>
			<div class="mt-2 flex flex-col gap-2">
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value=""
						checked={thumbnailSource === null}
						onchange={() => { thumbnailSource = null; }}
					/>
					No thumbnail
				</label>
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value="model"
						checked={thumbnailSource === 'model'}
						onchange={() => { thumbnailSource = 'model'; }}
					/>
					Use diagram thumbnail
				</label>
				{#if thumbnailSource === 'model'}
					<div class="ml-6">
						<select
							bind:value={thumbnailDiagramId}
							class="rounded border px-3 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						>
							<option value={null}>Select a diagram...</option>
							{#each diagrams as diagram}
								<option value={diagram.id}>{diagram.name}</option>
							{/each}
						</select>
					</div>
				{/if}
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value="image"
						checked={thumbnailSource === 'image'}
						onchange={() => { thumbnailSource = 'image'; }}
					/>
					Upload image
				</label>
				{#if thumbnailSource === 'image'}
					<div class="ml-6">
						<input
							type="file"
							accept="image/png,image/jpeg"
							onchange={handleFileInput}
							class="text-sm"
							style="color: var(--color-fg)"
						/>
						<p class="mt-1 text-xs" style="color: var(--color-muted)">PNG or JPEG, max 2 MB</p>
					</div>
				{/if}
			</div>
		</fieldset>

		<!-- Save button -->
		<div class="mt-6">
			<button
				type="submit"
				disabled={saving || !name.trim()}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				{saving ? 'Saving...' : 'Save Changes'}
			</button>
		</div>
	</form>

	<!-- ADR-209 (v6.17.0): attached images for this set. -->
	<div class="mt-4" style="max-width: 600px">
		<h2 class="text-sm font-bold" style="color: var(--color-fg)">Images</h2>
		<EntityImagesEditor
			entityType="set"
			entityId={set?.id ?? ''}
			editing={true}
			maxImages={1}
		/>
	</div>

	<!-- Info -->
	<div class="mt-6 text-sm" style="color: var(--color-muted); max-width: 600px">
		<p>{set.diagram_count} diagram{set.diagram_count !== 1 ? 's' : ''}, {set.element_count} element{set.element_count !== 1 ? 's' : ''} in this set</p>
	</div>

	<div class="mt-6">
		<a href="/ask" class="inline-flex items-center gap-2 rounded border px-4 py-2 text-sm"
			style="border-color: var(--color-border); color: var(--color-primary)">
			Iris AI — ask about this Set →
		</a>
	</div>

	<!-- Danger zone -->
	<div
		class="mt-8 rounded border p-4"
		style="border-color: var(--color-danger); max-width: 600px"
	>
		<h2 class="text-sm font-bold" style="color: var(--color-danger)">Danger Zone</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			This will permanently delete this set and all {set.diagram_count} diagram{set.diagram_count !== 1 ? 's' : ''} and {set.element_count} element{set.element_count !== 1 ? 's' : ''} within it.
		</p>
		<button
			onclick={() => (showDeleteDialog = true)}
			class="mt-3 rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-danger)"
		>
			Delete Set and All Contents
		</button>
	</div>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Set"
		message="Are you sure you want to delete &quot;{set.name}&quot; and all its contents? This will delete {set.diagram_count} diagram{set.diagram_count !== 1 ? 's' : ''} and {set.element_count} element{set.element_count !== 1 ? 's' : ''}. This action cannot be undone."
		confirmLabel={deleting ? 'Deleting...' : 'Delete Everything'}
		onconfirm={handleForceDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>
{/if}
