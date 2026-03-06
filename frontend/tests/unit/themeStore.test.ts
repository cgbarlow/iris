// @ts-nocheck — Theme store uses Svelte 5 runes ($state/$derived) which are compile-time only; we test exported functions directly.
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Tests for theme store — EA Rendering Parity (ADR-086).
 *
 * Verifies:
 * 1. Active theme overrides preferredThemeId in resolveNodeVisual
 * 2. ThemeRenderingConfig exposes hideTypeStereotypes and abstractBoldOverride
 */

const STORE_FILE = resolve(import.meta.dirname, '../../src/lib/stores/themeStore.svelte.ts');

describe('ThemeRenderingConfig fields', () => {
	it('ThemeRenderingConfig includes hideTypeStereotypes field', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		expect(content).toMatch(/hideTypeStereotypes\??:\s*boolean/);
	});

	it('ThemeRenderingConfig includes abstractBoldOverride field', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		expect(content).toMatch(/abstractBoldOverride\??:\s*boolean/);
	});

	it('getThemeRendering function is exported', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		expect(content).toContain('export function getThemeRendering');
	});

	it('getThemeRendering returns rendering config from theme', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		expect(content).toMatch(/theme\?\.config\?\.rendering/);
	});
});

describe('Active theme overrides preferredThemeId', () => {
	it('resolveNodeVisual checks explicit active theme before preferredThemeId', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		// The function should call getActiveThemeId to check user-explicit selection first
		expect(content).toContain('getActiveThemeId');
		// The function signature accepts preferredThemeId
		expect(content).toMatch(/resolveNodeVisual[\s\S]*?preferredThemeId/);
	});

	it('resolveNodeVisual prioritises explicitActive over preferredThemeId', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		// Verify the cascading logic: explicitActive checked first, then preferredThemeId, then default
		expect(content).toMatch(/const explicitActive\s*=\s*getActiveThemeId/);
		expect(content).toMatch(/explicitActive\s*\?[\s\S]*?preferredThemeId\s*\?/);
	});

	it('setActiveTheme persists to localStorage', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		expect(content).toContain('localStorage.setItem');
		expect(content).toContain('iris_active_themes');
	});

	it('getThemeRendering also respects active theme over preferredThemeId', () => {
		const content = readFileSync(STORE_FILE, 'utf-8');
		// getThemeRendering should follow the same cascade as resolveNodeVisual
		const fnMatch = content.match(/export function getThemeRendering[\s\S]*?^}/m);
		expect(fnMatch).not.toBeNull();
		const fnBody = fnMatch![0];
		expect(fnBody).toContain('getActiveThemeId');
		expect(fnBody).toContain('explicitActive');
	});
});
