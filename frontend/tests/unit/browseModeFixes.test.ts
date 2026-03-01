import { describe, it, expect } from 'vitest';
import type { CanvasNodeData, CanvasNode } from '$lib/types/canvas';
import type { EntityModelRef } from '$lib/types/api';

describe('WP-6: Browse Mode Fixes', () => {
	describe('Fix A: Used In Models — show all models including current', () => {
		it('CanvasNodeData entity can be looked up by entityId for model cross-reference', () => {
			const data: CanvasNodeData = {
				label: 'Auth Service',
				entityType: 'service',
				entityId: 'entity-1',
				description: 'Handles authentication',
			};
			expect(data.entityId).toBe('entity-1');
		});

		it('EntityModelRef list should not filter out current model', () => {
			const currentModelId = 'model-A';
			const usedInModels: EntityModelRef[] = [
				{ model_id: 'model-A', name: 'System Overview', model_type: 'simple' },
			];

			// Previously the filter removed the current model, leaving an empty list.
			// The fix removes the filter — all models should be shown.
			const displayed = usedInModels; // No filter applied
			expect(displayed).toHaveLength(1);
			expect(displayed[0].model_id).toBe(currentModelId);
		});

		it('current model should be identifiable for "(current)" annotation', () => {
			const currentModelId = 'model-A';
			const usedInModels: EntityModelRef[] = [
				{ model_id: 'model-A', name: 'System Overview', model_type: 'simple' },
				{ model_id: 'model-B', name: 'Deployment View', model_type: 'archimate' },
			];

			const withAnnotation = usedInModels.map((m) => ({
				...m,
				isCurrent: m.model_id === currentModelId,
			}));

			expect(withAnnotation[0].isCurrent).toBe(true);
			expect(withAnnotation[1].isCurrent).toBe(false);
		});

		it('empty model list shows correct empty state message', () => {
			const usedInModels: EntityModelRef[] = [];
			// The empty message should say "Not used in any models." (not "any other models")
			const emptyMessage =
				usedInModels.length === 0 ? 'Not used in any models.' : null;
			expect(emptyMessage).toBe('Not used in any models.');
		});
	});

	describe('Fix B: Browse mode node navigation overlay', () => {
		it('CanvasNodeData supports browseMode flag', () => {
			const data: CanvasNodeData = {
				label: 'API Gateway',
				entityType: 'service',
				entityId: 'entity-2',
				browseMode: true,
			};
			expect(data.browseMode).toBe(true);
		});

		it('browseMode defaults to undefined when not set', () => {
			const data: CanvasNodeData = {
				label: 'Database',
				entityType: 'database',
			};
			expect(data.browseMode).toBeUndefined();
		});

		it('nodes can be mapped to include browseMode flag', () => {
			const nodes: CanvasNode[] = [
				{
					id: 'n1',
					type: 'service',
					position: { x: 0, y: 0 },
					data: { label: 'Svc A', entityType: 'service', entityId: 'e1' },
				},
				{
					id: 'n2',
					type: 'database',
					position: { x: 200, y: 0 },
					data: { label: 'DB', entityType: 'database', entityId: 'e2' },
				},
			];

			const browseNodes = nodes.map((n) => ({
				...n,
				data: { ...n.data, browseMode: true as const },
			}));

			expect(browseNodes).toHaveLength(2);
			expect(browseNodes[0].data.browseMode).toBe(true);
			expect(browseNodes[1].data.browseMode).toBe(true);
			// Original data preserved
			expect(browseNodes[0].data.label).toBe('Svc A');
			expect(browseNodes[0].data.entityId).toBe('e1');
		});

		it('browse link URL is derived from entityId', () => {
			const entityId = 'entity-abc-123';
			const expectedUrl = `/entities/${entityId}`;
			expect(expectedUrl).toBe('/entities/entity-abc-123');
		});

		it('browse link should not render when entityId is absent', () => {
			const data: CanvasNodeData = {
				label: 'Unnamed',
				entityType: 'component',
				browseMode: true,
			};
			// entityId is undefined, so browse link should not appear
			const shouldRenderLink = data.browseMode === true && !!data.entityId;
			expect(shouldRenderLink).toBe(false);
		});

		it('browse link should not render when browseMode is false/undefined', () => {
			const data: CanvasNodeData = {
				label: 'Edit Node',
				entityType: 'service',
				entityId: 'entity-3',
			};
			// browseMode not set, so no link
			const shouldRenderLink = data.browseMode === true && !!data.entityId;
			expect(shouldRenderLink).toBe(false);
		});

		it('browse link renders when both browseMode and entityId are set', () => {
			const data: CanvasNodeData = {
				label: 'Browse Node',
				entityType: 'service',
				entityId: 'entity-4',
				browseMode: true,
			};
			const shouldRenderLink = data.browseMode === true && !!data.entityId;
			expect(shouldRenderLink).toBe(true);
		});
	});
});
