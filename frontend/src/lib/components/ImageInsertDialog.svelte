<script lang="ts">
	/**
	 * ImageInsertDialog (ADR-209, issue #194).
	 *
	 * Modal shown when the markdown editor's image button is clicked.
	 * Two tabs:
	 *
	 *  - **Link**:   user types a URL + optional alt text → emits
	 *    `![alt](url)` for the caller to splice at the cursor.
	 *  - **Upload**: user picks a file → POSTed to /api/images → emits
	 *    `![alt](/api/images/<id>)`.
	 *
	 * Client-side validation mirrors the server-side validation in
	 * backend/app/images/service.py: 5 MB cap, png|jpeg|gif|webp.
	 */
	import { apiFetch } from '$lib/utils/api';

	interface Props {
		open: boolean;
		oninsert: (markdown: string) => void;
		oncancel: () => void;
	}

	let { open, oninsert, oncancel }: Props = $props();

	type Mode = 'link' | 'upload';
	let mode = $state<Mode>('link');
	let url = $state('');
	let alt = $state('');
	let file = $state<File | null>(null);
	let busy = $state(false);
	let error = $state<string | null>(null);

	const MAX_BYTES = 5 * 1024 * 1024;
	const ALLOWED_MIMES = new Set([
		'image/png',
		'image/jpeg',
		'image/gif',
		'image/webp',
	]);

	function reset() {
		url = '';
		alt = '';
		file = null;
		busy = false;
		error = null;
		mode = 'link';
	}

	function onPickFile(e: Event) {
		const f = (e.target as HTMLInputElement).files?.[0] ?? null;
		if (f && !ALLOWED_MIMES.has(f.type)) {
			error = `Unsupported file type ${f.type}. Use PNG, JPEG, GIF, or WebP.`;
			file = null;
			return;
		}
		if (f && f.size > MAX_BYTES) {
			error = `File is ${(f.size / 1024 / 1024).toFixed(1)} MB; max is 5 MB.`;
			file = null;
			return;
		}
		error = null;
		file = f;
	}

	function submitLink() {
		const cleaned = url.trim();
		if (!cleaned) { error = 'URL is required.'; return; }
		oninsert(`![${alt}](${cleaned})`);
		reset();
	}

	async function submitUpload() {
		if (!file) { error = 'Choose a file first.'; return; }
		busy = true;
		error = null;
		try {
			const fd = new FormData();
			fd.append('file', file);
			const r = await apiFetch<{ id: string }>('/api/images', {
				method: 'POST',
				body: fd,
			});
			oninsert(`![${alt}](/api/images/${r.id})`);
			reset();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Upload failed.';
		} finally {
			busy = false;
		}
	}

	function close() {
		reset();
		oncancel();
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="img-dialog__scrim"
		onclick={close}
		onkeydown={(e) => { if (e.key === 'Escape') close(); }}
		role="presentation"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="img-dialog"
			role="dialog"
			aria-label="Insert image"
			aria-modal="true"
			onclick={(e) => e.stopPropagation()}
		>
			<header class="img-dialog__header">
				<h3>Insert image</h3>
				<button type="button" onclick={close} aria-label="Close">✕</button>
			</header>

			<div class="img-dialog__tabs" role="tablist">
				<button
					type="button"
					role="tab"
					aria-selected={mode === 'link'}
					class:active={mode === 'link'}
					onclick={() => { mode = 'link'; error = null; }}
				>Link</button>
				<button
					type="button"
					role="tab"
					aria-selected={mode === 'upload'}
					class:active={mode === 'upload'}
					onclick={() => { mode = 'upload'; error = null; }}
				>Upload</button>
			</div>

			<div class="img-dialog__body" role="tabpanel">
				{#if mode === 'link'}
					<label class="img-dialog__field">
						URL
						<input
							type="url"
							bind:value={url}
							placeholder="https://example.com/image.png"
							autocomplete="off"
						/>
					</label>
					<label class="img-dialog__field">
						Alt text <span class="img-dialog__hint">(optional)</span>
						<input type="text" bind:value={alt} autocomplete="off" />
					</label>
				{:else}
					<label class="img-dialog__field">
						File
						<input
							type="file"
							accept="image/png,image/jpeg,image/gif,image/webp"
							onchange={onPickFile}
						/>
					</label>
					<label class="img-dialog__field">
						Alt text <span class="img-dialog__hint">(optional)</span>
						<input type="text" bind:value={alt} autocomplete="off" />
					</label>
					<p class="img-dialog__hint">PNG / JPEG / GIF / WebP, max 5 MB.</p>
				{/if}

				{#if error}
					<p class="img-dialog__error" role="alert">{error}</p>
				{/if}
			</div>

			<footer class="img-dialog__footer">
				<button type="button" onclick={close}>Cancel</button>
				{#if mode === 'link'}
					<button
						type="button"
						class="img-dialog__primary"
						onclick={submitLink}
						disabled={!url.trim()}
					>Insert</button>
				{:else}
					<button
						type="button"
						class="img-dialog__primary"
						onclick={submitUpload}
						disabled={!file || busy}
					>{busy ? 'Uploading…' : 'Upload + insert'}</button>
				{/if}
			</footer>
		</div>
	</div>
{/if}

<style>
	.img-dialog__scrim {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex; align-items: center; justify-content: center;
		z-index: 50;
	}
	.img-dialog {
		min-width: 380px;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 8px;
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
		display: flex; flex-direction: column;
	}
	.img-dialog__header {
		display: flex; justify-content: space-between; align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
	}
	.img-dialog__header h3 { font-size: 15px; font-weight: 600; }
	.img-dialog__header button {
		background: transparent; border: 0;
		font-size: 14px; cursor: pointer;
		color: var(--color-muted, #6b7280);
	}
	.img-dialog__tabs {
		display: flex; gap: 0;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		padding: 0 16px;
	}
	.img-dialog__tabs button {
		padding: 8px 16px;
		background: transparent; border: 0;
		font-size: 13px;
		color: var(--color-muted, #6b7280);
		cursor: pointer;
		border-bottom: 2px solid transparent;
	}
	.img-dialog__tabs button.active {
		color: var(--color-primary, #2563eb);
		border-bottom-color: var(--color-primary, #2563eb);
	}
	.img-dialog__body {
		padding: 16px;
		display: flex; flex-direction: column; gap: 12px;
	}
	.img-dialog__field {
		display: flex; flex-direction: column; gap: 4px;
		font-size: 12px;
		color: var(--color-fg, #111827);
	}
	.img-dialog__field input[type="url"],
	.img-dialog__field input[type="text"],
	.img-dialog__field input[type="file"] {
		padding: 6px 8px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 13px;
		background: var(--color-bg, #ffffff);
		color: var(--color-fg, #111827);
	}
	.img-dialog__hint {
		color: var(--color-muted, #6b7280);
		font-size: 11px;
		font-weight: 400;
	}
	.img-dialog__error {
		color: var(--color-danger, #b91c1c);
		font-size: 12px;
		margin: 0;
	}
	.img-dialog__footer {
		display: flex; justify-content: flex-end; gap: 8px;
		padding: 12px 16px;
		border-top: 1px solid var(--color-border, #e5e7eb);
	}
	.img-dialog__footer button {
		padding: 6px 12px;
		font-size: 13px;
		background: transparent;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		cursor: pointer;
		color: var(--color-fg, #111827);
	}
	.img-dialog__primary {
		background: var(--color-primary, #2563eb);
		color: white !important;
		border-color: var(--color-primary, #2563eb);
	}
	.img-dialog__primary:disabled {
		opacity: 0.5; cursor: not-allowed;
	}
</style>
