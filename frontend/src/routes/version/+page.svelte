<script lang="ts">
	/**
	 * /version (v6.17.4+): shows the deployed version of every Iris
	 * component plus the build's git commit sha. Frontend version is
	 * baked in at build time from `frontend/package.json`. Backend,
	 * MCP and CLI versions plus git sha come from `GET /api/version`.
	 *
	 * v6.17.5 convention: all four pyproject.toml / package.json
	 * versions are bumped together on each Iris release so the numbers
	 * in this table always match. The git sha is the ground-truth
	 * signal if the package numbers ever diverge.
	 */
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/utils/api';
	import pkg from '../../../package.json';

	const FRONTEND_VERSION: string = (pkg as { version: string }).version;

	interface VersionResponse {
		backend: string | null;
		mcp: string | null;
		cli: string | null;
		git_sha: string | null;
	}

	let loading = $state(true);
	let error = $state<string | null>(null);
	let versions = $state<VersionResponse | null>(null);

	const allMatchExpected = $derived.by(() => {
		if (!versions) return null;
		const all = [
			FRONTEND_VERSION,
			versions.backend,
			versions.mcp,
			versions.cli,
		].filter((v): v is string => !!v);
		if (all.length === 0) return null;
		return all.every((v) => v === all[0]);
	});

	onMount(async () => {
		try {
			versions = await apiFetch<VersionResponse>('/api/version');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load versions.';
		} finally {
			loading = false;
		}
	});

	function shortSha(sha: string | null | undefined): string {
		return sha ? sha.slice(0, 7) : '—';
	}
</script>

<svelte:head>
	<title>Version — Iris</title>
</svelte:head>

<div style="max-width: 600px">
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Iris versions</h1>

	{#if !loading}
		<div class="mt-4 rounded border p-4" style="border-color: var(--color-border); background: var(--color-surface)">
			<div class="text-xs uppercase tracking-wide" style="color: var(--color-muted)">Iris release</div>
			<div class="mt-1 font-mono text-2xl" style="color: var(--color-fg)">v{FRONTEND_VERSION}</div>
			{#if versions?.git_sha}
				<div class="mt-2 text-xs" style="color: var(--color-muted)">
					commit <span class="font-mono">{shortSha(versions.git_sha)}</span>
				</div>
			{/if}
		</div>
	{/if}

	<h2 class="mt-6 text-sm font-semibold" style="color: var(--color-fg)">Components</h2>

	{#if loading}
		<p class="mt-2 text-sm" style="color: var(--color-muted)">Loading…</p>
	{:else}
		<table class="mt-2 w-full text-sm">
			<thead>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<th class="py-2 text-left" style="color: var(--color-muted)">Component</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Version</th>
				</tr>
			</thead>
			<tbody>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<td class="py-2" style="color: var(--color-fg)">Frontend (SPA)</td>
					<td class="py-2 font-mono" style="color: var(--color-fg)">{FRONTEND_VERSION}</td>
				</tr>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<td class="py-2" style="color: var(--color-fg)">Backend (FastAPI)</td>
					<td class="py-2 font-mono" style="color: var(--color-fg)">{versions?.backend ?? '—'}</td>
				</tr>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<td class="py-2" style="color: var(--color-fg)">MCP server</td>
					<td class="py-2 font-mono" style="color: var(--color-fg)">{versions?.mcp ?? '—'}</td>
				</tr>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<td class="py-2" style="color: var(--color-fg)">CLI / iris-client</td>
					<td class="py-2 font-mono" style="color: var(--color-fg)">{versions?.cli ?? '—'}</td>
				</tr>
			</tbody>
		</table>

		{#if allMatchExpected === false}
			<p class="mt-3 text-xs" style="color: var(--color-warning, #b45309)">
				⚠ Component versions diverge. One or more components is out of sync — check the git sha above against the GitHub release tag to confirm what's actually deployed.
			</p>
		{/if}

		{#if error}
			<p class="mt-3 text-sm" style="color: var(--color-danger, #b91c1c)" role="alert">
				Backend version fetch failed: {error}. Frontend version is rendered above.
			</p>
		{/if}
	{/if}
</div>
