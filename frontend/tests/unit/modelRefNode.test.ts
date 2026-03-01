import { describe, it, expect } from 'vitest';
import { simpleViewNodeTypes } from '../../src/lib/canvas/nodes/index';

describe('ModelRefNode type registration', () => {
	it('registers modelref node type', () => {
		expect(simpleViewNodeTypes).toHaveProperty('modelref');
	});

	it('modelref is distinct from component', () => {
		expect(simpleViewNodeTypes.modelref).not.toBe(simpleViewNodeTypes.component);
	});
});
