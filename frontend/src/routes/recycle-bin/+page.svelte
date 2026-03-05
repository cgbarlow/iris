<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Pagination from '$lib/components/Pagination.svelte';

	interface DeletedItem {
		id: string;
		item_type: 'package' | 'diagram' | 'element';
		name: string;
		description: string | null;
		deleted_at: string;
		deleted_by_username: string | null;
		deleted_group_id: string | null;
		set_id: string | null;
		set_name: string | null;
		diagram_type: string | null;
		element_type: string | null;
	}

	interface DeletedItemList {
		items: DeletedItem[];
		total: number;
		page: number;
		page_size: number;
	}

	let items = $state<DeletedItem[]>([]);
	let total = $state(0);
	let page = $state(1);
	let pageSize = $state(50);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let actionLoading = $state<string | null>(null);

	let showHardDeleteDialog = $state(false);
	let itemToDelete = $state<DeletedItem | null>(null);
	let showEmptyDialog = $state(false);
	let emptyLoading = $state(false);

	$effect(() => {
		loadItems();
	});

	async function loadItems() {
		loading = true;
		error = null;
		try {
			const params = new URLSearchParams();
			params.set('page', String(page));
			params.set('page_size', String(pageSize));
			const data = await apiFetch<DeletedItemList>(`/api/recycle-bin?${params}`);
			items = data.items;
			total = data.total;
		} catch {
			error = 'Failed to load recycle bin';
		}
		loading = false;
	}

	function handlePageChange(newPage: number) {
		page = newPage;
		loadItems();
	}

	function handlePageSizeChange(newSize: number) {
		pageSize = newSize;
		page = 1;
		loadItems();
	}

	async function restoreItem(item: DeletedItem) {
		actionLoading = item.id;
		error = null;
		try {
			const typeMap = { package: 'packages', diagram: 'diagrams', element: 'elements' };
			await apiFetch(`/api/recycle-bin/${typeMap[item.item_type]}/${item.id}/restore`, {
				method: 'POST',
			});
			await loadItems();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to restore';
		}
		actionLoading = null;
	}

	async function restoreGroup(groupId: string) {
		actionLoading = groupId;
		error = null;
		try {
			await apiFetch(`/api/recycle-bin/groups/${groupId}/restore`, {
				method: 'POST',
			});
			await loadItems();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to restore group';
		}
		actionLoading = null;
	}

	function confirmHardDelete(item: DeletedItem) {
		itemToDelete = item;
		showHardDeleteDialog = true;
	}

	async function hardDelete() {
		if (!itemToDelete) return;
		const item = itemToDelete;
		showHardDeleteDialog = false;
		actionLoading = item.id;
		error = null;
		try {
			const typeMap = { package: 'packages', diagram: 'diagrams', element: 'elements' };
			await apiFetch(`/api/recycle-bin/${typeMap[item.item_type]}/${item.id}`, {
				method: 'DELETE',
			});
			await loadItems();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to permanently delete';
		}
		actionLoading = null;
		itemToDelete = null;
	}

	async function emptyRecycleBin() {
		showEmptyDialog = false;
		emptyLoading = true;
		error = null;
		try {
			await apiFetch('/api/recycle-bin', { method: 'DELETE' });
			await loadItems();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to empty recycle bin';
		}
		emptyLoading = false;
	}

	function typeBadgeColor(itemType: string): string {
		if (itemType === 'package') return 'var(--color-primary)';
		if (itemType === 'diagram') return 'var(--color-success, #16a34a)';
		return 'var(--color-muted)';
	}

	// Group items by deleted_group_id for "Restore All" buttons
	const groupCounts = $derived(
		items.reduce(
			(acc, item) => {
				if (item.deleted_group_id) {
					acc[item.deleted_group_id] = (acc[item.deleted_group_id] || 0) + 1;
				}
				return acc;
			},
			{} as Record<string, number>,
		),
	);

	function shouldShowGroupRestore(item: DeletedItem): boolean {
		if (!item.deleted_group_id) return false;
		if ((groupCounts[item.deleted_group_id] || 0) < 2) return false;
		const firstOfGroup = items.find((i) => i.deleted_group_id === item.deleted_group_id);
		return firstOfGroup?.id === item.id;
	}
