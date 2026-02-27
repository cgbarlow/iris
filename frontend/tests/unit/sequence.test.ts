import { describe, it, expect } from 'vitest';
import { SEQUENCE_LAYOUT } from '$lib/canvas/sequence';
import type { SequenceDiagramData } from '$lib/canvas/sequence';

describe('Sequence diagram types and layout', () => {
	it('has valid layout constants', () => {
		expect(SEQUENCE_LAYOUT.participantWidth).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.participantHeight).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.participantGap).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.messageGap).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.activationWidth).toBeGreaterThan(0);
	});

	it('can construct a valid sequence diagram data object', () => {
		const data: SequenceDiagramData = {
			participants: [
				{ id: 'p1', name: 'Client', type: 'actor' },
				{ id: 'p2', name: 'API', type: 'service' },
				{ id: 'p3', name: 'DB', type: 'component' },
			],
			messages: [
				{ id: 'm1', from: 'p1', to: 'p2', label: 'POST /login', type: 'sync', order: 0 },
				{ id: 'm2', from: 'p2', to: 'p3', label: 'SELECT user', type: 'sync', order: 1 },
				{ id: 'm3', from: 'p3', to: 'p2', label: 'user row', type: 'reply', order: 2 },
				{ id: 'm4', from: 'p2', to: 'p1', label: '200 OK', type: 'reply', order: 3 },
			],
			activations: [
				{ participantId: 'p2', startOrder: 0, endOrder: 3 },
				{ participantId: 'p3', startOrder: 1, endOrder: 2 },
			],
		};

		expect(data.participants).toHaveLength(3);
		expect(data.messages).toHaveLength(4);
		expect(data.activations).toHaveLength(2);
	});

	it('messages can be sorted by order', () => {
		const messages = [
			{ id: 'm3', from: 'p1', to: 'p2', label: 'c', type: 'sync' as const, order: 2 },
			{ id: 'm1', from: 'p1', to: 'p2', label: 'a', type: 'sync' as const, order: 0 },
			{ id: 'm2', from: 'p2', to: 'p1', label: 'b', type: 'reply' as const, order: 1 },
		];
		const sorted = [...messages].sort((a, b) => a.order - b.order);
		expect(sorted[0].id).toBe('m1');
		expect(sorted[1].id).toBe('m2');
		expect(sorted[2].id).toBe('m3');
	});

	it('participant types cover expected values', () => {
		const types = ['actor', 'component', 'service'] as const;
		for (const t of types) {
			const p = { id: 'test', name: 'Test', type: t };
			expect(p.type).toBe(t);
		}
	});

	it('message types cover sync, async, and reply', () => {
		const types = ['sync', 'async', 'reply'] as const;
		for (const t of types) {
			const m = { id: 'test', from: 'a', to: 'b', label: 'test', type: t, order: 0 };
			expect(m.type).toBe(t);
		}
	});
});
