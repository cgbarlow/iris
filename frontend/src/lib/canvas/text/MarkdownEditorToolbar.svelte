<script lang="ts">
	/**
	 * v5.3.0 (issue #32 reopen): markdown formatting toolbar that sits
	 * above the existing TextCanvas <textarea>. Reuses the v5.1.1
	 * `textareaEl` $bindable from TextCanvas — no new ref plumbing.
	 *
	 * Each button calls a pure helper from
	 * `markdownEditorToolbarHelpers.ts` and applies the result back to
	 * the textarea, then forwards through `onchange` so the page-level
	 * `canvasDirty` wiring fires automatically.
	 *
	 * Markdown stays the canonical source — no hidden state, no WYSIWYG.
	 * Matches the most-loved pattern across StackEdit / GitHub / HackMD /
	 * Obsidian source mode.
	 */
	import {
		wrapSelection,
		prefixLines,
		insertAtCursor,
		applyOp,
	} from './markdownEditorToolbarHelpers';

	interface Props {
		/** Bound from TextCanvas (the v5.1.1 textareaEl). */
		textareaEl: HTMLTextAreaElement | undefined;
		/** Fired with the new textarea value after each toolbar action so
		 *  the parent's existing oncontentchange wiring flips canvasDirty. */
		onchange?: (value: string) => void;
	}

	let { textareaEl, onchange }: Props = $props();

	function fire(op: ReturnType<typeof wrapSelection>) {
		if (!textareaEl) return;
		applyOp(textareaEl, op);
		onchange?.(op.value);
	}

	function bold()      { if (textareaEl) fire(wrapSelection(textareaEl, '**', '**')); }
	function italic()    { if (textareaEl) fire(wrapSelection(textareaEl, '*', '*')); }
	function inlineCode(){ if (textareaEl) fire(wrapSelection(textareaEl, '`', '`')); }
	function link()      { if (textareaEl) fire(wrapSelection(textareaEl, '[', '](url)')); }

	function h1()   { if (textareaEl) fire(prefixLines(textareaEl, '# ')); }
	function h2()   { if (textareaEl) fire(prefixLines(textareaEl, '## ')); }
	function h3()   { if (textareaEl) fire(prefixLines(textareaEl, '### ')); }
	function ul()   { if (textareaEl) fire(prefixLines(textareaEl, '- ')); }
	function ol()   { if (textareaEl) fire(prefixLines(textareaEl, '1. ')); }
	function quote(){ if (textareaEl) fire(prefixLines(textareaEl, '> ')); }

	function image(){ if (textareaEl) fire(insertAtCursor(textareaEl, '![alt](path)')); }
	function hr()   { if (textareaEl) fire(insertAtCursor(textareaEl, '\n---\n')); }
</script>

<!-- Buttons keep their tooltips short; aria-labels are descriptive. -->
<div class="md-toolbar" role="toolbar" aria-label="Markdown formatting">
	<button type="button" onclick={bold} aria-label="Bold (Ctrl+B)" title="Bold (Ctrl/Cmd+B)"><strong>B</strong></button>
	<button type="button" onclick={italic} aria-label="Italic (Ctrl+I)" title="Italic (Ctrl/Cmd+I)"><em>I</em></button>
	<span class="md-toolbar__sep" aria-hidden="true"></span>
	<button type="button" onclick={h1} aria-label="Heading 1" title="Heading 1">H1</button>
	<button type="button" onclick={h2} aria-label="Heading 2" title="Heading 2">H2</button>
	<button type="button" onclick={h3} aria-label="Heading 3" title="Heading 3">H3</button>
	<span class="md-toolbar__sep" aria-hidden="true"></span>
	<button type="button" onclick={ul} aria-label="Bulleted list" title="Bulleted list">•</button>
	<button type="button" onclick={ol} aria-label="Numbered list" title="Numbered list">1.</button>
	<button type="button" onclick={quote} aria-label="Blockquote" title="Blockquote">❝</button>
	<button type="button" onclick={inlineCode} aria-label="Inline code" title="Inline code">{'</>'}</button>
	<span class="md-toolbar__sep" aria-hidden="true"></span>
	<button type="button" onclick={link} aria-label="Link (Ctrl+K)" title="Link (Ctrl/Cmd+K)">🔗</button>
	<button type="button" onclick={image} aria-label="Image" title="Image">🖼</button>
	<button type="button" onclick={hr} aria-label="Horizontal rule" title="Horizontal rule">─</button>
</div>

<style>
	.md-toolbar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		border-bottom: 1px solid var(--color-border, #d4d4d4);
		background: var(--color-surface, #ffffff);
		flex-shrink: 0;
	}
	.md-toolbar button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 28px;
		height: 28px;
		padding: 0 6px;
		font-size: 13px;
		line-height: 1;
		color: var(--color-fg, #202931);
		background: transparent;
		border: 1px solid transparent;
		border-radius: 4px;
		cursor: pointer;
	}
	.md-toolbar button:hover {
		background: var(--color-bg, #f3f4f6);
		border-color: var(--color-border, #d4d4d4);
	}
	.md-toolbar button:focus-visible {
		outline: 2px solid var(--color-primary, #2563eb);
		outline-offset: 1px;
	}
	.md-toolbar__sep {
		display: inline-block;
		width: 1px;
		height: 18px;
		background: var(--color-border, #d4d4d4);
		margin: 0 4px;
	}
</style>
