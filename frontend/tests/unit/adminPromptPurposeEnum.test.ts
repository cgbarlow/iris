/**
 * v5.18.0 (ADR-163, SPEC-163-A) — `PURPOSES` enum extended with
 * `mcp_server_instructions` and `appliesToLabel` shows "Server-wide
 * (MCP instructions)" for the new purpose.
 *
 * Inline copies of helpers; keep in sync with
 * `frontend/src/routes/admin/settings/ai/+page.svelte`.
 */
import { describe, it, expect } from 'vitest';

const PURPOSES = ['creation_format', 'response_format', 'mcp_server_instructions'] as const;

function appliesToLabel(p: { purpose?: string; layer: string; notation: string | null; diagram_type: string | null }): string {
	if (p.purpose === 'mcp_server_instructions') return 'Server-wide (MCP instructions)';
	const n = p.notation || null;
	const d = p.diagram_type || null;
	if (p.layer === 'base') return 'Any notation × Any diagram type';
	if (p.layer === 'override') return n ? `Override: ${n} (replaces all layers)` : 'Override (no notation set — invalid)';
	if (p.layer === 'notation') return n ? `${n} × any diagram type` : 'Notation layer (no notation set — invalid)';
	const notationPart = n ?? 'Any notation';
	const dtPart = d ?? '?';
	return `${notationPart} × ${dtPart} diagrams`;
}

describe('PURPOSES enum', () => {
	it('contains creation_format, response_format, mcp_server_instructions', () => {
		expect(PURPOSES).toContain('creation_format');
		expect(PURPOSES).toContain('response_format');
		expect(PURPOSES).toContain('mcp_server_instructions');
	});

	it('has exactly 3 values (v5.18.0)', () => {
		expect(PURPOSES.length).toBe(3);
	});
});

describe('appliesToLabel — mcp_server_instructions branch', () => {
	it('returns "Server-wide (MCP instructions)" for the new purpose', () => {
		expect(
			appliesToLabel({
				purpose: 'mcp_server_instructions',
				layer: 'base',
				notation: null,
				diagram_type: null,
			}),
		).toBe('Server-wide (MCP instructions)');
	});

	it('wins over the layer=base default label', () => {
		// Without the purpose branch, this would return
		// "Any notation × Any diagram type". The new branch must short-circuit.
		const label = appliesToLabel({
			purpose: 'mcp_server_instructions',
			layer: 'base',
			notation: null,
			diagram_type: null,
		});
		expect(label).not.toBe('Any notation × Any diagram type');
	});

	it('does not affect creation_format rows', () => {
		expect(
			appliesToLabel({
				purpose: 'creation_format',
				layer: 'notation',
				notation: 'doview',
				diagram_type: null,
			}),
		).toBe('doview × any diagram type');
	});

	it('does not affect response_format rows', () => {
		expect(
			appliesToLabel({
				purpose: 'response_format',
				layer: 'diagram_type',
				notation: 'markdown',
				diagram_type: 'doview_analysis',
			}),
		).toBe('markdown × doview_analysis diagrams');
	});

	it('omitting purpose still works for legacy rows', () => {
		// Pre-v5.18.0 rows might be rendered without `purpose` — the
		// helper must not crash and must fall through to layer logic.
		expect(
			appliesToLabel({
				layer: 'base',
				notation: null,
				diagram_type: null,
			}),
		).toBe('Any notation × Any diagram type');
	});
});
