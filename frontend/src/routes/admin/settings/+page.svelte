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
	let seeding = $state(false);
	let seedSuccess = $state<string | null>(null);
	let seedError = $state<string | null>(null);

	// Form values
	let sessionTimeout = $state(15);
	let thumbnailMode = $state('svg');
	let debugAi = $state(false);

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
				if (s.key === 'debug_ai') debugAi = s.value === '1';
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

	async function seedExampleData() {
		seeding = true;
		seedSuccess = null;
		seedError = null;
		try {
			await apiFetch('/api/settings/seed-example-data', { method: 'POST' });
			seedSuccess = 'Example diagrams seeded into the Default set';
		} catch (e) {
			seedError = e instanceof ApiError ? e.message : 'Failed to seed example data';
		}
		seeding = false;
	}

	async function saveAll() {
		saving = true;
		error = null;
		success = null;
		try {
			const timeout = Math.max(5, Math.min(480, sessionTimeout));
			await saveSetting('session_timeout_minutes', String(timeout));
			await saveSetting('gallery_thumbnail_mode', thumbnailMode);
			await saveSetting('debug_ai', debugAi ? '1' : '0');
			success = 'Settings saved successfully';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save settings';
		}
		saving = false;
	}
</script>

<p class="mb-4" style="color: var(--color-muted)">Configure session timeout and system preferences.</p>

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
			<h2 class="text-lg font-medium" style="color: var(--color-fg)">Debug Logging</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				Enable verbose server-side logging for troubleshooting. Logs are written to the backend console.
			</p>
			<div class="mt-3 flex flex-col gap-2">
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input type="checkbox" bind:checked={debugAi} class="h-4 w-4" />
					AI debug logging
					<span class="text-xs" style="color: var(--color-muted)">(prompts, messages, streaming, diagram creation)</span>
				</label>
			</div>
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

		<div class="rounded border p-4" style="border-color: var(--color-border)">
			<h2 class="text-lg font-medium" style="color: var(--color-fg)">
				Seed Example Data
			</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				Populate the Default set with example diagrams (Simple View, UML, ArchiMate, Sequence, DoView). Safe to run multiple times.
			</p>
			{#if seedError}
				<div
					role="alert"
					class="mt-3 rounded border p-3 text-sm"
					style="border-color: var(--color-danger); color: var(--color-danger)"
				>
					{seedError}
				</div>
			{/if}
			{#if seedSuccess}
				<div
					role="status"
					class="mt-3 rounded border p-3 text-sm"
					style="border-color: var(--color-success, #16a34a); color: var(--color-success, #16a34a)"
				>
					{seedSuccess}
				</div>
			{/if}
			<button
				onclick={seedExampleData}
				disabled={seeding}
				class="mt-3 rounded px-4 py-2 text-sm text-white disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{seeding ? 'Seeding...' : 'Seed Example Diagrams'}
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
