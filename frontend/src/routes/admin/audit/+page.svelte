<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { AuditEntry, AuditVerifyResult, PaginatedResponse } from '$lib/types/api';

	let entries = $state<AuditEntry[]>([]);
	let total = $state(0);
	let currentPage = $state(1);
	let pageSize = $state(25);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Filters
	let actionFilter = $state('');
	let usernameFilter = $state('');
	let targetTypeFilter = $state('');
	let fromDate = $state('');
	let toDate = $state('');

	// Chain verification
	let verifyResult = $state<AuditVerifyResult | null>(null);
	let verifying = $state(false);

	// Expandable rows
	let expandedIds = $state<Set<number>>(new Set());

	$effect(() => {
		loadEntries();
		verifyChain();
	});

	async function loadEntries() {
		loading = true;
		error = null;
		try {
			const params = new URLSearchParams();
			params.set('page', String(currentPage));
			params.set('page_size', String(pageSize));
			if (actionFilter) params.set('action', actionFilter);
			if (usernameFilter) params.set('username', usernameFilter);
			if (targetTypeFilter) params.set('target_type', targetTypeFilter);
			if (fromDate) params.set('from_date', fromDate);
			if (toDate) params.set('to_date', toDate);

			const data = await apiFetch<PaginatedResponse<AuditEntry>>(`/api/audit?${params.toString()}`);
			entries = data.items;
			total = data.total;
		} catch {
			error = 'Failed to load audit entries';
		}
		loading = false;
	}

	async function verifyChain() {
		verifying = true;
		try {
			verifyResult = await apiFetch<AuditVerifyResult>('/api/audit/verify');
		} catch {
			verifyResult = null;
		}
		verifying = false;
	}

	function applyFilters() {
		currentPage = 1;
		loadEntries();
	}

	function goToPage(p: number) {
		currentPage = p;
		loadEntries();
	}

	function toggleExpanded(id: number) {
		const next = new Set(expandedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		expandedIds = next;
	}

	const totalPages = $derived(Math.ceil(total / pageSize));

	function formatDetail(detail: string | null): string {
		if (!detail) return '';
		try {
			const parsed = JSON.parse(detail);
			return JSON.stringify(parsed, null, 2);
		} catch {
			return detail;
		}
	}
</script>

<svelte:head>
	<title>Audit Log — Iris Admin</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">Audit Log</li>
	</ol>
</nav>

<div class="flex items-center justify-between">
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Audit Log</h1>

	<!-- Chain Verification Badge -->
	<div class="flex items-center gap-2">
		{#if verifying}
			<span class="text-sm" style="color: var(--color-muted)">Verifying chain...</span>
		{:else if verifyResult}
			<span
				class="rounded px-3 py-1 text-sm font-medium"
				style="background: {verifyResult.valid ? 'var(--color-success)' : 'var(--color-danger)'}; color: var(--color-bg)"
			>
				Chain {verifyResult.valid ? 'Valid' : 'Invalid'} ({verifyResult.entries_checked} entries)
			</span>
		{/if}
	</div>
</div>

<p class="mt-1" style="color: var(--color-muted)">View system audit trail with SHA-256 hash chain verification.</p>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3 items-end">
	<div>
		<label for="audit-action" class="block text-xs" style="color: var(--color-muted)">Action</label>
		<input
			id="audit-action"
			bind:value={actionFilter}
			type="text"
			placeholder="e.g. POST"
			class="mt-1 rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="audit-username" class="block text-xs" style="color: var(--color-muted)">Username</label>
		<input
			id="audit-username"
			bind:value={usernameFilter}
			type="text"
			placeholder="Filter by user"
			class="mt-1 rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="audit-target" class="block text-xs" style="color: var(--color-muted)">Target Type</label>
		<input
			id="audit-target"
			bind:value={targetTypeFilter}
			type="text"
			placeholder="e.g. entity"
			class="mt-1 rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="audit-from-date" class="block text-xs" style="color: var(--color-muted)">From Date</label>
		<input
			id="audit-from-date"
			bind:value={fromDate}
			type="date"
			class="mt-1 rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="audit-to-date" class="block text-xs" style="color: var(--color-muted)">To Date</label>
		<input
			id="audit-to-date"
			bind:value={toDate}
			type="date"
			class="mt-1 rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<button
		onclick={applyFilters}
		class="rounded px-4 py-2 text-sm font-medium"
		style="background: var(--color-primary); color: var(--color-bg)"
	>
		Apply Filters
	</button>
</div>

<!-- Table -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading audit entries...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if entries.length === 0}
		<p style="color: var(--color-muted)">No audit entries found.</p>
	{:else}
		<p class="mb-2 text-sm" style="color: var(--color-muted)">{total} total entries — page {currentPage} of {totalPages}</p>
		<table class="w-full text-sm">
			<thead>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<th class="py-2 text-left" style="color: var(--color-muted)">ID</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Timestamp</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">User</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Action</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Target</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Detail</th>
				</tr>
			</thead>
			<tbody>
				{#each entries as entry}
					<tr style="border-bottom: 1px solid var(--color-border)">
						<td class="py-2 font-mono text-xs" style="color: var(--color-muted)">{entry.id}</td>
						<td class="py-2 text-xs" style="color: var(--color-fg)">{entry.timestamp}</td>
						<td class="py-2" style="color: var(--color-fg)">{entry.username}</td>
						<td class="py-2" style="color: var(--color-fg)">{entry.action}</td>
						<td class="py-2" style="color: var(--color-fg)">
							{entry.target_type}{entry.target_id ? ` (${entry.target_id.slice(0, 8)}...)` : ''}
						</td>
						<td class="py-2">
							{#if entry.detail}
								<button
									onclick={() => toggleExpanded(entry.id)}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-primary)"
									aria-expanded={expandedIds.has(entry.id)}
								>
									{expandedIds.has(entry.id) ? 'Hide' : 'Show'}
								</button>
							{:else}
								<span class="text-xs" style="color: var(--color-muted)">—</span>
							{/if}
						</td>
					</tr>
					{#if expandedIds.has(entry.id) && entry.detail}
						<tr>
							<td colspan="6" class="py-2">
								<pre
									class="overflow-x-auto rounded p-3 text-xs"
									style="background: var(--color-surface); color: var(--color-fg); max-height: 300px"
								>{formatDetail(entry.detail)}</pre>
							</td>
						</tr>
					{/if}
				{/each}
			</tbody>
		</table>

		<!-- Pagination -->
		{#if totalPages > 1}
			<div class="mt-4 flex items-center gap-2">
				<button
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage <= 1}
					class="rounded border px-3 py-1 text-sm"
					style="border-color: var(--color-border); color: {currentPage <= 1 ? 'var(--color-muted)' : 'var(--color-primary)'}"
				>
					Previous
				</button>
				{#each Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
					const start = Math.max(1, Math.min(currentPage - 2, totalPages - 4));
					return start + i;
				}).filter(p => p <= totalPages) as p}
					<button
						onclick={() => goToPage(p)}
						class="rounded px-3 py-1 text-sm"
						style={p === currentPage
							? 'background: var(--color-primary); color: var(--color-bg)'
							: 'border: 1px solid var(--color-border); color: var(--color-fg)'}
					>
						{p}
					</button>
				{/each}
				<button
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage >= totalPages}
					class="rounded border px-3 py-1 text-sm"
					style="border-color: var(--color-border); color: {currentPage >= totalPages ? 'var(--color-muted)' : 'var(--color-primary)'}"
				>
					Next
				</button>
			</div>
		{/if}
	{/if}
</div>
