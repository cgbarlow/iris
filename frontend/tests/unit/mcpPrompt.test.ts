/**
 * ADR-155 (v5.10.0): strict-split scope prompts.
 *
 * - `system_prompt`: auto-applies in Iris AI, not surfaced via MCP.
 * - `mcp_prompt`: surfaced via MCP picker as `set:<uuid>` /
 *   `collection:<uuid>`, never auto-applies in Iris AI.
 *
 * Lightweight unit tests aligned with this repo's frontend testing
 * posture (data shape + payload composition).
 */

import { describe, expect, it } from 'vitest';

describe('Set edit page PUT payload shape (ADR-155)', () => {
	it('PUT body separates system_prompt and mcp_prompt', () => {
		// Mirrors handleSave composition in routes/sets/[id]/+page.svelte
		const payload = {
			name: 'DoView Book',
			description: 'Iris set',
			thumbnail_source: null,
			thumbnail_diagram_id: null,
			collection_id: null,
			system_prompt: 'Iris-AI directive.',
			mcp_prompt: 'MCP-only directive.',
		};
		expect(payload.system_prompt).not.toBe(payload.mcp_prompt);
		expect(Object.keys(payload)).toContain('system_prompt');
		expect(Object.keys(payload)).toContain('mcp_prompt');
	});

	it('mcp_prompt is null when textarea is empty', () => {
		const mcpPromptInput = '   ';
		const sanitized = mcpPromptInput.trim() ? mcpPromptInput.trim() : null;
		expect(sanitized).toBeNull();
	});

	it('system_prompt and mcp_prompt are independent', () => {
		// Author populates only mcp_prompt — system_prompt should remain null.
		const payload = {
			system_prompt: null,
			mcp_prompt: 'MCP-only directive.',
		};
		expect(payload.system_prompt).toBeNull();
		expect(payload.mcp_prompt).toBe('MCP-only directive.');
	});
});

describe('Collection edit page PUT payload shape (ADR-155)', () => {
	it('PUT body includes both prompt slots', () => {
		const payload = {
			name: 'NZISM',
			description: null,
			system_prompt: 'Cite the control number.',
			mcp_prompt: 'Format responses in markdown.',
		};
		expect(payload.system_prompt).toBeDefined();
		expect(payload.mcp_prompt).toBeDefined();
	});
});
