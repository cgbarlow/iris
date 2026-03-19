// @ts-nocheck — Svelte component source is read as text; no runtime rendering in these tests.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Tests for NoteNode rendering — EA Rendering Parity (ADR-086).
 *
 * Verifies:
 * 1. Note uses CSS variable --note-bg for background
 * 2. Note background respects theme colours through CSS variables
 */

const NOTE_FILE = resolve(import.meta.dirname, '../../src/lib/canvas/nodes/NoteNode.svelte');
const VISUAL_STYLES_FILE = resolve(import.meta.dirname, '../../src/lib/canvas/utils/visualStyles.ts');

describe('Note CSS variable --note-bg', () => {
	it('NoteNode sets --note-bg CSS variable from visual.bgColor', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		expect(content).toContain('--note-bg');
		// The component should set --note-bg based on the visual bgColor
		expect(content).toMatch(/--note-bg.*bgColor|bgColor.*--note-bg/);
	});

	it('NoteNode corner fold uses --note-bg variable', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		// The ::before pseudo-element for the corner fold should reference --note-bg
		expect(content).toMatch(/::before[\s\S]*?--note-bg/);
	});

	it('NoteNode sets --note-border CSS variable from visual.borderColor', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		expect(content).toContain('--note-border');
		expect(content).toMatch(/--note-border.*borderColor|borderColor.*--note-border/);
	});

	it('NoteNode default background is yellow (#fef9c3)', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		expect(content).toContain('#fef9c3');
	});
});

describe('Note background respects theme colours', () => {
	it('NoteNode imports nodeOverrideStyle for visual styling', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		expect(content).toContain('nodeOverrideStyle');
	});

	it('NoteNode applies visual overrides through style attribute', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		// The component should use nodeOverrideStyle to generate inline styles from visual overrides
		expect(content).toMatch(/style=\{visualStyle\}|style="\{visualStyle\}"/);
	});

	it('nodeOverrideStyle handles bgColor from theme visual overrides', () => {
		const content = readFileSync(VISUAL_STYLES_FILE, 'utf-8');
		expect(content).toContain('background-color');
		expect(content).toContain('bgColor');
	});

	it('NoteNode reads theme rendering config for notation-aware rendering', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		// The note node should import and use getThemeRendering for theme-aware rendering
		expect(content).toContain('getThemeRendering');
	});

	it('NoteNode gets preferredThemeId from Svelte context', () => {
		const content = readFileSync(NOTE_FILE, 'utf-8');
		expect(content).toContain('preferredThemeId');
		expect(content).toContain('getContext');
	});
});
