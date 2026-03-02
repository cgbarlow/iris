<script lang="ts">
	interface Props {
		page: number;
		pageSize: number;
		total: number;
		onpagechange: (page: number) => void;
		onpagesizechange: (size: number) => void;
	}

	let { page, pageSize, total, onpagechange, onpagesizechange }: Props = $props();

	let totalPages = $derived(Math.max(1, Math.ceil(total / pageSize)));

	let pageNumbers = $derived.by(() => {
		const pages: (number | '...')[] = [];
		if (totalPages <= 7) {
			for (let i = 1; i <= totalPages; i++) pages.push(i);
		} else {
			pages.push(1);
			if (page > 3) pages.push('...');
			const start = Math.max(2, page - 1);
			const end = Math.min(totalPages - 1, page + 1);
			for (let i = start; i <= end; i++) pages.push(i);
			if (page < totalPages - 2) pages.push('...');
			pages.push(totalPages);
		}
		return pages;
	});

	function handleSizeChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		onpagesizechange(parseInt(select.value, 10));
	}
</script>

<nav class="flex flex-wrap items-center justify-between gap-3 py-3" aria-label="Pagination">
	<div class="flex items-center gap-2 text-sm" style="color: var(--color-muted)">
		<span>Show</span>
		<select
			value={pageSize}
			onchange={handleSizeChange}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Page size"
		>
			<option value={25}>25</option>
			<option value={50}>50</option>
			<option value={100}>100</option>
		</select>
		<span>of {total} items</span>
	</div>

	<div class="flex items-center gap-1">
		<button
			onclick={() => onpagechange(page - 1)}
			disabled={page <= 1}
			class="rounded border px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
			style="border-color: var(--color-border); color: var(--color-fg)"
			aria-label="Previous page"
		>
			Prev
		</button>

		{#each pageNumbers as p}
			{#if p === '...'}
				<span class="px-2 py-1 text-sm" style="color: var(--color-muted)">...</span>
			{:else}
				<button
					onclick={() => onpagechange(p)}
					class="rounded border px-3 py-1 text-sm"
					class:font-bold={p === page}
					style="border-color: var(--color-border); {p === page
						? `background: var(--color-primary); color: white`
						: `color: var(--color-fg)`}"
					aria-label="Page {p}"
					aria-current={p === page ? 'page' : undefined}
				>
					{p}
				</button>
			{/if}
		{/each}

		<button
			onclick={() => onpagechange(page + 1)}
			disabled={page >= totalPages}
			class="rounded border px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
			style="border-color: var(--color-border); color: var(--color-fg)"
			aria-label="Next page"
		>
			Next
		</button>
	</div>
</nav>
