<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import DOMPurify from 'dompurify';

	interface Setting {
		key: string;
		value: string;
		updated_at: string | null;
		updated_by: string | null;
	}

	let settings = $state<Setting[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	let saving = $state(false);
	let regenerating = $state(false);
	let regenSuccess = $state<string | null>(null);
	let regenError = $state<string | null>(null);

	// Form values
	let sessionTimeout = $state(15);
	let thumbnailMode = $state('svg');

	$effect(() => {
		loadSettings();
	});

	async function loadSettings() {
		loading = true;
		try {
			settings = await apiFetch<Setting[]>('/api/settings');
			for (const s of settings) {
				if (s.key === 'session_timeout_minutes') sessionTimeout = Number(s.value) || 15;
				if (s.key === 'gallery_thumbnail_mode') thumbnailMode = s.value;
			}
		} catch {
			error = 'Failed to load settings';
		}
		loading = false;
	}

	async function saveSetting(key: string, value: string) {
		const sanitized = DOMPurify.sanitize(value);
		await apiFetch(`/api/settings/${key}`, {
			method: 'PUT',
			body: JSON.stringify({ value: sanitized }),
		});
	}

	async function regenerateThumbnails() {
		regenerating = true;
		regenSuccess = null;
		regenError = null;
		try {
			const result = await apiFetch<{ count: number }>('/api/admin/thumbnails/regenerate', {
				method: 'POST',
			});
			regenSuccess = `Regenerated ${result.count} model thumbnails`;
		} catch (e) {
			regenError =
				e instanceof ApiError ? e.message : 'Failed to regenerate thumbnails';
		}
		regenerating = false;
	}

	async function saveAll() {
		saving = true;
		error = null;
		success = null;
		try {
			const timeout = Math.max(5, Math.min(480, sessionTimeout));
			await saveSetting('session_timeout_minutes', String(timeout));
			await saveSetting('gallery_thumbnail_mode', thumbnailMode);
			success = 'Settings saved successfully';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save settings';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>Admin Settings — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">Settings</li>
	</ol>
</nav>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Settings</h1>
<p class="mt-2" style="color: var(--color-muted)">Configure system-wide settings.</p>

{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading settings...</p>
{:else}
	{#if error}
		<div
			role="alert"
			class="mt-4 rounded border p-3"
			style="border-color: var(--color-danger); color: var(--color-danger)"
		>
			{error}
		</div>
	{/if}
	{#if success}
		<div
			role="status"
			class="mt-4 rounded border p-3"
			style="border-color: var(--color-success, #16a34a); color: var(--color-success, #16a34a)"
		>
			{success}
		</div>
	{/if}

	<div class="mt-6 flex flex-col gap-6">
		<div class="rounded border p-4" style="border-color: var(--color-border)">
			<h2 class="text-lg font-medium" style="color: var(--color-fg)">Session Timeout</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				How long before a user session expires (minutes).
			</p>
			<div class="mt-3">
				<label for="session-timeout" class="text-sm" style="color: var(--color-fg)"
					>Timeout (minutes)</label
				>
				<input
					id="session-timeout"
					type="number"
					min="5"
					max="480"
					bind:value={sessionTimeout}
					class="mt-1 block rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>
		</div>

		<div class="rounded border p-4" style="border-color: var(--color-border)">
			<h2 class="text-lg font-medium" style="color: var(--color-fg)">Gallery Thumbnails</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				How model thumbnails are displayed in the gallery.
			</p>
			<fieldset class="mt-3">
				<legend class="sr-only">Thumbnail display mode</legend>
				<div class="flex gap-4">
					<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
						<input type="radio" name="thumbnail-mode" value="svg" bind:group={thumbnailMode} />
						SVG (inline)
					</label>
					<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
						<input type="radio" name="thumbnail-mode" value="png" bind:group={thumbnailMode} />
						PNG (server-generated)
					</label>
				</div>
			</fieldset>
		</div>

		<div class="rounded border p-4" style="border-color: var(--color-border)">
			<h2 class="text-lg font-medium" style="color: var(--color-fg)">
				Thumbnail Regeneration
			</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				Regenerate PNG thumbnails for all models across all themes.
			</p>
			{#if regenError}
				<div
					role="alert"
					class="mt-3 rounded border p-3 text-sm"
					style="border-color: var(--color-danger); color: var(--color-danger)"
				>
					{regenError}
				</div>
			{/if}
			{#if regenSuccess}
				<div
					role="status"
					class="mt-3 rounded border p-3 text-sm"
					style="border-color: var(--color-success, #16a34a); color: var(--color-success, #16a34a)"
				>
					{regenSuccess}
				</div>
			{/if}
			<button
				onclick={regenerateThumbnails}
				disabled={regenerating}
				class="mt-3 rounded px-4 py-2 text-sm text-white disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{regenerating ? 'Regenerating...' : 'Regenerate Thumbnails'}
			</button>
		</div>

		<button
			onclick={saveAll}
			disabled={saving}
			class="self-start rounded px-4 py-2 text-sm text-white disabled:opacity-50"
			style="background-color: var(--color-primary)"
		>
			{saving ? 'Saving...' : 'Save Settings'}
		</button>
	</div>
{/if}
