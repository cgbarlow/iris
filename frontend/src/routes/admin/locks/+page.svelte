<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { EditLock } from '$lib/types/api';

	let locks = $state<EditLock[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		loadLocks();
	});

	async function loadLocks() {
		loading = true;
		error = null;
		try {
			const data = await apiFetch<{ items: EditLock[] }>('/api/locks');
			locks = data.items;
		} catch {
			error = 'Failed to load active locks';
		}
		loading = false;
	}

	async function forceRelease(lockId: string) {
		try {
			await apiFetch(`/api/admin/locks/${lockId}`, { method: 'DELETE' });
			locks = locks.filter((l) => l.id !== lockId);
		} catch {
			error = 'Failed to force-release lock';
		}
	}
</script>

<svelte:head>
	<title>Active Locks — Iris Admin</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Active Locks</h1>
<p class="mt-1" style="color: var(--color-muted)">Manage edit locks across the system.</p>

{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading locks...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else if locks.length === 0}
	<p class="mt-4" style="color: var(--color-muted)">No active locks.</p>
{:else}
	<div class="mt-4 overflow-x-auto">
		<table class="w-full text-sm" style="color: var(--color-fg); table-layout: fixed">
			<colgroup>
				<col style="width: 45%">
				<col style="width: 15%">
				<col style="width: 14%">
				<col style="width: 14%">
				<col style="width: 12%">
			</colgroup>
			<thead>
				<tr style="border-bottom: 2px solid var(--color-border)">
					<th class="px-3 py-2 text-left font-semibold">Target</th>
					<th class="px-3 py-2 text-left font-semibold">User</th>
					<th class="px-3 py-2 text-left font-semibold">Acquired</th>
					<th class="px-3 py-2 text-left font-semibold">Expires</th>
					<th class="px-3 py-2 text-left font-semibold">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each locks as lock}
					<tr style="border-bottom: 1px solid var(--color-border)">
						<td class="px-3 py-2" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
							<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{lock.target_type}</span>
							<span class="ml-1" title={lock.target_id}>{lock.target_name ?? lock.target_id}</span>
						</td>
						<td class="px-3 py-2">{lock.username}</td>
						<td class="px-3 py-2" style="white-space: nowrap">{new Date(lock.acquired_at).toLocaleString()}</td>
						<td class="px-3 py-2" style="white-space: nowrap">{new Date(lock.expires_at).toLocaleString()}</td>
						<td class="px-3 py-2">
							<button
								onclick={() => forceRelease(lock.id)}
								class="rounded px-3 py-1 text-xs text-white"
								style="background-color: var(--color-danger)"
							>
								Force Release
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
