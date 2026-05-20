<script lang="ts">
	/**
	 * SmartMarkdownCanvas: edit/view canvas for Smart Markdown diagrams
	 * (ADR-205, issue #185).
	 *
	 * Edit mode: textarea over the user-edited `markdown_source`. Typing
	 * "/" at the start of a line or after whitespace opens the
	 * SmartMarkdownSlashPicker for inserting an inline token of the form
	 * `{{<entity-type>:<id>:<field-spec>}}`.
	 *
	 * View mode: renders the *server-resolved* markdown coming from
	 * `data.content` (the backend resolver, ADR-187 hook, substitutes
	 * tokens for live field values). Resolution is server-side so the
	 * markdown/docx/pdf renderers all see the same resolved content
	 * (Protocol §13 DRY).
	 */
	import MarkdownView from '$lib/components/MarkdownView.svelte';
	import type { TocHeading } from '$lib/components/markdownHelpers';
	import MarkdownEditorToolbar from '$lib/canvas/text/MarkdownEditorToolbar.svelte';
	import { wrapSelection, applyOp, insertAtCursor } from '$lib/canvas/text/markdownEditorToolbarHelpers';
	import SmartMarkdownSlashPicker from '$lib/canvas/text/SmartMarkdownSlashPicker.svelte';
	import ImageInsertDialog from '$lib/components/ImageInsertDialog.svelte';

	interface Props {
		/** Server-resolved markdown (`data.content`). Shown in view mode. */
		content: string;
		/** User-edited markdown source with tokens (`data.markdown_source`). */
		source: string;
		/** Edit-mode toggle controlled by the parent. */
		editing?: boolean;
		/** Set of Text-class diagram IDs for the iris:// link styling pass. */
		textDiagramIds?: Set<string>;
		/** Called whenever the source changes in edit mode. */
		onsourcechange?: (source: string) => void;
		/** Heading list updates — wire to MarkdownToc. */
		onheadings?: (headings: TocHeading[]) => void;
		/** ADR-207: the diagram's set_id. The picker uses it to seed
		 *  its initial breadcrumb at the parent collection (or set if no
		 *  collection) so the user opens at their current location, not
		 *  at the global root. */
		contextSetId?: string | null;
	}

	let {
		content,
		source = $bindable(),
		editing = false,
		textDiagramIds,
		onsourcechange,
		onheadings,
		contextSetId = null,
	}: Props = $props();

	let textareaEl = $state<HTMLTextAreaElement | undefined>(undefined);

	// Picker state. ``pickerCaret`` is the textarea caret index just
	// *after* the "/" that opened the picker — used to splice the
	// token back in.
	let pickerOpen = $state(false);
	let pickerCaret = $state(0);

	// ADR-209: image-insert dialog state (Link vs Upload chooser).
	let imageDialogOpen = $state(false);
	let imageDialogCaret = $state(0);

	function onImageInsert(markdown: string) {
		imageDialogOpen = false;
		if (!textareaEl) return;
		textareaEl.focus();
		textareaEl.setSelectionRange(imageDialogCaret, imageDialogCaret);
		const op = insertAtCursor(textareaEl, markdown);
		applyOp(textareaEl, op);
		commitSource(op.value);
	}

	function openImageDialog() {
		if (textareaEl) imageDialogCaret = textareaEl.selectionStart;
		imageDialogOpen = true;
	}

	function commitSource(value: string) {
		source = value;
		onsourcechange?.(value);
	}

	function onInput(e: Event) {
		commitSource((e.target as HTMLTextAreaElement).value);
	}

	function openPicker(ta: HTMLTextAreaElement) {
		pickerCaret = ta.selectionStart;
		pickerOpen = true;
	}

	function onKeydown(e: KeyboardEvent) {
		const ta = e.currentTarget as HTMLTextAreaElement;

		// "/" trigger: only at line start or after whitespace, to avoid
		// hijacking intra-word slashes (URLs, paths, dates).
		if (e.key === '/') {
			const cursor = ta.selectionStart;
			const prev = cursor === 0 ? '\n' : ta.value[cursor - 1];
			if (cursor === 0 || prev === ' ' || prev === '\n' || prev === '\t') {
				e.preventDefault();
				openPicker(ta);
				return;
			}
		}

		// Ctrl/Cmd+B / +I / +K mirror the toolbar — preserves the
		// markdown source-of-truth pattern from TextCanvas.
		if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
			const k = e.key.toLowerCase();
			if (k === 'b') {
				e.preventDefault();
				const op = wrapSelection(ta, '**', '**');
				applyOp(ta, op);
				commitSource(op.value);
				return;
			}
			if (k === 'i') {
				e.preventDefault();
				const op = wrapSelection(ta, '*', '*');
				applyOp(ta, op);
				commitSource(op.value);
				return;
			}
			if (k === 'k') {
				e.preventDefault();
				const op = wrapSelection(ta, '[', '](url)');
				applyOp(ta, op);
				commitSource(op.value);
				return;
			}
		}
	}

	function onTokenInsert(token: string) {
		pickerOpen = false;
		if (!textareaEl) return;
		// Restore the caret to where it was before the picker opened
		// (browser may have moved focus / scrolled).
		textareaEl.focus();
		textareaEl.setSelectionRange(pickerCaret, pickerCaret);
		const op = insertAtCursor(textareaEl, token);
		applyOp(textareaEl, op);
		commitSource(op.value);
	}

	function onPickerClose() {
		pickerOpen = false;
		textareaEl?.focus();
	}
</script>

<div class="smart-markdown-canvas" data-mode={editing ? 'edit' : 'view'}>
	{#if editing}
		<MarkdownEditorToolbar
			textareaEl={textareaEl}
			onchange={(v) => commitSource(v)}
			onimage={openImageDialog}
		/>
		<textarea
			bind:this={textareaEl}
			class="smart-markdown-canvas__editor"
			value={source ?? ''}
			oninput={onInput}
			onkeydown={onKeydown}
			placeholder="Write markdown. Type ‘/’ to insert a reference to an Iris entity field (e.g. an element name or attribute). Tokens render with live values at view time."
			spellcheck="true"
		></textarea>
		{#if pickerOpen}
			<SmartMarkdownSlashPicker
				oninsert={onTokenInsert}
				onclose={onPickerClose}
				existingSource={source ?? ''}
				contextSetId={contextSetId}
			/>
		{/if}
		<ImageInsertDialog
			open={imageDialogOpen}
			oninsert={onImageInsert}
			oncancel={() => { imageDialogOpen = false; textareaEl?.focus(); }}
		/>
	{:else}
		<div class="smart-markdown-canvas__view">
			<MarkdownView source={content ?? ''} {textDiagramIds} {onheadings} />
		</div>
	{/if}
</div>

<style>
	.smart-markdown-canvas {
		position: relative;
		display: flex; flex-direction: column;
		width: 100%; height: 100%;
		background: var(--color-surface, #ffffff);
	}
	.smart-markdown-canvas__editor {
		flex: 1;
		width: 100%; height: 100%;
		padding: 16px;
		border: 0; resize: none; outline: none;
		background: var(--color-surface, #ffffff);
		color: var(--color-fg, #202931);
		font-family: ui-monospace, monospace;
		font-size: 13px; line-height: 1.55;
	}
	.smart-markdown-canvas__view {
		flex: 1;
		padding: 24px 32px;
		overflow-y: auto;
		font-size: 14px;
		max-width: 920px;
		width: 100%;
		margin: 0 auto;
	}
</style>
