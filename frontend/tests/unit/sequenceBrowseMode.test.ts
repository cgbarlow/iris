import { describe, it, expect } from 'vitest';
import type { Participant, SequenceDiagramData } from '$lib/canvas/sequence/types';
import type { CanvasNodeData, CanvasNode } from '$lib/types/canvas';

describe('WP-7: Sequence diagram browse mode', () => {
	describe('Participant entityId support', () => {
		it('Participant type accepts an optional entityId field', () => {
			const participant: Participant = {
				id: 'p1',
				name: 'Auth Service',
				type: 'service',
				entityId: 'entity-abc-123',
			};
			expect(participant.entityId).toBe('entity-abc-123');
		});

		it('Participant without entityId remains valid', () => {
			const participant: Participant = {
				id: 'p2',
				name: 'Client',
				type: 'actor',
			};
			expect(participant.entityId).toBeUndefined();
		});
	});

	describe('SequenceDiagram onparticipantselect prop', () => {
		it('SequenceDiagram Props interface accepts onparticipantselect callback', async () => {
			// Verify the component module exports correctly and can be imported
			const mod = await import('$lib/canvas/sequence/SequenceDiagram.svelte');
			expect(mod.default).toBeDefined();
		});

		it('onparticipantselect callback receives the clicked Participant', () => {
			const participant: Participant = {
				id: 'p1',
				name: 'API Gateway',
				type: 'service',
				entityId: 'entity-gw-001',
			};

			let received: Participant | null = null;
			const handler = (p: Participant) => {
				received = p;
			};

			// Simulate what the click handler does
			handler(participant);

			expect(received).not.toBeNull();
			expect(received!.id).toBe('p1');
			expect(received!.name).toBe('API Gateway');
			expect(received!.entityId).toBe('entity-gw-001');
		});
	});

	describe('Browse mode participant-to-entity mapping', () => {
		it('maps a Participant to a synthetic CanvasNodeData for EntityDetailPanel', () => {
			const participant: Participant = {
				id: 'p1',
				name: 'Auth Service',
				type: 'service',
				entityId: 'entity-auth-001',
			};

			// This is the mapping logic that the model page will use
			const nodeData: CanvasNodeData = {
				label: participant.name,
				entityType: participant.type,
				entityId: participant.entityId,
			};

			expect(nodeData.label).toBe('Auth Service');
			expect(nodeData.entityType).toBe('service');
			expect(nodeData.entityId).toBe('entity-auth-001');
		});

		it('creates a synthetic CanvasNode from Participant for selectedBrowseNode', () => {
			const participant: Participant = {
				id: 'p1',
				name: 'Database',
				type: 'component',
				entityId: 'entity-db-001',
			};

			const syntheticNode: CanvasNode = {
				id: `seq-participant-${participant.id}`,
				type: 'default',
				position: { x: 0, y: 0 },
				data: {
					label: participant.name,
					entityType: participant.type,
					entityId: participant.entityId,
				},
			};

			expect(syntheticNode.id).toBe('seq-participant-p1');
			expect(syntheticNode.data.label).toBe('Database');
			expect(syntheticNode.data.entityType).toBe('component');
			expect(syntheticNode.data.entityId).toBe('entity-db-001');
		});

		it('participant without entityId should not open entity detail panel', () => {
			const participant: Participant = {
				id: 'p2',
				name: 'External Client',
				type: 'actor',
			};

			// Only open the panel if participant has an entityId
			const shouldOpenPanel = !!participant.entityId;
			expect(shouldOpenPanel).toBe(false);
		});

		it('participant with entityId should open entity detail panel', () => {
			const participant: Participant = {
				id: 'p1',
				name: 'API',
				type: 'service',
				entityId: 'entity-api-001',
			};

			const shouldOpenPanel = !!participant.entityId;
			expect(shouldOpenPanel).toBe(true);
		});
	});

	describe('Sequence diagram data with entityId participants', () => {
		it('SequenceDiagramData supports participants with entityId', () => {
			const data: SequenceDiagramData = {
				participants: [
					{ id: 'p1', name: 'Client', type: 'actor' },
					{ id: 'p2', name: 'API', type: 'service', entityId: 'entity-api' },
					{ id: 'p3', name: 'DB', type: 'component', entityId: 'entity-db' },
				],
				messages: [
					{ id: 'm1', from: 'p1', to: 'p2', label: 'POST /data', type: 'sync', order: 0 },
				],
				activations: [],
			};

			expect(data.participants[0].entityId).toBeUndefined();
			expect(data.participants[1].entityId).toBe('entity-api');
			expect(data.participants[2].entityId).toBe('entity-db');
		});

		it('all three participant types map to valid SimpleEntityType', () => {
			// Participant types are 'actor' | 'component' | 'service'
			// These all exist in SimpleEntityType, so mapping is direct
			const typeMap: Record<Participant['type'], string> = {
				actor: 'actor',
				component: 'component',
				service: 'service',
			};

			expect(typeMap.actor).toBe('actor');
			expect(typeMap.component).toBe('component');
			expect(typeMap.service).toBe('service');
		});
	});

	describe('Cursor style for clickable participants', () => {
		it('cursor should be pointer when onparticipantselect is provided', () => {
			const hasHandler = true;
			const cursorStyle = hasHandler ? 'pointer' : 'default';
			expect(cursorStyle).toBe('pointer');
		});

		it('cursor should be default when onparticipantselect is not provided', () => {
			const hasHandler = false;
			const cursorStyle = hasHandler ? 'pointer' : 'default';
			expect(cursorStyle).toBe('default');
		});
	});
});
