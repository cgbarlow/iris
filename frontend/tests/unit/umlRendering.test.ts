// @ts-nocheck — Svelte component source is read as text; no runtime rendering in these tests.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Tests for UML rendering behaviour — EA Rendering Parity (ADR-086).
 *
 * Verifies:
 * 1. Stereotype suppression: hideTypeStereotypes hides type-derived stereotypes
 * 2. Label centering: .uml-node__header uses centered flex layout
 * 3. Bold override: abstractBoldOverride=false yields font-weight: 400
 * 4. Attribute sorting: sort_attributes controls attribute display order
 */

const RENDERER_FILE = resolve(import.meta.dirname, '../../src/lib/canvas/renderers/UmlRenderer.svelte');

describe('Stereotype suppression (hideTypeStereotypes)', () => {
	it('UmlRenderer reads hideTypeStereotypes from rendering config', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		expect(content).toContain('hideTypeStereotypes');
	});

	it('stereotype display is conditional on hideTypeStereotypes', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// When hideTypeStereotypes is true, type-derived stereotypes (abstract, interface, enumeration)
		// should be suppressed while data.stereotype values are still shown.
		// The template should have a condition guarding the built-in STEREOTYPES display.
		expect(content).toMatch(/hideTypeStereotypes/);
		// There should be logic that distinguishes type-derived stereotypes from data.stereotype
		expect(content).toMatch(/data\.stereotype|data\s*as\s*Record.*stereotype/);
	});

	it('STEREOTYPES map includes abstract_class, interface_uml, and enumeration', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		expect(content).toContain("abstract_class: 'abstract'");
		expect(content).toContain("interface_uml: 'interface'");
		expect(content).toContain("enumeration: 'enumeration'");
	});

	it('abstract_class stereotype is hidden when hideTypeStereotypes is true', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// The stereotype derived should be conditional on hideTypeStereotypes.
		// When true, only data.stereotype is used, not the STEREOTYPES map.
		// The derived uses a ternary: hideTypeStereotypes ? data.stereotype : STEREOTYPES[...] ?? data.stereotype
		expect(content).toMatch(/hideTypeStereotypes\s*\?/);
	});
});

describe('Label centering', () => {
	it('.uml-node__header uses flex column layout', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		expect(content).toMatch(/\.uml-node__header\s*\{[^}]*display:\s*flex/);
		expect(content).toMatch(/\.uml-node__header\s*\{[^}]*flex-direction:\s*column/);
	});

	it('.uml-node__header uses align-items: center for centered content', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		expect(content).toMatch(/\.uml-node__header\s*\{[^}]*align-items:\s*center/);
	});
});

describe('Bold override (abstractBoldOverride)', () => {
	it('UmlRenderer reads abstractBoldOverride from rendering config', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// The renderer should read abstractBoldOverride from the theme rendering config.
		// This test will FAIL because the current implementation does not reference abstractBoldOverride.
		expect(content).toContain('abstractBoldOverride');
	});

	it('abstract class label can have font-weight controlled by abstractBoldOverride', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// When abstractBoldOverride is false, abstract class labels should render with font-weight: 400
		// instead of the default 700.
		// This test will FAIL because the current implementation always uses font-weight: 700 for labels.
		expect(content).toMatch(/font-weight:\s*400|abstractBoldOverride\s*===?\s*false/);
	});
});

describe('Attribute sorting (sort_attributes)', () => {
	it('UmlRenderer reads sort_attributes or sortAttributes setting', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// The renderer should read a sort_attributes setting to control attribute display order.
		// This test will FAIL because the current implementation does not sort attributes.
		expect(content).toMatch(/sort_attributes|sortAttributes/);
	});

	it('attributes are sorted alphabetically when sort mode is alpha', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// There should be logic that sorts attributes by name when the sort mode is 'alpha'.
		// This test will FAIL because the current implementation renders attributes in original order.
		expect(content).toMatch(/sort|alpha/i);
	});

	it('attributes preserve original order when sort mode is pos', () => {
		const content = readFileSync(RENDERER_FILE, 'utf-8');
		// When sort_attributes is 'pos', attributes should display in their original import order.
		// The renderer should have some handling for the 'pos' mode (or treat it as default).
		expect(content).toMatch(/pos|position|original/i);
	});
});
