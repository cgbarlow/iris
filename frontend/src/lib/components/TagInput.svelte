<script lang="ts">
	/** Reusable tag input with add/remove pills, autocomplete suggestions, and optional inherited tags display. */
	import DOMPurify from 'dompurify';

	interface Props {
		tags: string[];
		onaddtag: (tag: string) => void;
		onremovetag: (tag: string) => void;
		inheritedTags?: string[];
		readonly?: boolean;
		suggestions?: string[];
	}

	let { tags, onaddtag, onremovetag, inheritedTags = [], readonly = false, suggestions = [] }: Props = $props();

	let inputValue = $state('');
	let showSuggestions = $state(false);
	let selectedIndex = $state(-1);

	const filteredSuggestions = $derived(
		inputValue.trim().length > 0
			? suggestions
					.filter(
						(s) =>
							s.toLowerCase().includes(inputValue.trim().toLowerCase()) &&
							!tags.includes(s) &&
							!inheritedTags.includes(s),
					)
					.slice(0, 8)
			: [],
	);

	function handleAdd() {
		const sanitized = DOMPurify.sanitize(inputValue.trim());
		if (!sanitized || sanitized.length > 50) return;
		if (tags.includes(sanitized) || inheritedTags.includes(sanitized)) return;
		onaddtag(sanitized);
		inputValue = '';
		showSuggestions = false;
		selectedIndex = -1;
	}

	function selectSuggestion(tag: string) {
		inputValue = tag;
		handleAdd();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			if (selectedIndex >= 0 && selectedIndex < filteredSuggestions.length) {
				selectSuggestion(filteredSuggestions[selectedIndex]);
			} else {
				handleAdd();
			}
		} else if (event.key === 'Escape') {
			showSuggestions = false;
			selectedIndex = -1;
		} else if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (filteredSuggestions.length > 0) {
				showSuggestions = true;
				selectedIndex = Math.min(selectedIndex + 1, filteredSuggestions.length - 1);
			}
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, -1);
		}
	}

	function handleInput() {
		showSuggestions = filteredSuggestions.length > 0;
		selectedIndex = -1;
	}

	function handleBlur() {
		// Delay to allow click on suggestion
		setTimeout(() => {
			showSuggestions = false;
			selectedIndex = -1;
		}, 150);
	}
</script>

<div class="tag-input" aria-label="Tags">
	<div class="tag-input__pills">
		{#each tags as tag}
			<span class="tag-input__pill">
				<span class="tag-input__pill-text">{tag}</span>
				{#if !readonly}
					<button
						class="tag-input__pill-remove"
						onclick={() => onremovetag(tag)}
						aria-label="Remove tag {tag}"
					>
						&times;
					</button>
				{/if}
			</span>
		{/each}

		{#each inheritedTags as tag}
			<span class="tag-input__pill tag-input__pill--inherited" title="Inherited tag">
				<span class="tag-input__pill-text">{tag}</span>
			</span>
		{/each}
	</div>

	{#if !readonly}
		<div class="tag-input__controls">
			<div class="tag-input__input-wrapper">
				<input
					type="text"
					bind:value={inputValue}
					placeholder="Add tag..."
					maxlength={50}
					class="tag-input__field"
					onkeydown={handleKeydown}
					oninput={handleInput}
					onblur={handleBlur}
					onfocus={() => { if (filteredSuggestions.length > 0) showSuggestions = true; }}
					aria-label="New tag"
					role="combobox"
					aria-expanded={showSuggestions}
					aria-autocomplete="list"
					aria-controls="tag-suggestions"
				/>
				{#if showSuggestions && filteredSuggestions.length > 0}
					<ul
						id="tag-suggestions"
						class="tag-input__suggestions"
						role="listbox"
						aria-label="Tag suggestions"
					>
						{#each filteredSuggestions as suggestion, i}
							<li
								role="option"
								aria-selected={i === selectedIndex}
								class="tag-input__suggestion"
								class:tag-input__suggestion--selected={i === selectedIndex}
								onmousedown={() => selectSuggestion(suggestion)}
							>
								{suggestion}
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			<button
				class="tag-input__add"
				onclick={handleAdd}
				disabled={!inputValue.trim()}
				aria-label="Add tag"
			>
				Add
			</button>
		</div>
	{/if}
</div>

<style>
	.tag-input {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.tag-input__pills {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}

	.tag-input__pill {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
		font-size: 0.75rem;
		background-color: var(--color-primary);
		color: white;
	}

	.tag-input__pill--inherited {
		opacity: 0.5;
		background-color: var(--color-muted);
	}

	.tag-input__pill-remove {
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: 0 0.125rem;
		font-size: 0.875rem;
		line-height: 1;
	}

	.tag-input__controls {
		display: flex;
		gap: 0.25rem;
	}

	.tag-input__input-wrapper {
		flex: 1;
		position: relative;
	}

	.tag-input__field {
		width: 100%;
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: 0.25rem;
		font-size: 0.75rem;
		background: var(--color-bg);
		color: var(--color-fg);
	}

	.tag-input__suggestions {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		z-index: 50;
		list-style: none;
		margin: 2px 0 0;
		padding: 0;
		border: 1px solid var(--color-border);
		border-radius: 0.25rem;
		background: var(--color-bg);
		max-height: 160px;
		overflow-y: auto;
	}

	.tag-input__suggestion {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		cursor: pointer;
		color: var(--color-fg);
	}

	.tag-input__suggestion:hover,
	.tag-input__suggestion--selected {
		background: var(--color-surface);
		color: var(--color-primary);
	}

	.tag-input__add {
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--color-primary);
		border-radius: 0.25rem;
		background: var(--color-primary);
		color: white;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.tag-input__add:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
