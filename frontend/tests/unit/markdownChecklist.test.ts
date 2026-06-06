/**
 * @vitest-environment jsdom
 *
 * Issue #255 / ADR-239: checklist mode for Markdown & Smart Markdown.
 *
 * Tests the pure helpers in `markdownHelpers.ts`:
 *   - toggleChecklistItem(source, index) — flip/add a GFM task marker on
 *     the Nth (0-based, document order) list item.
 *   - countChecklistItems(source) — count list items, skipping fenced code.
 *   - decorateChecklist(root) — post-render DOM pass turning <li>s into
 *     interactive checkboxes.
 */
import { describe, it, expect } from 'vitest';
import {
	toggleChecklistItem,
	countChecklistItems,
	checklistItemStates,
	decorateChecklist,
	renderMarkdown,
} from '$lib/components/markdownHelpers';

describe('toggleChecklistItem — flipping existing markers', () => {
	it('ticks an unchecked item: - [ ] a → - [x] a', () => {
		expect(toggleChecklistItem('- [ ] a', 0)).toBe('- [x] a');
	});

	it('unticks a checked item: - [x] a → - [ ] a', () => {
		expect(toggleChecklistItem('- [x] a', 0)).toBe('- [ ] a');
	});

	it('recognises uppercase [X]', () => {
		expect(toggleChecklistItem('- [X] a', 0)).toBe('- [ ] a');
	});

	it('targets the correct item by document-order index', () => {
		const src = '- [ ] a\n- [ ] b\n- [ ] c';
		expect(toggleChecklistItem(src, 1)).toBe('- [ ] a\n- [x] b\n- [ ] c');
	});
});

describe('toggleChecklistItem — plain items tick in one tap', () => {
	it('plain item gains a checked marker: - a → - [x] a', () => {
		expect(toggleChecklistItem('- a', 0)).toBe('- [x] a');
	});

	it('preserves the bullet character (* and +)', () => {
		expect(toggleChecklistItem('* a', 0)).toBe('* [x] a');
		expect(toggleChecklistItem('+ a', 0)).toBe('+ [x] a');
	});
});

describe('toggleChecklistItem — ordered lists', () => {
	it('handles 1. style', () => {
		expect(toggleChecklistItem('1. a', 0)).toBe('1. [x] a');
	});

	it('handles 1) style and flips existing markers', () => {
		expect(toggleChecklistItem('1) [ ] a', 0)).toBe('1) [x] a');
	});
});

describe('toggleChecklistItem — nesting & indentation', () => {
	it('toggles the correct nested item by document order and preserves indent', () => {
		const src = '- [ ] a\n  - [ ] a1\n  - [ ] a2\n- [ ] b';
		// document order: 0=a, 1=a1, 2=a2, 3=b
		expect(toggleChecklistItem(src, 2)).toBe('- [ ] a\n  - [ ] a1\n  - [x] a2\n- [ ] b');
	});

	it('preserves tab/space indentation exactly when adding a marker', () => {
		expect(toggleChecklistItem('  - a', 0)).toBe('  - [x] a');
	});
});

describe('toggleChecklistItem — preserves item text', () => {
	it('keeps trailing strikethrough markup the user authored', () => {
		expect(toggleChecklistItem('- [ ] ~~done~~ x', 0)).toBe('- [x] ~~done~~ x');
	});

	it('keeps inline formatting and links', () => {
		const src = '- [ ] see **bold** and [link](https://example.com)';
		expect(toggleChecklistItem(src, 0)).toBe('- [x] see **bold** and [link](https://example.com)');
	});
});

