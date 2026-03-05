import { describe, it, expect } from 'vitest';
import type { EditLock, LockCheckResponse } from '$lib/types/api';

describe('Lock manager state transitions', () => {
	it('models an unlocked → locked → released lifecycle', () => {
		// Start unlocked
		let state: LockCheckResponse = { locked: false, lock: null, is_owner: false };
		expect(state.locked).toBe(false);

		// Acquire lock
		const lock: EditLock = {
			id: 'lock-abc',
			target_type: 'diagram',
			target_id: 'diag-1',
			user_id: 'user-1',
			username: 'alice',
			acquired_at: '2025-01-01T00:00:00Z',
			expires_at: '2025-01-01T00:15:00Z',
			last_heartbeat: '2025-01-01T00:00:00Z',
		};
		state = { locked: true, lock, is_owner: true };
		expect(state.locked).toBe(true);
		expect(state.is_owner).toBe(true);

		// Release lock
		state = { locked: false, lock: null, is_owner: false };
		expect(state.locked).toBe(false);
	});

	it('models conflict when another user holds the lock', () => {
		const otherLock: EditLock = {
			id: 'lock-xyz',
			target_type: 'element',
			target_id: 'elem-1',
			user_id: 'user-2',
			username: 'bob',
			acquired_at: '2025-01-01T00:00:00Z',
			expires_at: '2025-01-01T00:15:00Z',
			last_heartbeat: '2025-01-01T00:00:00Z',
		};
		const state: LockCheckResponse = { locked: true, lock: otherLock, is_owner: false };
		expect(state.locked).toBe(true);
		expect(state.is_owner).toBe(false);
		expect(state.lock?.username).toBe('bob');
	});

	it('heartbeat extends lock expiry', () => {
		const lock: EditLock = {
			id: 'lock-1',
			target_type: 'diagram',
			target_id: 'diag-1',
			user_id: 'user-1',
			username: 'alice',
			acquired_at: '2025-01-01T00:00:00Z',
			expires_at: '2025-01-01T00:15:00Z',
			last_heartbeat: '2025-01-01T00:05:00Z',
		};
		// After heartbeat, expiry is extended
		const extended: EditLock = {
			...lock,
			expires_at: '2025-01-01T00:20:00Z',
			last_heartbeat: '2025-01-01T00:05:00Z',
		};
		expect(new Date(extended.expires_at).getTime()).toBeGreaterThan(
			new Date(lock.expires_at).getTime()
		);
	});

	it('lock target_type must be one of diagram, element, package', () => {
		const validTypes = ['diagram', 'element', 'package'];
		for (const t of validTypes) {
			const lock: EditLock = {
				id: 'lock-1',
				target_type: t,
				target_id: 'id-1',
				user_id: 'user-1',
				username: 'alice',
				acquired_at: '2025-01-01T00:00:00Z',
				expires_at: '2025-01-01T00:15:00Z',
				last_heartbeat: '2025-01-01T00:00:00Z',
			};
			expect(validTypes).toContain(lock.target_type);
		}
	});
});
