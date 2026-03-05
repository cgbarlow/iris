import { describe, it, expect } from 'vitest';
import type {
	DiagramTypeRegistry,
	NotationMapping,
	NotationRegistry,
	EditLock,
	LockCheckResponse,
} from '$lib/types/api';

describe('Registry types (ADR-079)', () => {
	it('DiagramTypeRegistry includes expected fields', () => {
		const reg: DiagramTypeRegistry = {
			id: 'component',
			name: 'Component',
			description: 'Component diagrams',
			display_order: 0,
			is_active: true,
			notations: [
				{ notation_id: 'simple', notation_name: 'Simple', is_default: true },
				{ notation_id: 'uml', notation_name: 'UML', is_default: false },
			],
		};
		expect(reg.id).toBe('component');
		expect(reg.notations).toHaveLength(2);
		expect(reg.notations[0].is_default).toBe(true);
	});

	it('NotationMapping includes notation_id, notation_name, is_default', () => {
		const mapping: NotationMapping = {
			notation_id: 'c4',
			notation_name: 'C4',
			is_default: false,
		};
		expect(mapping.notation_id).toBe('c4');
		expect(mapping.is_default).toBe(false);
	});

	it('NotationRegistry includes expected fields', () => {
		const notation: NotationRegistry = {
			id: 'uml',
			name: 'UML',
			description: 'Unified Modeling Language',
			display_order: 1,
			is_active: true,
		};
		expect(notation.id).toBe('uml');
		expect(notation.is_active).toBe(true);
	});
});

describe('Lock types (ADR-080)', () => {
	it('EditLock includes expected fields', () => {
		const lock: EditLock = {
			id: 'lock-1',
			target_type: 'diagram',
			target_id: 'diag-1',
			user_id: 'user-1',
			username: 'alice',
			acquired_at: '2025-01-01T00:00:00Z',
			expires_at: '2025-01-01T00:15:00Z',
			last_heartbeat: '2025-01-01T00:00:00Z',
		};
		expect(lock.target_type).toBe('diagram');
		expect(lock.username).toBe('alice');
	});

	it('LockCheckResponse indicates locked state', () => {
		const check: LockCheckResponse = {
			locked: true,
			lock: {
				id: 'lock-1',
				target_type: 'diagram',
				target_id: 'diag-1',
				user_id: 'user-2',
				username: 'bob',
				acquired_at: '2025-01-01T00:00:00Z',
				expires_at: '2025-01-01T00:15:00Z',
				last_heartbeat: '2025-01-01T00:00:00Z',
			},
			is_owner: false,
		};
		expect(check.locked).toBe(true);
		expect(check.is_owner).toBe(false);
	});

	it('LockCheckResponse indicates unlocked state', () => {
		const check: LockCheckResponse = {
			locked: false,
			lock: null,
			is_owner: false,
		};
		expect(check.locked).toBe(false);
		expect(check.lock).toBeNull();
	});
});
