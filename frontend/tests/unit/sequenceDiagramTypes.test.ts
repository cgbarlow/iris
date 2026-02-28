import { describe, it, expect } from 'vitest';
import { SEQUENCE_LAYOUT } from '$lib/canvas/sequence/types';
import type { SequenceDiagramData, Participant, SequenceMessage, Activation } from '$lib/canvas/sequence/types';

describe('SequenceDiagram types', () => {
	it('SEQUENCE_LAYOUT has all required properties', () => {
		expect(SEQUENCE_LAYOUT.participantWidth).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.participantHeight).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.participantGap).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.headerY).toBeGreaterThanOrEqual(0);
		expect(SEQUENCE_LAYOUT.messageStartY).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.messageGap).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.activationWidth).toBeGreaterThan(0);
		expect(SEQUENCE_LAYOUT.lifelineStroke).toBeTruthy();
		expect(SEQUENCE_LAYOUT.padding).toBeGreaterThan(0);
	});

	it('accepts valid SequenceDiagramData', () => {
		const data: SequenceDiagramData = {
			participants: [
				{ id: 'p1', name: 'Client', type: 'actor' },
				{ id: 'p2', name: 'Server', type: 'service' },
			],
			messages: [
				{ id: 'm1', from: 'p1', to: 'p2', label: 'request()', type: 'sync', order: 0 },
			],
			activations: [
				{ participantId: 'p2', startOrder: 0, endOrder: 0 },
			],
		};
		expect(data.participants).toHaveLength(2);
		expect(data.messages).toHaveLength(1);
		expect(data.activations).toHaveLength(1);
	});

	it('empty sequence data is valid', () => {
		const data: SequenceDiagramData = {
			participants: [],
			messages: [],
			activations: [],
		};
		expect(data.participants).toHaveLength(0);
		expect(data.messages).toHaveLength(0);
		expect(data.activations).toHaveLength(0);
	});

	it('participant types are constrained', () => {
		const validTypes: Participant['type'][] = ['actor', 'component', 'service'];
		const participant: Participant = { id: 'p1', name: 'Test', type: 'actor' };
		expect(validTypes).toContain(participant.type);
	});

	it('message types are constrained', () => {
		const validTypes: SequenceMessage['type'][] = ['sync', 'async', 'reply'];
		const message: SequenceMessage = { id: 'm1', from: 'p1', to: 'p2', label: 'test', type: 'sync', order: 0 };
		expect(validTypes).toContain(message.type);
	});
});
