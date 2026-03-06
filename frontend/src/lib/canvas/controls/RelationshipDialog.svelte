<script lang="ts">
	/** Dialog for configuring a relationship between two entities (ADR-086: UML extras). */
	import {
		SIMPLE_RELATIONSHIP_TYPES,
		UML_RELATIONSHIP_TYPES,
		ARCHIMATE_RELATIONSHIP_TYPES,
		C4_RELATIONSHIP_TYPES,
		type SimpleRelationshipType,
		type NotationType,
	} from '$lib/types/canvas';

	interface EdgeExtras {
		sourceCardinality?: string;
		targetCardinality?: string;
		sourceRole?: string;
		targetRole?: string;
		stereotype?: string;
	}

	interface Props {
		open: boolean;
		sourceName: string;
		targetName: string;
		notation?: NotationType;
		onsave: (type: SimpleRelationshipType, label: string, extras?: EdgeExtras) => void;
		oncancel: () => void;
	}

	let { open, sourceName, targetName, notation, onsave, oncancel }: Props = $props();

	let relationshipType = $state<SimpleRelationshipType>('uses');
	let label = $state('');
	let sourceCardinality = $state('');
	let targetCardinality = $state('');
	let sourceRole = $state('');
	let targetRole = $state('');
	let stereotype = $state('');
	let dialogEl: HTMLDialogElement | undefined = $state();

	const isUml = $derived(notation === 'uml');

	const relationshipTypeOptions = $derived.by(() => {
		if (notation === 'uml') return UML_RELATIONSHIP_TYPES;
		if (notation === 'archimate') return ARCHIMATE_RELATIONSHIP_TYPES;
		if (notation === 'c4') return C4_RELATIONSHIP_TYPES;
		return SIMPLE_RELATIONSHIP_TYPES;
	});

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			const types = relationshipTypeOptions;
			relationshipType = (types[0]?.key ?? 'uses') as SimpleRelationshipType;
			label = '';
			sourceCardinality = '';
			targetCardinality = '';
			sourceRole = '';
			targetRole = '';
			stereotype = '';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const extras: EdgeExtras = {};
		if (sourceCardinality.trim()) extras.sourceCardinality = sourceCardinality.trim();
		if (targetCardinality.trim()) extras.targetCardinality = targetCardinality.trim();
		if (sourceRole.trim()) extras.sourceRole = sourceRole.trim();
		if (targetRole.trim()) extras.targetRole = targetRole.trim();
		if (stereotype.trim()) extras.stereotype = stereotype.trim();
		onsave(relationshipType, label.trim(), Object.keys(extras).length > 0 ? extras : undefined);
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
		aria-labelledby="relationship-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="relationship-dialog-title" class="text-lg font-bold">Create Relationship</h2>

		<p class="mt-2 text-sm" style="color: var(--color-muted)">
			From <strong>{sourceName}</strong> to <strong>{targetName}</strong>
		</p>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="relationship-type" class="block text-sm font-medium">Type</label>
				<select
					id="relationship-type"
					bind:value={relationshipType}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each relationshipTypeOptions as t}
						<option value={t.key}>{t.label} — {t.description}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="relationship-label" class="block text-sm font-medium">Label (optional)</label>
				<input
					id="relationship-label"
					bind:value={label}
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			{#if isUml}
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="rel-source-card" class="block text-xs font-medium">Source Cardinality</label>
						<input
							id="rel-source-card"
							bind:value={sourceCardinality}
							autocomplete="off"
							placeholder="e.g. 0..*"
							class="mt-1 w-full rounded border px-2 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</div>
					<div>
						<label for="rel-target-card" class="block text-xs font-medium">Target Cardinality</label>
						<input
							id="rel-target-card"
							bind:value={targetCardinality}
							autocomplete="off"
							placeholder="e.g. 1"
							class="mt-1 w-full rounded border px-2 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</div>
					<div>
						<label for="rel-source-role" class="block text-xs font-medium">Source Role</label>
						<input
							id="rel-source-role"
							bind:value={sourceRole}
							autocomplete="off"
							placeholder="e.g. +owner"
							class="mt-1 w-full rounded border px-2 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</div>
					<div>
						<label for="rel-target-role" class="block text-xs font-medium">Target Role</label>
						<input
							id="rel-target-role"
							bind:value={targetRole}
							autocomplete="off"
							placeholder="e.g. +items"
							class="mt-1 w-full rounded border px-2 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</div>
				</div>
				<div>
					<label for="rel-stereotype" class="block text-xs font-medium">Stereotype (optional)</label>
					<input
						id="rel-stereotype"
						bind:value={stereotype}
						autocomplete="off"
						placeholder="e.g. create"
						class="mt-1 w-full rounded border px-2 py-1.5 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
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
					Create
				</button>
			</div>
		</form>
	</dialog>
{/if}