</script>

<svelte:head>
	<title>Recycle Bin — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Recycle Bin</h1>
		<p class="mt-2" style="color: var(--color-muted)">
			Deleted items can be restored or permanently removed.
		</p>
	</div>
	{#if total > 0 && !loading}
		<button
			onclick={() => (showEmptyDialog = true)}
			disabled={emptyLoading}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-danger)"
		>
			{emptyLoading ? 'Emptying...' : 'Empty Recycle Bin'}
		</button>
	{/if}
</div>

<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if items.length === 0}
		<p style="color: var(--color-muted)">Recycle bin is empty.</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each items as item (item.id)}
				<li class="flex items-center gap-3 rounded border p-3" style="border-color: var(--color-border)">
					<span
						class="rounded px-2 py-0.5 text-xs font-medium"
						style="background: {typeBadgeColor(item.item_type)}20; color: {typeBadgeColor(item.item_type)}"
					>
						{item.item_type}
					</span>
					<div class="flex-1">
						<span class="font-medium" style="color: var(--color-fg)">{item.name}</span>
						{#if item.diagram_type}
							<span class="ml-1 text-xs" style="color: var(--color-muted)">{item.diagram_type}</span>
						{/if}
						{#if item.element_type}
							<span class="ml-1 text-xs" style="color: var(--color-muted)">{item.element_type}</span>
						{/if}
						{#if item.set_name}
							<span class="ml-2 text-xs" style="color: var(--color-muted)">{item.set_name}</span>
						{/if}
						{#if item.deleted_group_id}
							<span
								class="ml-2 rounded px-1.5 py-0.5 text-xs"
								style="background: var(--color-surface); color: var(--color-muted)"
								title="Cascade group: {item.deleted_group_id}"
							>
								group
							</span>
						{/if}
					</div>
					<span class="text-xs" style="color: var(--color-muted)">
						{new Date(item.deleted_at).toLocaleDateString()}
						{#if item.deleted_by_username}
							by {item.deleted_by_username}
						{/if}
					</span>
					<div class="flex gap-1">
						{#if shouldShowGroupRestore(item)}
							<button
								onclick={() => restoreGroup(item.deleted_group_id!)}
								disabled={actionLoading === item.deleted_group_id}
								class="rounded px-3 py-1 text-xs"
								style="border: 1px solid var(--color-primary); color: var(--color-primary)"
							>
								Restore All ({groupCounts[item.deleted_group_id!]})
							</button>
						{/if}
						<button
							onclick={() => restoreItem(item)}
							disabled={actionLoading === item.id}
							class="rounded px-3 py-1 text-xs"
							style="border: 1px solid var(--color-border); color: var(--color-success, #16a34a)"
						>
							Restore
						</button>
						<button
							onclick={() => confirmHardDelete(item)}
							disabled={actionLoading === item.id}
							class="rounded px-3 py-1 text-xs"
							style="border: 1px solid var(--color-border); color: var(--color-danger)"
						>
							Delete
						</button>
					</div>
				</li>
			{/each}
		</ul>

		<Pagination
			{page}
			{pageSize}
			{total}
			onpagechange={handlePageChange}
			onpagesizechange={handlePageSizeChange}
		/>
	{/if}
</div>

<ConfirmDialog
	open={showHardDeleteDialog}
	title="Permanently Delete"
	message="This item will be permanently removed and cannot be recovered. Are you sure?"
	confirmLabel="Delete Forever"
	onconfirm={hardDelete}
	oncancel={() => {
		showHardDeleteDialog = false;
		itemToDelete = null;
	}}
/>

<ConfirmDialog
	open={showEmptyDialog}
	title="Empty Recycle Bin"
	message="All {total} item{total === 1 ? '' : 's'} will be permanently deleted. This cannot be undone."
	confirmLabel="Empty All"
	onconfirm={emptyRecycleBin}
	oncancel={() => (showEmptyDialog = false)}
/>
