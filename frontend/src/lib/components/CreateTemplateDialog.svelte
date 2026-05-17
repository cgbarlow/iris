<script lang="ts">
	/**
	 * "Save as template" dialog (v6.8.0, ADR-191, issue #153).
	 *
	 * Captures a snapshot of the current element with user-chosen
	 * fields. Whitelist matches `INCLUDED_FIELD_WHITELIST` in
	 * `backend/app/element_templates/models.py`. The user can promote
	 * the template to global; otherwise it is scoped to the element's
	 * current set.
	 */
	import DOMPurify from 'dompurify';
	import { apiFetch, ApiError } from '$lib/utils/api';

	const FIELD_OPTIONS: { value: string; label: string }[] = [
		{ value: 'name', label: 'Name' },
		{ value: 'description', label: 'Description' },
		{ value: 'element_type', label: 'Type' },
		{ value: 'notation', label: 'Notation' },
		{ value: 'data', label: 'Data payload' },
		{ value: 'metadata', label: 'Metadata' },
		{ value: 'package_id', label: 'Package membership' },
		{ value: 'tags', label: 'Tags' },
	];

	interface Props {
		open: boolean;
		sourceElementId: string;
		sourceElementName: string;
		setId: string | null;
		oncancel: () => void;
		oncreated: (templateId: string) => void;
	}

	let { open, sourceElementId, sourceElementName, setId, oncancel, oncreated }: Props = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let name = $state('');
	let description = $state('');
	let isGlobal = $state(false);
	let includedSet = $state<Set<string>>(new Set(['name', 'description', 'element_type', 'notation', 'data', 'tags']));
	let submitting = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = sourceElementName ? `${sourceElementName} template` : '';
			description = '';
			isGlobal = false;
			includedSet = new Set(['name', 'description', 'element_type', 'notation', 'data', 'tags']);
			error = null;
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function toggleField(value: string, checked: boolean) {
		const next = new Set(includedSet);
		if (checked) next.add(value);
		else next.delete(value);
		includedSet = next;
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (submitting) return;
		error = null;
		const trimmed = name.trim();
		if (!trimmed) {
			error = 'Template name is required.';
			return;
		}
		const included = [...includedSet];
		if (included.length === 0) {
			error = 'Pick at least one field to capture.';
			return;
		}
		if (!isGlobal && !setId) {
			error = 'Source element has no set — only Global scope is available.';
			return;
		}
		submitting = true;
		try {
			const body: Record<string, unknown> = {
				source_element_id: sourceElementId,
				name: DOMPurify.sanitize(trimmed),
				description: description.trim() ? DOMPurify.sanitize(description.trim()) : null,
				included_fields: included,
				is_global: isGlobal,
				set_id: isGlobal ? null : setId,
			};
			const created = await apiFetch<{ id: string }>('/api/element-templates', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			oncreated(created.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create template';
		}
		submitting = false;
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
		aria-labelledby="create-template-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 460px; max-width: 90vw"
	>
		<h2 id="create-template-title" class="text-lg font-bold">Save as template</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Capture selected fields from <strong style="color: var(--color-fg)">{sourceElementName}</strong>
			so later elements can be pre-filled from this template.
		</p>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="template-name" class="block text-sm font-medium">Template name</label>
				<input
					id="template-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label for="template-description" class="block text-sm font-medium">Description (optional)</label>
				<textarea
					id="template-description"
					bind:value={description}
					rows="2"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</div>

			<fieldset>
				<legend class="text-sm font-medium">Fields to capture</legend>
				<div class="mt-1 grid grid-cols-2 gap-1">
					{#each FIELD_OPTIONS as field (field.value)}
						<label class="flex items-center gap-2 text-sm">
							<input
								type="checkbox"
								checked={includedSet.has(field.value)}
								onchange={(e) => toggleField(field.value, (e.currentTarget as HTMLInputElement).checked)}
							/>
							{field.label}
						</label>
					{/each}
				</div>
			</fieldset>

			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={isGlobal} />
				Make template global (visible from any set)
			</label>

			{#if error}
				<p class="text-sm" role="alert" style="color: var(--color-danger)">{error}</p>
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
					disabled={submitting}
					class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
					style="background-color: var(--color-primary)"
				>
					{submitting ? 'Saving…' : 'Save template'}
				</button>
			</div>
		</form>
	</dialog>
{/if}
