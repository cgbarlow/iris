<script lang="ts">
	/**
	 * VersionHistory: Shared version history display component.
	 * Card-based layout showing version, change type, summary, date, and author.
	 * Supports rollback via optional onrollback callback.
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
		currentVersion?: number;
		onrollback?: (version: number) => void;
	}

	let { versions, loading = false, currentVersion, onrollback }: Props = $props();

	let confirmingVersion = $state<number | null>(null);

	function handleRestore(version: number) {
		if (confirmingVersion === version) {
			onrollback?.(version);
			confirmingVersion = null;
		} else {
			confirmingVersion = version;
		}
	}

	function cancelConfirm() {
		confirmingVersion = null;
	}
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
					<div class="flex items-center gap-2">
						<span class="text-xs" style="color: var(--color-muted)">{v.created_at}</span>
						{#if onrollback && v.version !== currentVersion}
							{#if confirmingVersion === v.version}
								<button
									onclick={() => handleRestore(v.version)}
									class="rounded px-2 py-0.5 text-xs font-medium"
									style="background: var(--color-danger); color: #fff"
								>
									Confirm
								</button>
								<button
									onclick={cancelConfirm}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									Cancel
								</button>
							{:else}
								<button
									onclick={() => handleRestore(v.version)}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									Restore
								</button>
							{/if}
						{:else if v.version === currentVersion}
							<span class="rounded px-2 py-0.5 text-xs" style="color: var(--color-success)">Current</span>
						{/if}
					</div>
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