describe('toggleChecklistItem — fenced code blocks are not list items', () => {
	it('skips list-like lines inside ``` fences', () => {
		const src = '- [ ] real\n\n```\n- [ ] fake in code\n```\n\n- [ ] also real';
		// indices: 0=real, 1=also real (the fenced line is skipped)
		expect(toggleChecklistItem(src, 1)).toBe(
			'- [ ] real\n\n```\n- [ ] fake in code\n```\n\n- [x] also real',
		);
	});

	it('does not rewrite a line inside a fence even at its visual position', () => {
		const src = '```\n- [ ] fenced\n```';
		// no real list items → any index is a no-op
		expect(toggleChecklistItem(src, 0)).toBe(src);
	});
});

describe('toggleChecklistItem — multi-line items', () => {
	it('only rewrites the bullet line, not continuation lines', () => {
		const src = '- [ ] first line\n  continuation\n- [ ] second';
		expect(toggleChecklistItem(src, 0)).toBe('- [x] first line\n  continuation\n- [ ] second');
	});
});

describe('toggleChecklistItem — out of range', () => {
	it('returns the source unchanged for an index past the end', () => {
		expect(toggleChecklistItem('- [ ] a', 5)).toBe('- [ ] a');
	});

	it('returns the source unchanged for a negative index', () => {
		expect(toggleChecklistItem('- [ ] a', -1)).toBe('- [ ] a');
	});

	it('returns prose unchanged when there are no list items', () => {
		expect(toggleChecklistItem('# Heading\n\nA paragraph.', 0)).toBe('# Heading\n\nA paragraph.');
	});
});

describe('countChecklistItems', () => {
	it('counts unordered + ordered + nested items', () => {
		const src = '- a\n  - a1\n- b\n\n1. c\n2. d';
		expect(countChecklistItems(src)).toBe(5);
	});

	it('ignores list-like lines inside fenced code', () => {
		const src = '- a\n```\n- not counted\n```\n- b';
		expect(countChecklistItems(src)).toBe(2);
	});

	it('returns 0 for prose', () => {
		expect(countChecklistItems('Just a paragraph.')).toBe(0);
	});
});

describe('decorateChecklist — DOM pass', () => {
	function frag(source: string): HTMLElement {
		const { html } = renderMarkdown(source);
		const el = document.createElement('div');
		el.innerHTML = html;
		return el;
	}
	const decorate = (source: string) => {
		const el = frag(source);
		decorateChecklist(el, checklistItemStates(source));
		return el;
	};

	it('adds an interactive checkbox button with sequential indices to each <li>', () => {
		const el = decorate('- a\n- b\n- c');
		const boxes = el.querySelectorAll('.md-check');
		expect(boxes.length).toBe(3);
		expect([...boxes].map((b) => b.getAttribute('data-checklist-index'))).toEqual(['0', '1', '2']);
		expect(boxes[0].getAttribute('role')).toBe('checkbox');
	});

	it('marks checked items from authored [x] and adds the strike class', () => {
		const el = decorate('- [x] done\n- [ ] todo');
		const items = el.querySelectorAll('li');
		expect(items[0].classList.contains('md-check-checked')).toBe(true);
		expect(items[1].classList.contains('md-check-checked')).toBe(false);
		expect(el.querySelector('.md-check')?.getAttribute('aria-checked')).toBe('true');
	});

	it('leaves no <input> in the decorated output (DOMPurify may strip the type attr)', () => {
		const el = decorate('- [x] done');
		expect(el.querySelector('input')).toBeNull();
		expect(el.querySelector('.md-check')).not.toBeNull();
	});

	it('trims the leading space marked leaves after a task checkbox', () => {
		// marked emits `<input> done`; after stripping the input the text
		// node would start with a space and read as a big gap before the label.
		const el = decorate('- [x] done');
		const li = el.querySelector('li')!;
		// The label text node (after the button) must not start with whitespace.
		const label = [...li.childNodes].find((n) => n.nodeType === 3 && n.textContent?.trim());
		expect(label?.textContent).toBe('done');
	});

	it('indexes nested items in document order matching toggleChecklistItem', () => {
		const el = decorate('- a\n  - a1\n- b');
		expect(el.querySelectorAll('.md-check').length).toBe(3);
	});
});
