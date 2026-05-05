<script lang="ts">
	/**
	 * TextCanvas: edit/view canvas for Text-class diagrams (ADR-137).
	 *
	 * Replaces UnifiedCanvas / SequenceDiagram when a diagram has
	 * notation === 'markdown'. View mode renders MarkdownView; edit
	 * mode shows the markdown source in a textarea; save calls the
	 * existing diagram update endpoint with `data.content` patched.
	 *
	 * The TOC drawer is passed in by the parent page (the diagram detail
	 * page already has the right layout for a 300px right drawer matching
	 * CommentsPanel — TextCanvas just emits the heading list).
	 */
	import MarkdownView, { type TocHeading } from '$lib/components/MarkdownView.svelte';

	interface Props {
		/** Markdown source — read from diagram.data.content. */
		content: string;
		/** Edit-mode toggle controlled by the parent. */
		editing?: boolean;
		/** Set of diagram IDs that are themselves Text — passed to MarkdownView for muted styling of iris://diagram/<id> links. */
		textDiagramIds?: Set<string>;
		/** Called whenever the markdown source changes in edit mode. */
		oncontentchange?: (content: string) => void;
		/** Called whenever the heading list updates — wire to MarkdownToc. */
		onheadings?: (headings: TocHeading[]) => void;
		/** Two-way binding to the underlying textarea so the parent can insert markdown links at the cursor. */
		textareaEl?: HTMLTextAreaElement;
	}

	let {
		content = $bindable(),
		editing = false,
		textDiagramIds,
		oncontentchange,
		onheadings,
		textareaEl = $bindable(),
	}: Props = $props();

	function onInput(e: Event) {
		const value = (e.target as HTMLTextAreaElement).value;
		content = value;
		oncontentchange?.(value);
	}
</script>

<div class="text-canvas" data-mode={editing ? 'edit' : 'view'}>
	{#if editing}
		<textarea
			bind:this={textareaEl}
			class="text-canvas__editor"
			value={content ?? ''}
			oninput={onInput}
			placeholder="Write markdown… use [label](iris://diagram/<id>) or iris://element/<id> to link to other Iris models."
			spellcheck="true"
		></textarea>
	{:else}
		<div class="text-canvas__view">
			<MarkdownView source={content ?? ''} {textDiagramIds} {onheadings} />
		</div>
	{/if}
</div>

<style>
	.text-canvas {
		display: flex; flex-direction: column;
		width: 100%; height: 100%;
		background: var(--color-surface, #ffffff);
	}
	.text-canvas__editor {
		flex: 1;
		width: 100%; height: 100%;
		padding: 16px;
		border: 0; resize: none; outline: none;
		background: var(--color-surface, #ffffff);
		color: var(--color-fg, #202931);
		font-family: ui-monospace, monospace;
		font-size: 13px; line-height: 1.55;
	}
	.text-canvas__view {
		flex: 1;
		padding: 24px 32px;
		overflow-y: auto;
		font-size: 14px;
		max-width: 920px;
		width: 100%;
		margin: 0 auto;
	}
</style>
