import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * KG settings tab split: Visibility → Nodes + Relationships
 * (v6.9.0, ADR-199, issue #173 items 4 + 5).
 *
 * The previous Visibility tab mixed node-type toggles and relationship-type
 * toggles in one column. We split into three tabs:
 *
 *   Nodes  |  Relationships  |  Display
 *
 * Item 5 also adds the new `element_package` edge type, which lands in
 * the Package group under the Relationships tab.
 *
 * Static-parser style to match the rest of this suite.
 */

const src = readFileSync(
	resolve(__dirname, '../../src/lib/components/KnowledgeGraphSettings.svelte'),
	'utf-8',
);

describe('KG settings — tab structure', () => {
	it("widens activeTab to 'nodes' | 'relationships' | 'display'", () => {
		expect(src).toMatch(/\$state<'nodes'\s*\|\s*'relationships'\s*\|\s*'display'>/);
	});

	it("defaults activeTab to 'nodes'", () => {
		expect(src).toMatch(/\$state<'nodes'\s*\|\s*'relationships'\s*\|\s*'display'>\('nodes'\)/);
	});

	it('renders a Nodes tab button', () => {
		expect(src).toMatch(/onclick=\{[^}]*activeTab\s*=\s*'nodes'[^}]*\}[^>]*>[^<]*Nodes/);
	});

	it('renders a Relationships tab button', () => {
		expect(src).toMatch(/onclick=\{[^}]*activeTab\s*=\s*'relationships'[^}]*\}[^>]*>[^<]*Relationships/);
	});

	it('renders a Display tab button', () => {
		expect(src).toMatch(/onclick=\{[^}]*activeTab\s*=\s*'display'[^}]*\}[^>]*>[^<]*Display/);
	});

	it("no longer references the old 'visibility' tab key", () => {
		expect(src).not.toMatch(/activeTab\s*===\s*'visibility'/);
		expect(src).not.toMatch(/'visibility'\s*\|\s*'display'/);
	});
});

describe('KG settings — Nodes tab body', () => {
	it('Node-Types section is gated on activeTab === "nodes"', () => {
		// The section heading or content sits inside an {#if activeTab === 'nodes'} branch.
		expect(src).toMatch(/activeTab\s*===\s*'nodes'[\s\S]*?Node Types/);
	});
});

describe('KG settings — Relationships tab body', () => {
	it('Relationship-Types section is gated on activeTab === "relationships"', () => {
		expect(src).toMatch(/activeTab\s*===\s*'relationships'[\s\S]*?Relationship Types/);
	});

	it('still iterates EDGE_GROUPS in the Relationships branch', () => {
		// Sanity: edge group rendering is preserved, just moved.
		expect(src).toContain('EDGE_GROUPS');
	});
});

describe('KG settings — element ↔ package edge toggle (#173 item 5)', () => {
	it('exposes an element_package toggle key in EDGE_GROUPS', () => {
		expect(src).toMatch(/key:\s*'element_package'/);
	});

	it('places the element_package toggle under the Package group', () => {
		// Slice from the start of the Package group to the start of the
		// next *group-level* label (Diagram). That window contains every
		// `key: 'foo'` entry for the Package group's items.
		const packageGroupStart = src.indexOf("label: 'Package'");
		expect(packageGroupStart, "'Package' group not found").toBeGreaterThan(-1);
		const diagramGroupStart = src.indexOf("label: 'Diagram'", packageGroupStart);
		expect(diagramGroupStart, "'Diagram' group not found").toBeGreaterThan(-1);
		const packageGroupSlice = src.slice(packageGroupStart, diagramGroupStart);
		expect(packageGroupSlice).toMatch(/key:\s*'element_package'/);
	});
});

describe('KG settings — onResetToDefaults prop signature', () => {
	it("widens onResetToDefaults to accept the new 3-tab union", () => {
		expect(src).toMatch(
			/onResetToDefaults\?:\s*\(tab:\s*'nodes'\s*\|\s*'relationships'\s*\|\s*'display'\)\s*=>\s*void/,
		);
	});
});
