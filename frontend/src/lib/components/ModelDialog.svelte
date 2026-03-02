<script lang="ts">
	/** Dialog for creating/editing models. */
	import DOMPurify from 'dompurify';
	import TagInput from '$lib/components/TagInput.svelte';

	interface Props {
		open: boolean;
		mode: 'create' | 'edit';
		initialName?: string;
		initialType?: string;
		initialDescription?: string;
		initialTags?: string[];
		initialIsTemplate?: boolean;
		suggestions?: string[];
		inheritedTags?: string[];
		onsave: (name: string, modelType: string, description: string, tags?: string[], isTemplate?: boolean) => void;
		oncancel: () => void;
	}

	let {
		open,
		mode,
		initialName = '',
		initialType = 'component',
		initialDescription = '',
		initialTags = [],
		initialIsTemplate = false,
		suggestions = [],
		inheritedTags = [],
		onsave,
		oncancel,
	}: Props = $props();

	let name = $state('');
	let modelType = $state('');
	let description = $state('');
	let tags = $state<string[]>([]);
	let isTemplate = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	const MODEL_TYPES = [
		{ value: 'simple', label: 'Simple' },
		{ value: 'component', label: 'Component' },
		{ value: 'sequence', label: 'Sequence' },
		{ value: 'uml', label: 'UML' },
		{ value: 'archimate', label: 'ArchiMate' },
		{ value: 'roadmap', label: 'Roadmap' },
	];

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = initialName;
			modelType = initialType;
			description = initialDescription;
			tags = [...initialTags];
			isTemplate = initialIsTemplate;
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleAddTag(tag: string) {
		if (!tags.includes(tag)) {
			tags = [...tags, tag];
		}
	}

	function handleRemoveTag(tag: string) {
		tags = tags.filter((t) => t !== tag);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const sanitizedName = DOMPurify.sanitize(name.trim());
		const sanitizedType = DOMPurify.sanitize(modelType.trim());
		const sanitizedDesc = DOMPurify.sanitize(description.trim());
		if (sanitizedName && sanitizedType) {
			if (mode === 'edit') {
				onsave(sanitizedName, sanitizedType, sanitizedDesc, tags, isTemplate);
			} else {
				onsave(sanitizedName, sanitizedType, sanitizedDesc);
			}
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			oncancel();
		}
	}
</script>

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="model-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="model-dialog-title" class="text-lg font-bold">
			{mode === 'create' ? 'Create Model' : 'Edit Model'}
		</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="model-name" class="block text-sm font-medium">Name</label>
				<input
					id="model-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label for="model-type" class="block text-sm font-medium">Model Type</label>
				{#if mode === 'create'}
					<select
						id="model-type"
						bind:value={modelType}
						required
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="" disabled>Select a type…</option>
						{#each MODEL_TYPES as t}
							<option value={t.value}>{t.label}</option>
						{/each}
					</select>
				{:else}
					<input
						id="model-type"
						value={modelType}
						readonly
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-muted)"
					/>
				{/if}
			</div>

			<div>
				<label for="model-description" class="block text-sm font-medium">Description</label>
				<textarea
					id="model-description"
					bind:value={description}
					rows="3"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</div>

			{#if mode === 'edit'}
				<div>
					<label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
						<input
							type="checkbox"
							bind:checked={isTemplate}
							aria-label="Mark as template"
						/>
						Template
					</label>
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Mark this model as a reusable template</p>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2">Tags</label>
					<TagInput
						{tags}
						onaddtag={handleAddTag}
						onremovetag={handleRemoveTag}
						{inheritedTags}
						{suggestions}
					/>
				</div>
			{/if}

			<div class="flex justify-end gap-3">
				<button
					type="button"
					onclick={oncancel}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Cancel
				</button>
				<button
					type="submit"
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					{mode === 'create' ? 'Create' : 'Save'}
				</button>
			</div>
		</form>
	</dialog>
{/if}
