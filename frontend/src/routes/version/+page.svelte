<script lang="ts">
	/**
	 * /version (v6.17.4): shows the deployed version of every Iris
	 * component. Frontend version is baked in at build time from
	 * `frontend/package.json` (Vite injects via `__APP_VERSION__`).
	 * Backend, MCP and CLI versions are fetched from
	 * `GET /api/version`, which reads each component's pyproject.toml
	 * at backend startup.
	 */
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/utils/api';
	import pkg from '../../../package.json';

	const FRONTEND_VERSION: string = (pkg as { version: string }).version;

	interface VersionResponse {
		backend: string | null;
		mcp: string | null;
		cli: string | null;
	}

	let loading = $state(true);
	let error = $state<string | null>(null);
	let versions = $state<VersionResponse | null>(null);

	onMount(async () => {
		try {
			versions = await apiFetch<VersionResponse>('/api/version');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load versions.';
		} finally {
			loading = false;
		}
	});

	function row(name: string, version: string | null | undefined): { name: string; version: string } {
		return { name, version: version ?? '—' };
	}
</script>

<svelte:head>
	<title>Version — Iris</title>
</svelte:head>

<div style="max-width: 600px">
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Iris versions</h1>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">
		Deployed versions of each Iris component. Refresh after a release
		to confirm the new build is live.
	</p>

	{#if loading}
		<p class="mt-4 text-sm" style="color: var(--color-muted)">Loading…</p>
	{:else}
		<table class="mt-4 w-full text-sm">
			<thead>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<th class="py-2 text-left" style="color: var(--color-muted)">Component</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Version</th>
				</tr>
			</thead>
			<tbody>
				{#each [
					row('Frontend (SPA)', FRONTEND_VERSION),
					row('Backend (FastAPI)', versions?.backend ?? null),
					row('MCP server', versions?.mcp ?? null),
					row('CLI / iris-client', versions?.cli ?? null),
				] as r (r.name)}
					<tr style="border-bottom: 1px solid var(--color-border)">
						<td class="py-2" style="color: var(--color-fg)">{r.name}</td>
						<td class="py-2 font-mono" style="color: var(--color-fg)">{r.version}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if error}
			<p class="mt-3 text-sm" style="color: var(--color-danger, #b91c1c)" role="alert">
				Backend version fetch failed: {error}. Frontend version is rendered above.
			</p>
		{/if}
	{/if}
</div>
