<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { isNewerSemver } from '$lib/utils/semverCompare';

	type Extension = {
		id: string;
		name: string;
		description: string | null;
		version: string;
		is_enabled: boolean;
		installed_at: string;
		installed_by: string;
		updated_at: string;
		config: Record<string, unknown>;
		// v5.5.0 (issue #48): source-tracking fields populated by the backend.
		source_method?: string;
		source_url?: string | null;
		latest_version?: string | null;
		latest_version_checked_at?: string | null;
	};

	type KnownExtension = {
		id: string;
		name: string;
		description: string;
		version: string;
		source_method?: string;
		source_url?: string | null;
		supports_auto_upgrade?: boolean;
	};

	const KNOWN_EXTENSIONS: KnownExtension[] = [
		{
			id: 'scenia',
			name: 'Scenia',
			description: 'Open-source roadmapping tool for strategic planning and initiative tracking.',
			version: '1.0.0',
			source_method: 'github',
			source_url: 'https://github.com/cgbarlow/waylonkenning_scenia',
			supports_auto_upgrade: false,
		},
		{
			id: 'mnemos',
			name: 'MNEMOS',
			description:
				'Semantic memory and retrieval service for improved AI context quality across large datasets.',
			version: '1.0.0',
			source_method: 'github',
			source_url: 'https://github.com/ro0TuX777/MNEMOSv2',
			supports_auto_upgrade: true,
		},
		{
			id: 'docref',
			name: 'DocRef',
			description:
				'NZ legislation from legislation.docref.nz as AI context for Iris AI.',
			version: '1.0.0',
			source_method: 'local',
			source_url: null,
			supports_auto_upgrade: false,
		},
	];

	let extensions = $state<Extension[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let actionLoading = $state<string | null>(null);

	$effect(() => {
		loadExtensions();
	});

	async function loadExtensions() {
		loading = true;
		error = null;
		try {
			const data = await apiFetch<{ items: Extension[] }>('/api/extensions');
			extensions = data.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load extensions';
		}
		loading = false;
	}

	function isInstalled(extensionId: string): boolean {
		return extensions.some((e) => e.id === extensionId);
	}

	function getInstalled(extensionId: string): Extension | undefined {
		return extensions.find((e) => e.id === extensionId);
	}

	async function installExtension(known: KnownExtension) {
		actionLoading = known.id;
		error = null;
		try {
			await apiFetch(`/api/extensions/${known.id}/install`, {
				method: 'POST',
				body: JSON.stringify({
					name: known.name,
					description: known.description,
					version: known.version,
				}),
				headers: { 'Content-Type': 'application/json' },
			});
			await loadExtensions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to install extension';
		}
		actionLoading = null;
	}

	async function uninstallExtension(extensionId: string) {
		actionLoading = extensionId;
		error = null;
		try {
			await apiFetch(`/api/extensions/${extensionId}/uninstall`, { method: 'POST' });
			await loadExtensions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to uninstall extension';
		}
		actionLoading = null;
	}

	async function toggleExtension(ext: Extension) {
		actionLoading = ext.id;
		error = null;
		const endpoint = ext.is_enabled ? 'disable' : 'enable';
		try {
			await apiFetch(`/api/extensions/${ext.id}/${endpoint}`, { method: 'POST' });
			await loadExtensions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to toggle extension';
		}
		actionLoading = null;
	}

	// v5.5.0 (issue #48): per-extension Check-Updates + Upgrade flow.
	let checkingUpdate = $state<string | null>(null);
	let upgrading = $state<string | null>(null);

	/**
	 * v5.5.5 (issue #55 follow-up): the registry (KNOWN_EXTENSIONS) is the
	 * canonical source for source_method / source_url. Installed-row values
	 * can be stale — extensions installed before v5.5.0 have
	 * source_method='local' (the m048 default) even though the registry
	 * knows they're github-sourced. Prefer the registry whenever it
	 * declares a non-local source.
	 */
	function effectiveSourceMethod(installed: Extension | undefined, known: KnownExtension): string {
		if (known.source_method && known.source_method !== 'local') return known.source_method;
		return installed?.source_method ?? known.source_method ?? 'local';
	}
	function effectiveSourceUrl(installed: Extension | undefined, known: KnownExtension): string | null {
		return known.source_url ?? installed?.source_url ?? null;
	}

	async function checkForUpdates(extensionId: string) {
		checkingUpdate = extensionId;
		error = null;
		try {
			await apiFetch(`/api/extensions/${extensionId}/check-update`, { method: 'POST' });
			await loadExtensions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to check for updates';
		}
		checkingUpdate = null;
	}

	async function upgradeExtension(extensionId: string) {
		upgrading = extensionId;
		error = null;
		try {
			await apiFetch(`/api/extensions/${extensionId}/upgrade`, { method: 'POST' });
			await loadExtensions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to upgrade extension';
		}
		upgrading = null;
	}

	function updateAvailable(installed: Extension | undefined): boolean {
		if (!installed) return false;
		return isNewerSemver(installed.latest_version, installed.version);
	}

	// MNEMOS reindex
	let reindexing = $state(false);
	let reindexResult = $state<string | null>(null);

	async function reindexMnemos() {
		reindexing = true;
		reindexResult = null;
		error = null;
		try {
			const result = await apiFetch<{ indexed: number; errors: number; duration_ms: number }>(
				'/api/mnemos/reindex',
				{ method: 'POST' },
			);
			reindexResult = `Indexed ${result.indexed} items in ${result.duration_ms}ms` +
				(result.errors > 0 ? ` (${result.errors} errors)` : '');
			setTimeout(() => { reindexResult = null; }, 5000);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Reindex failed';
		}
		reindexing = false;
	}
</script>

<p class="mb-4 text-sm" style="color: var(--color-muted)">Manage optional integrations and extensions.</p>

{#if error}
	<div
		class="mt-4 rounded border p-3 text-sm"
		style="background-color: var(--color-danger-bg, rgba(239,68,68,0.1)); border-color: var(--color-danger); color: var(--color-danger)"
	>
		{error}
	</div>
{/if}

{#if loading}
	<p class="mt-6" style="color: var(--color-muted)">Loading extensions...</p>
{:else}
	<div class="mt-6 space-y-4" style="max-width: 750px">
		{#each KNOWN_EXTENSIONS as known}
			{@const installed = getInstalled(known.id)}
			<div
				class="rounded border p-5"
				style="border-color: var(--color-border); background-color: var(--color-surface)"
			>
				<div class="flex items-start justify-between">
					<div>
						<div class="flex items-center gap-2 flex-wrap">
							<h2 class="text-lg font-semibold" style="color: var(--color-fg)">
								{known.name}
							</h2>
							<!-- v5.5.0 (issue #48): installed/latest version pair -->
							<span class="text-xs" style="color: var(--color-muted)">
								v{installed?.version ?? known.version}
								{#if installed?.latest_version && isNewerSemver(installed.latest_version, installed.version)}
									→ <span style="color: var(--color-fg)">v{installed.latest_version}</span>
								{:else if installed?.latest_version}
									(latest v{installed.latest_version})
								{/if}
							</span>
							<!-- Source method badge -->
							{#if effectiveSourceMethod(installed, known) === 'github'}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: rgba(59, 130, 246, 0.15); color: rgb(37, 99, 235)"
									title="Pulled from GitHub"
								>
									GitHub
								</span>
							{:else if effectiveSourceMethod(installed, known) === 'npm'}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: rgba(220, 38, 38, 0.15); color: rgb(220, 38, 38)"
								>
									npm
								</span>
							{:else}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: var(--color-bg); color: var(--color-muted)"
								>
									Local
								</span>
							{/if}
							<!-- Update-available pill -->
							{#if updateAvailable(installed)}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: rgba(245, 158, 11, 0.18); color: rgb(180, 83, 9)"
									title="A newer release is available on the source repo"
								>
									Update available
								</span>
							{/if}
							{#if installed}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: {installed.is_enabled
										? 'var(--color-success-bg, rgba(34,197,94,0.15))'
										: 'var(--color-warning-bg, rgba(234,179,8,0.15))'}; color: {installed.is_enabled
										? 'var(--color-success, #22c55e)'
										: 'var(--color-warning, #eab308)'}"
								>
									{installed.is_enabled ? 'Enabled' : 'Disabled'}
								</span>
							{:else}
								<span
									class="rounded-full px-2 py-0.5 text-xs font-medium"
									style="background-color: var(--color-bg); color: var(--color-muted)"
								>
									Not installed
								</span>
							{/if}
						</div>
						<p class="mt-1 text-sm" style="color: var(--color-muted)">
							{known.description}
						</p>
						{#if effectiveSourceUrl(installed, known)}
							<p class="mt-1 text-xs">
								<a
									href={effectiveSourceUrl(installed, known) ?? '#'}
									target="_blank"
									rel="noopener noreferrer"
									style="color: var(--color-primary, #3b82f6)"
								>
									{effectiveSourceUrl(installed, known)}
								</a>
							</p>
						{/if}
						{#if installed}
							<p class="mt-2 text-xs" style="color: var(--color-muted)">
								Installed {new Date(installed.installed_at).toLocaleDateString()}
								{#if installed.latest_version_checked_at}
									· Last checked {new Date(installed.latest_version_checked_at).toLocaleDateString()}
								{/if}
							</p>
						{/if}
						{#if known.id === 'mnemos' && installed?.is_enabled && reindexResult}
							<p class="mt-2 text-xs" style="color: var(--color-success, #16a34a)">{reindexResult}</p>
						{/if}
					</div>
					<div class="flex items-center gap-2 flex-wrap">
						{#if installed}
							<!-- v5.5.0 (issue #48): Check for updates is available
								 for github-sourced extensions; Upgrade is available
								 only when latest > installed AND the extension
								 supports automated upgrade. -->
							{#if effectiveSourceMethod(installed, known) === 'github'}
								<button
									onclick={() => checkForUpdates(known.id)}
									disabled={checkingUpdate === known.id}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									{checkingUpdate === known.id ? 'Checking…' : 'Check for updates'}
								</button>
							{/if}
							{#if updateAvailable(installed) && known.supports_auto_upgrade}
								<button
									onclick={() => upgradeExtension(known.id)}
									disabled={upgrading === known.id}
									class="rounded px-3 py-1.5 text-sm font-medium"
									style="background-color: var(--color-primary); color: white"
								>
									{upgrading === known.id ? 'Upgrading…' : `Upgrade to v${installed.latest_version}`}
								</button>
							{/if}
							{#if known.id === 'mnemos' && installed.is_enabled}
								<button
									onclick={reindexMnemos}
									disabled={reindexing}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									{reindexing ? 'Reindexing…' : 'Reindex'}
								</button>
							{/if}
							<button
								onclick={() => toggleExtension(installed)}
								disabled={actionLoading === known.id}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								{installed.is_enabled ? 'Disable' : 'Enable'}
							</button>
							<button
								onclick={() => uninstallExtension(known.id)}
								disabled={actionLoading === known.id}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Uninstall
							</button>
						{:else}
							<button
								onclick={() => installExtension(known)}
								disabled={actionLoading === known.id}
								class="rounded px-3 py-1.5 text-sm font-medium"
								style="background-color: var(--color-primary); color: white"
							>
								Install
							</button>
						{/if}
					</div>
				</div>
			</div>
		{/each}
	</div>
{/if}
