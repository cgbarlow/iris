<script lang="ts">
	/**
	 * EntityImagesEditor (ADR-209, issue #194).
	 *
	 * Reusable gallery + upload control mounted on every entity
	 * details screen (collection, set, package, view, element).
	 *
	 * Read mode: a grid of thumbnails. Each opens the image at full
	 * size on click.
	 *
	 * Edit mode: same grid + a "+ Upload" tile + per-image "Remove"
	 * buttons. Hits the v6.17.0 attachment endpoints.
	 */
	import { onMount } from 'svelte';
	import { apiFetch } from '$lib/utils/api';
	import { imageUrl } from '$lib/utils/imageUrl';

	interface EntityImage {
		id: string;
		entity_type: string;
		entity_id: string;
		image_id: string;
		display_order: number;
		image_mime: string;
		image_size_bytes: number;
		created_at: string;
		created_by: string;
	}

	interface Props {
		entityType: 'collection' | 'set' | 'package' | 'diagram' | 'element';
		entityId: string;
		editing?: boolean;
	}

	let { entityType, entityId, editing = false }: Props = $props();

	let attachments = $state<EntityImage[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let busyUpload = $state(false);
	let lightboxImage = $state<EntityImage | null>(null);

	const MAX_BYTES = 5 * 1024 * 1024;
	const ALLOWED_MIMES = new Set([
		'image/png', 'image/jpeg', 'image/gif', 'image/webp',
	]);

	async function load() {
		loading = true;
		error = null;
		try {
			attachments = await apiFetch<EntityImage[]>(
				`/api/${entityType}/${encodeURIComponent(entityId)}/images`,
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load images.';
			attachments = [];
		} finally {
			loading = false;
		}
	}

	onMount(load);
	// Re-load when entityId changes (parent navigated to a different entity).
	$effect(() => {
		// Read entityId reactively.
		entityId;
		load();
	});

	async function onFile(e: Event) {
		const f = (e.target as HTMLInputElement).files?.[0];
		if (!f) return;
		if (!ALLOWED_MIMES.has(f.type)) {
			error = `Unsupported file type ${f.type}. Use PNG, JPEG, GIF, or WebP.`;
			return;
		}
		if (f.size > MAX_BYTES) {
			error = `File is ${(f.size / 1024 / 1024).toFixed(1)} MB; max is 5 MB.`;
			return;
		}
		busyUpload = true;
		error = null;
		try {
			const fd = new FormData();
			fd.append('file', f);
			await apiFetch(
				`/api/${entityType}/${encodeURIComponent(entityId)}/images`,
				{ method: 'POST', body: fd },
			);
			await load();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed.';
		} finally {
			busyUpload = false;
			// Reset the file input so the same file can be picked again.
			(e.target as HTMLInputElement).value = '';
		}
	}

	async function remove(att: EntityImage) {
		if (!confirm('Remove this image from this entity?')) return;
		try {
			await apiFetch(
				`/api/${entityType}/${encodeURIComponent(entityId)}/images/${att.id}`,
				{ method: 'DELETE' },
			);
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Remove failed.';
		}
	}
</script>

<section class="ent-images" aria-label="Attached images">
	{#if loading}
		<p class="ent-images__hint">Loading images…</p>
	{:else}
		{#if attachments.length === 0 && !editing}
			<!-- Hidden when nothing to show and not editing — avoids clutter. -->
		{:else}
			<div class="ent-images__grid">
				{#each attachments as att (att.id)}
					<div class="ent-images__cell">
						<button
							type="button"
							class="ent-images__thumb"
							onclick={() => (lightboxImage = att)}
							aria-label="View image"
						>
							<img
								src={imageUrl(att.image_id)}
								alt=""
								loading="lazy"
							/>
						</button>
						{#if editing}
							<button
								type="button"
								class="ent-images__remove"
								onclick={() => remove(att)}
								aria-label="Remove image"
								title="Remove"
							>×</button>
						{/if}
					</div>
				{/each}
				{#if editing}
					<label class="ent-images__upload">
						<input
							type="file"
							accept="image/png,image/jpeg,image/gif,image/webp"
							onchange={onFile}
							disabled={busyUpload}
						/>
						<span>{busyUpload ? 'Uploading…' : '+ Upload'}</span>
					</label>
				{/if}
			</div>
		{/if}
	{/if}

	{#if error}
		<p class="ent-images__error" role="alert">{error}</p>
	{/if}
</section>

{#if lightboxImage}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="ent-images__lightbox"
		onclick={() => (lightboxImage = null)}
		onkeydown={(e) => { if (e.key === 'Escape') lightboxImage = null; }}
		role="presentation"
	>
		<img src={imageUrl(lightboxImage.image_id)} alt="" />
	</div>
{/if}

<style>
	.ent-images {
		margin-top: 12px;
	}
	.ent-images__grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: 8px;
	}
	.ent-images__cell {
		position: relative;
		aspect-ratio: 1;
		background: var(--color-surface, #f3f4f6);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		overflow: hidden;
	}
	.ent-images__thumb {
		display: block;
		width: 100%; height: 100%;
		background: transparent;
		border: 0; padding: 0;
		cursor: pointer;
	}
	.ent-images__thumb img {
		width: 100%; height: 100%;
		object-fit: cover;
	}
	.ent-images__remove {
		position: absolute; top: 2px; right: 2px;
		width: 22px; height: 22px;
		border: 0; border-radius: 50%;
		background: rgba(0, 0, 0, 0.55); color: white;
		font-size: 14px; line-height: 1;
		cursor: pointer;
	}
	.ent-images__upload {
		aspect-ratio: 1;
		display: flex; align-items: center; justify-content: center;
		background: var(--color-bg, #ffffff);
		border: 1px dashed var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 12px;
		color: var(--color-muted, #6b7280);
		cursor: pointer;
	}
	.ent-images__upload input { display: none; }
	.ent-images__upload:hover {
		border-color: var(--color-primary, #2563eb);
		color: var(--color-primary, #2563eb);
	}
	.ent-images__hint {
		font-size: 12px;
		color: var(--color-muted, #6b7280);
	}
	.ent-images__error {
		font-size: 12px;
		color: var(--color-danger, #b91c1c);
	}
	.ent-images__lightbox {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.8);
		display: flex; align-items: center; justify-content: center;
		z-index: 60;
		cursor: zoom-out;
	}
	.ent-images__lightbox img {
		max-width: 92vw; max-height: 92vh;
		object-fit: contain;
	}
</style>
