import { describe, it, expect, vi, beforeEach } from 'vitest';
import { sanitizeFilename, extractSvgString } from '../../src/lib/utils/export';

describe('sanitizeFilename', () => {
	it('passes through simple alphanumeric names', () => {
		expect(sanitizeFilename('MyModel')).toBe('MyModel');
	});

	it('allows hyphens, underscores, spaces, and dots', () => {
		expect(sanitizeFilename('my-model_v2.1 final')).toBe('my-model_v2.1 final');
	});

	it('removes special characters', () => {
		expect(sanitizeFilename('model<>:"/\\|?*name')).toBe('modelname');
	});

	it('removes emoji and unicode symbols', () => {
		expect(sanitizeFilename('model\u{1F600}test')).toBe('modeltest');
	});

	it('trims whitespace', () => {
		expect(sanitizeFilename('  model  ')).toBe('model');
	});

	it('returns "export" for empty string', () => {
		expect(sanitizeFilename('')).toBe('export');
	});

	it('returns "export" when all characters are removed', () => {
		expect(sanitizeFilename('***')).toBe('export');
	});

	it('handles strings with only whitespace', () => {
		expect(sanitizeFilename('   ')).toBe('export');
	});
});

describe('extractSvgString', () => {
	beforeEach(() => {
		// Reset DOM
		document.body.innerHTML = '';
	});

	it('extracts SVG from a container with svelte-flow__edges SVG', () => {
		const container = document.createElement('div');
		const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.classList.add('svelte-flow__edges');
		svg.innerHTML = '<rect width="100" height="100" />';
		container.appendChild(svg);

		// Mock getBoundingClientRect
		vi.spyOn(container, 'getBoundingClientRect').mockReturnValue({
			width: 800,
			height: 600,
			x: 0,
			y: 0,
			top: 0,
			right: 800,
			bottom: 600,
			left: 0,
			toJSON: () => ({}),
		});

		const result = extractSvgString(container);
		expect(result).toContain('<svg');
		expect(result).toContain('xmlns="http://www.w3.org/2000/svg"');
		expect(result).toContain('width="800"');
		expect(result).toContain('height="600"');
		expect(result).toContain('<rect');
	});

	it('falls back to any SVG if svelte-flow__edges is not found', () => {
		const container = document.createElement('div');
		const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.innerHTML = '<circle r="50" />';
		container.appendChild(svg);

		vi.spyOn(container, 'getBoundingClientRect').mockReturnValue({
			width: 400,
			height: 300,
			x: 0,
			y: 0,
			top: 0,
			right: 400,
			bottom: 300,
			left: 0,
			toJSON: () => ({}),
		});

		const result = extractSvgString(container);
		expect(result).toContain('<svg');
		expect(result).toContain('width="400"');
		expect(result).toContain('<circle');
	});

	it('throws when no SVG element is present', () => {
		const container = document.createElement('div');
		container.innerHTML = '<div>No SVG here</div>';

		expect(() => extractSvgString(container)).toThrow('No SVG element found in the flow container');
	});

	it('sets xmlns attribute on the cloned SVG', () => {
		const container = document.createElement('div');
		const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		container.appendChild(svg);

		vi.spyOn(container, 'getBoundingClientRect').mockReturnValue({
			width: 200,
			height: 200,
			x: 0,
			y: 0,
			top: 0,
			right: 200,
			bottom: 200,
			left: 0,
			toJSON: () => ({}),
		});

		const result = extractSvgString(container);
		expect(result).toContain('xmlns="http://www.w3.org/2000/svg"');
	});

	it('does not modify the original SVG element', () => {
		const container = document.createElement('div');
		const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		container.appendChild(svg);

		vi.spyOn(container, 'getBoundingClientRect').mockReturnValue({
			width: 500,
			height: 400,
			x: 0,
			y: 0,
			top: 0,
			right: 500,
			bottom: 400,
			left: 0,
			toJSON: () => ({}),
		});

		extractSvgString(container);
		// Original should not have width/height attributes set by our code
		expect(svg.getAttribute('width')).toBeNull();
		expect(svg.getAttribute('height')).toBeNull();
	});
});

describe('viewport element selection', () => {
	it('prefers .svelte-flow__viewport over container', () => {
		const container = document.createElement('div');
		const viewport = document.createElement('div');
		viewport.classList.add('svelte-flow__viewport');
		container.appendChild(viewport);

		const found = container.querySelector('.svelte-flow__viewport');
		expect(found).toBe(viewport);
	});

	it('falls back to container when no viewport exists', () => {
		const container = document.createElement('div');
		const found = container.querySelector('.svelte-flow__viewport');
		expect(found).toBeNull();
	});
});
