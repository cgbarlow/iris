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
	import MarkdownView from '$lib/components/MarkdownView.svelte';
	import type { TocHeading } from '$lib/components/markdownHelpers';
	import MarkdownEditorToolbar from '$lib/canvas/text/MarkdownEditorToolbar.svelte';
	import { wrapSelection, applyOp, insertAtCursor, uploadPastedImage } from '$lib/canvas/text/markdownEditorToolbarHelpers';
	import ImageInsertDialog from '$lib/components/ImageInsertDialog.svelte';

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
		/** v5.4.1 (#46 item #4): called when clipboard image paste fails (network, MIME, auth). The parent can surface a toast; the handler also console.errors so dev tools shows the underlying cause. */
		onpasteerror?: (err: unknown) => void;
		/** ADR-239: render list items as tappable checkboxes in view mode. */
		checklist?: boolean;
		/** ADR-239: called with the tapped item's 0-based index. */
		ontoggle?: (index: number) => void;
	}

	let {
		content = $bindable(),
		editing = false,
		textDiagramIds,
		oncontentchange,
		onheadings,
		textareaEl = $bindable(),
		onpasteerror,
		checklist = false,
		ontoggle,
	}: Props = $props();

	function onInput(e: Event) {
		const value = (e.target as HTMLTextAreaElement).value;
		content = value;
		oncontentchange?.(value);
	}

	// ADR-209: image-insert dialog state for the toolbar button.
	let imageDialogOpen = $state(false);
	let imageDialogCaret = $state(0);

	function openImageDialog() {
		if (textareaEl) imageDialogCaret = textareaEl.selectionStart;
		imageDialogOpen = true;
	}

	function onImageInsert(markdown: string) {
		imageDialogOpen = false;
		if (!textareaEl) return;
		textareaEl.focus();
		textareaEl.setSelectionRange(imageDialogCaret, imageDialogCaret);
		const op = insertAtCursor(textareaEl, markdown);
		applyOp(textareaEl, op);
		content = op.value;
		oncontentchange?.(op.value);
	}

	/**
	 * Issue #31: trap Tab inside the textarea so it indents instead of
	 * moving focus. Esc temporarily releases the trap so the next Tab
	 * moves focus normally — preserves WCAG 2.1.2 (No Keyboard Trap).
	 */
	let tabTrapEnabled = $state(true);

	function commitChange(ta: HTMLTextAreaElement) {
		content = ta.value;
		oncontentchange?.(ta.value);
	}

	function handleKeydown(e: KeyboardEvent) {
		const ta = e.currentTarget as HTMLTextAreaElement;

		// Issue #32 reopen: Ctrl/Cmd+B / +I / +K = bold / italic / link.
		// Mirrors the toolbar buttons; keeps source-of-truth markdown.
		if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
			const k = e.key.toLowerCase();
			if (k === 'b') {
				e.preventDefault();
				const op = wrapSelection(ta, '**', '**');
				applyOp(ta, op);
				content = op.value;
				oncontentchange?.(op.value);
				return;
			}
			if (k === 'i') {
				e.preventDefault();
				const op = wrapSelection(ta, '*', '*');
				applyOp(ta, op);
				content = op.value;
				oncontentchange?.(op.value);
				return;
			}
			if (k === 'k') {
				e.preventDefault();
				const op = wrapSelection(ta, '[', '](url)');
				applyOp(ta, op);
				content = op.value;
				oncontentchange?.(op.value);
				return;
			}
		}

		if (e.key === 'Escape') {
			tabTrapEnabled = false;
			return;
		}

		if (e.key !== 'Tab') {
			tabTrapEnabled = true;
			return;
		}

		if (!tabTrapEnabled) {
			tabTrapEnabled = true;
			return;
		}

		e.preventDefault();
		const start = ta.selectionStart;
		const end = ta.selectionEnd;
		const value = ta.value;

		if (e.shiftKey) {
			const lineStart = value.lastIndexOf('\n', start - 1) + 1;
			if (value[lineStart] === '\t') {
				ta.value = value.slice(0, lineStart) + value.slice(lineStart + 1);
				const offset = start === lineStart ? 0 : 1;
				ta.setSelectionRange(start - offset, end - 1);
			} else {
				const spaces = value.slice(lineStart).match(/^ {1,4}/)?.[0].length ?? 0;
				if (spaces === 0) return;
				ta.value = value.slice(0, lineStart) + value.slice(lineStart + spaces);
				ta.setSelectionRange(Math.max(start - spaces, lineStart), end - spaces);
			}
		} else {
			ta.value = value.slice(0, start) + '\t' + value.slice(end);
			ta.setSelectionRange(start + 1, start + 1);
		}
		commitChange(ta);
	}

	/** v5.4.0 (#7): paste an image from the clipboard → upload to Iris →
	 *  splice `![pasted-image](/api/images/<id>)` at the cursor. The user
	 *  experience is GitHub-style. Falls through to the browser default
	 *  for non-image clipboard content (text, etc). */
	async function handlePaste(e: ClipboardEvent) {
		const items = e.clipboardData?.items;
		if (!items) return;
		for (const item of items) {
			if (item.kind === 'file' && item.type.startsWith('image/')) {
				e.preventDefault();
				const file = item.getAsFile();
				if (!file) return;
				const ta = e.currentTarget as HTMLTextAreaElement;
				try {
					const uploaded = await uploadPastedImage(file);
					const op = insertAtCursor(ta, `![pasted-image](${uploaded.url})`);
					applyOp(ta, op);
					content = op.value;
					oncontentchange?.(op.value);
				} catch (err) {
					// v5.4.1 (#46 item #4): surface the failure so users can
					// see *something* in dev tools when paste silently no-ops
					// (auth, network, MIME rejection). Pre-fix the catch was
					// empty and the user couldn't tell upload had failed.
					console.error('Image paste failed:', err);
					onpasteerror?.(err);
				}
				return;
			}
		}
	}
</script>

<div class="text-canvas" data-mode={editing ? 'edit' : 'view'}>
	{#if editing}
		<MarkdownEditorToolbar
			textareaEl={textareaEl}
			onchange={(v) => { content = v; oncontentchange?.(v); }}
			onimage={openImageDialog}
		/>
		<textarea
			bind:this={textareaEl}
			class="text-canvas__editor"
			value={content ?? ''}
			oninput={onInput}
			onkeydown={handleKeydown}
			onpaste={handlePaste}
			placeholder="Write markdown… use [label](iris://diagram/<id>) or iris://element/<id> to link to other Iris models. Tab indents; Esc then Tab moves focus. Paste an image to upload it inline."
			spellcheck="true"
		></textarea>
		<ImageInsertDialog
			open={imageDialogOpen}
			oninsert={onImageInsert}
			oncancel={() => { imageDialogOpen = false; textareaEl?.focus(); }}
		/>
	{:else}
		<div class="text-canvas__view">
			<MarkdownView source={content ?? ''} {textDiagramIds} {onheadings} {checklist} {ontoggle} />
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
