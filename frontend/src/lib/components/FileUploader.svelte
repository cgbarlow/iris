<script lang="ts">
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import { API_BASE_URL } from '$lib/config.js';
	import type { FileExtractResponse } from '$lib/types/api';

	const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

	export type UploadedFile = {
		id: string;
		filename: string;
		content_type: string;
		size_bytes: number;
		extracted_text: string;
		truncated: boolean;
		error: string | null;
		uploading: boolean;
	};

	interface Props {
		files: UploadedFile[];
		onchange: (files: UploadedFile[]) => void;
	}

	let { files, onchange }: Props = $props();

	let dragOver = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function uploadFile(fileObj: File) {
		if (fileObj.size > MAX_FILE_SIZE) {
			const entry: UploadedFile = {
				id: crypto.randomUUID(),
				filename: fileObj.name,
				content_type: fileObj.type || 'application/octet-stream',
				size_bytes: fileObj.size,
				extracted_text: '',
				truncated: false,
				error: `File exceeds 5 MB limit (${formatSize(fileObj.size)})`,
				uploading: false,
			};
			onchange([...files, entry]);
			return;
		}

		const id = crypto.randomUUID();
		const placeholder: UploadedFile = {
			id,
			filename: fileObj.name,
			content_type: fileObj.type || 'application/octet-stream',
			size_bytes: fileObj.size,
			extracted_text: '',
			truncated: false,
			error: null,
			uploading: true,
		};
		onchange([...files, placeholder]);

		try {
			const formData = new FormData();
			formData.append('file', fileObj);

			const token = getAccessToken();
			const resp = await fetch(`${API_BASE_URL}/api/ai/files/extract`, {
				method: 'POST',
				headers: token ? { Authorization: `Bearer ${token}` } : {},
				body: formData,
			});

			if (!resp.ok) {
				const errText = await resp.text();
				onchange(
					files.map((f) =>
						f.id === id
							? { ...f, uploading: false, error: `Upload failed: ${errText}` }
							: f
					)
				);
				return;
			}

			const result: FileExtractResponse = await resp.json();
			onchange(
				files.map((f) =>
					f.id === id
						? {
								...f,
								content_type: result.content_type,
								size_bytes: result.size_bytes,
								extracted_text: result.extracted_text,
								truncated: result.truncated,
								error: result.error,
								uploading: false,
							}
						: f
				)
			);
		} catch (err) {
			onchange(
				files.map((f) =>
					f.id === id
						? { ...f, uploading: false, error: `Upload failed: ${err}` }
						: f
				)
			);
		}
	}

	function handleFiles(fileList: FileList | File[]) {
		for (const f of fileList) {
			uploadFile(f);
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
		const droppedFiles = event.dataTransfer?.files;
		if (droppedFiles) handleFiles(droppedFiles);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleFileInput(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files) {
			handleFiles(input.files);
			input.value = '';
		}
	}

	function removeFile(id: string) {
		onchange(files.filter((f) => f.id !== id));
	}
</script>

<div>
	<span class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Files</span>

	<!-- Drop zone -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="rounded border-2 border-dashed px-4 py-3 text-center text-sm transition-colors"
		style="border-color: {dragOver ? 'var(--color-primary)' : 'var(--color-border)'}; background: {dragOver ? 'var(--color-primary-muted, rgba(59,130,246,0.05))' : 'var(--color-bg)'}; color: var(--color-muted); cursor: pointer"
		ondrop={handleDrop}
		ondragover={handleDragOver}
		ondragleave={handleDragLeave}
		onclick={() => fileInput?.click()}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInput?.click(); }}
		role="button"
		tabindex="0"
		aria-label="Upload files by dropping or clicking"
	>
		Drop files here or click to browse
		<input
			bind:this={fileInput}
			type="file"
			multiple
			class="hidden"
			onchange={handleFileInput}
		/>
	</div>

	<!-- File list -->
	{#if files.length > 0}
		<ul class="mt-2 space-y-1">
			{#each files as file (file.id)}
				<li
					class="flex items-center gap-2 rounded px-2 py-1 text-sm"
					style="background: var(--color-surface); color: var(--color-fg)"
				>
					<span class="flex-1 truncate" title={file.filename}>
						{file.filename}
						<span class="text-xs" style="color: var(--color-muted)">
							({formatSize(file.size_bytes)})
						</span>
					</span>

					{#if file.uploading}
						<span class="text-xs" style="color: var(--color-muted)">Extracting...</span>
					{:else if file.error}
						<span class="text-xs" style="color: var(--color-danger, #ef4444)" title={file.error}>Error</span>
					{:else if file.truncated}
						<span class="text-xs" style="color: var(--color-warning, #f59e0b)" title="File content was truncated due to size">Truncated</span>
					{:else}
						<span class="text-xs" style="color: var(--color-success, #22c55e)">Ready</span>
					{/if}

					<button
						onclick={() => removeFile(file.id)}
						class="ml-1 text-sm hover:opacity-70"
						style="color: var(--color-muted)"
						title="Remove file"
						aria-label="Remove {file.filename}"
					>
						&times;
					</button>
				</li>
			{/each}
		</ul>
	{/if}

	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		Max 5 MB per file. Text is extracted for AI context.
	</p>
</div>
