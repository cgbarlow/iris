import { describe, it, expect, beforeEach } from 'vitest';
import type { Element } from '$lib/types/api';
import type { CanvasNodeData } from '$lib/types/canvas';

describe('Notation-First UX (ADR-081)', () => {
	describe('Default notation helpers', () => {
		beforeEach(() => {
			localStorage.clear();
		});

		it('getDefaultNotation returns "simple" when localStorage is empty', async () => {
			const { getDefaultNotation } = await import('$lib/stores/defaultNotation.svelte');
			expect(getDefaultNotation()).toBe('simple');
		});

		it('setDefaultNotation stores value and getDefaultNotation retrieves it', async () => {
			const { getDefaultNotation, setDefaultNotation } = await import(
				'$lib/stores/defaultNotation.svelte'
			);
			setDefaultNotation('uml');
			expect(getDefaultNotation()).toBe('uml');
			expect(localStorage.getItem('iris-default-notation')).toBe('uml');
		});

		it('setDefaultNotation overwrites previous value', async () => {
			const { getDefaultNotation, setDefaultNotation } = await import(
				'$lib/stores/defaultNotation.svelte'
			);
			setDefaultNotation('archimate');
			setDefaultNotation('c4');
			expect(getDefaultNotation()).toBe('c4');
		});
	});

	describe('Element notation field', () => {
		it('Element interface accepts notation', () => {
			const el: Element = {
				id: 'e1',
				element_type: 'component',
				current_version: 1,
				name: 'Test',
				description: null,
				data: {},
				created_at: '',
				created_by: '',
				updated_at: '',
				is_deleted: false,
				notation: 'uml',
			};
			expect(el.notation).toBe('uml');
		});

		it('Element notation defaults to undefined when omitted', () => {
			const el: Element = {
				id: 'e2',
				element_type: 'component',
				current_version: 1,
				name: 'Test',
				description: null,
				data: {},
				created_at: '',
				created_by: '',
				updated_at: '',
				is_deleted: false,
			};
			expect(el.notation).toBeUndefined();
		});
	});

	describe('CanvasNodeData notation field', () => {
		it('CanvasNodeData accepts notation', () => {
			const data: CanvasNodeData = {
				label: 'Test',
				entityType: 'component',
				notation: 'archimate',
			};
			expect(data.notation).toBe('archimate');
		});
	});

	describe('Notation→type filtering logic', () => {
		// Mirrors the NOTATION_TYPE_FALLBACK from DiagramDialog
		const NOTATION_TYPE_FALLBACK: Record<string, string[]> = {
			simple: ['component', 'sequence', 'deployment', 'process', 'roadmap', 'free_form'],
			uml: ['component', 'sequence', 'class', 'deployment', 'process', 'free_form'],
			archimate: ['component', 'deployment', 'process', 'free_form'],
			c4: ['component', 'deployment', 'free_form'],
		};

		it('simple notation includes component, sequence, deployment, process, roadmap, free_form', () => {
			expect(NOTATION_TYPE_FALLBACK['simple']).toEqual([
				'component',
				'sequence',
				'deployment',
				'process',
				'roadmap',
				'free_form',
			]);
		});

		it('uml notation includes class but not roadmap', () => {
			expect(NOTATION_TYPE_FALLBACK['uml']).toContain('class');
			expect(NOTATION_TYPE_FALLBACK['uml']).not.toContain('roadmap');
		});

		it('archimate notation has 4 types', () => {
			expect(NOTATION_TYPE_FALLBACK['archimate']).toHaveLength(4);
		});

		it('c4 notation has 3 types', () => {
			expect(NOTATION_TYPE_FALLBACK['c4']).toHaveLength(3);
		});
	});
});
