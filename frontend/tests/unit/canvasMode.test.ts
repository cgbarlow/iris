import { describe, it, expect } from 'vitest';
import {
	getCanvasMode,
	setCanvasMode,
	isEditMode,
	isBrowseMode,
} from '$lib/stores/canvasMode.svelte';

describe('canvasMode store', () => {
	it('defaults to browse mode', () => {
		expect(getCanvasMode()).toBe('browse');
		expect(isBrowseMode()).toBe(true);
		expect(isEditMode()).toBe(false);
	});

	it('can switch to edit mode', () => {
		setCanvasMode('edit');
		expect(getCanvasMode()).toBe('edit');
		expect(isEditMode()).toBe(true);
		expect(isBrowseMode()).toBe(false);
	});

	it('can switch back to browse mode', () => {
		setCanvasMode('edit');
		setCanvasMode('browse');
		expect(getCanvasMode()).toBe('browse');
		expect(isBrowseMode()).toBe(true);
	});
});
