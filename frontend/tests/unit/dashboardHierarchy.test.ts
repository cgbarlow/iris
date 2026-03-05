import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Dashboard Hierarchy Tree tests (ADR-076).
 * Verifies that the dashboard page reuses the TreeNode component
 * to display a diagram hierarchy when a set is selected.
 */

const dashboardSrc = readFileSync(
	resolve(__dirname, '../../src/routes/+page.svelte'),
	'utf-8',
);

describe('Dashboard hierarchy tree — imports', () => {
	it('imports TreeNode component', () => {
		expect(dashboardSrc).toContain("TreeNode");
		expect(dashboardSrc).toContain("$lib/components/TreeNode.svelte");
	});

	it('imports DiagramHierarchyNode type', () => {
		expect(dashboardSrc).toContain('DiagramHierarchyNode');
	});
});

describe('Dashboard hierarchy tree — API call', () => {
	it('calls /api/diagrams/hierarchy endpoint', () => {
		expect(dashboardSrc).toContain('/api/diagrams/hierarchy');
	});

	it('passes set_id query parameter to hierarchy endpoint', () => {
		expect(dashboardSrc).toContain('set_id=');
		expect(dashboardSrc).toContain('hierarchy');
	});
});

describe('Dashboard hierarchy tree — template', () => {
	it('renders a tree with role="tree"', () => {
		expect(dashboardSrc).toContain('role="tree"');
	});

	it('has a tree search input', () => {
		expect(dashboardSrc).toContain('id="tree-search"');
	});

	it('hierarchy section is conditional on activeSet', () => {
		expect(dashboardSrc).toContain('{#if activeSet}');
	});

	it('renders TreeNode components for each hierarchy node', () => {
		expect(dashboardSrc).toContain('<TreeNode');
		expect(dashboardSrc).toContain('hierarchyTree');
	});
});

describe('Dashboard hierarchy tree — TreeNode props', () => {
	it('passes searchQuery prop to TreeNode', () => {
		expect(dashboardSrc).toContain('searchQuery={treeSearchQuery}');
	});

	it('passes expandedIds prop to TreeNode', () => {
		expect(dashboardSrc).toContain('expandedIds={treeExpandedIds}');
	});
});
