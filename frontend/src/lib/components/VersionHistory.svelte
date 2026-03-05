<script lang="ts">
	/**
	 * VersionHistory: Shared version history display component.
	 * Card-based layout showing version, change type, summary, date, and author.
	 * Used by diagram, element, and package detail pages.
	 */

	interface VersionEntry {
		version: number;
		change_type: string;
		change_summary: string | null;
		created_at: string;
		created_by: string;
		created_by_username?: string;
	}

	interface Props {
		versions: VersionEntry[];
		loading?: boolean;
	}

	let { versions, loading = false }: Props = $props();
</script>

{#if loading}
	<p style="color: var(--color-muted)">Loading versions...</p>
{:else if versions.length === 0}
	<p style="color: var(--color-muted)">No version history.</p>
{:else}
	<div class="space-y-3">
		{#each versions as v}
			<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium" style="color: var(--color-fg)">
						v{v.version} — {v.change_type}
					</span>
					<span class="text-xs" style="color: var(--color-muted)">{v.created_at}</span>
				</div>
				{#if v.change_summary}
					<p class="mt-1 text-sm" style="color: var(--color-muted)">{v.change_summary}</p>
				{/if}
				<p class="mt-1 text-xs" style="color: var(--color-muted)">
					by {v.created_by_username ?? v.created_by}
				</p>
			</div>
		{/each}
	</div>
{/if}
