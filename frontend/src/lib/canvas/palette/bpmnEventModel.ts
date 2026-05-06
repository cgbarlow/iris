/**
 * v5.4.1 (#46 item #11): shared BPMN event-variant model. Extracted
 * from EventMatrixPicker.svelte so the new compact EventTriggerFlyout
 * can reuse the same legal-trigger logic and trigger glyph table —
 * single source of truth (DRY protocol #13).
 */
import type { BpmnEntityType, BpmnEventTrigger, BpmnEventDirection } from '$lib/types/canvas';

export interface EventVariant {
	entityType: BpmnEntityType;
	eventTrigger: BpmnEventTrigger;
	eventDirection?: BpmnEventDirection;
	boundaryInterrupting?: boolean;
}

export type EventPosition =
	| 'start'
	| 'intermediate_catch'
	| 'intermediate_throw'
	| 'end'
	| 'boundary'
	| 'boundary_ni';

export const POSITIONS: { id: EventPosition; label: string }[] = [
	{ id: 'start',              label: 'Start' },
	{ id: 'intermediate_catch', label: 'Intermediate (catch)' },
	{ id: 'intermediate_throw', label: 'Intermediate (throw)' },
	{ id: 'end',                label: 'End' },
	{ id: 'boundary',           label: 'Boundary (interrupting)' },
	{ id: 'boundary_ni',        label: 'Boundary (non-interrupting)' },
];

export const TRIGGERS: { id: BpmnEventTrigger; label: string; glyph: string }[] = [
	{ id: 'none',         label: 'None',         glyph: '○' },
	{ id: 'message',      label: 'Message',      glyph: '✉' },
	{ id: 'timer',        label: 'Timer',        glyph: '⏱' },
	{ id: 'signal',       label: 'Signal',       glyph: '▲' },
	{ id: 'conditional',  label: 'Conditional',  glyph: '☰' },
	{ id: 'error',        label: 'Error',        glyph: '⚡' },
	{ id: 'escalation',   label: 'Escalation',   glyph: '⇗' },
	{ id: 'compensation', label: 'Compensation', glyph: '◀◀' },
	{ id: 'link',         label: 'Link',         glyph: '➤' },
	{ id: 'terminate',    label: 'Terminate',    glyph: '●' },
];

/** Which (position × trigger) combinations are legal in BPMN 2.0. */
export function isLegal(p: EventPosition, t: BpmnEventTrigger): boolean {
	if (t === 'terminate') return p === 'end';
	if (t === 'error') return p !== 'intermediate_throw';
	if (t === 'timer') return p !== 'intermediate_throw' && p !== 'end';
	if (t === 'conditional') return p !== 'intermediate_throw' && p !== 'end';
	if (t === 'compensation') return p === 'intermediate_throw' || p === 'end' || p === 'boundary';
	if (t === 'link') return p === 'intermediate_catch' || p === 'intermediate_throw';
	if (t === 'escalation') return p === 'intermediate_throw' || p === 'end' || p === 'boundary' || p === 'boundary_ni' || p === 'start';
	return true;
}

export function variantFor(p: EventPosition, t: BpmnEventTrigger): EventVariant {
	switch (p) {
		case 'start':              return { entityType: 'event_start',        eventTrigger: t };
		case 'intermediate_catch': return { entityType: 'event_intermediate', eventTrigger: t, eventDirection: 'catch' };
		case 'intermediate_throw': return { entityType: 'event_intermediate', eventTrigger: t, eventDirection: 'throw' };
		case 'end':                return { entityType: 'event_end',          eventTrigger: t };
		case 'boundary':           return { entityType: 'event_boundary',     eventTrigger: t, boundaryInterrupting: true };
		case 'boundary_ni':        return { entityType: 'event_boundary',     eventTrigger: t, boundaryInterrupting: false };
	}
}

/** Map a BPMN entity type back to the position(s) it can hold. The
 *  EventTriggerFlyout uses this to pick the legal-trigger filter for a
 *  just-placed node. For event_intermediate we default to 'catch'
 *  (the user can swap to 'throw' via PropertyPanel). */
export function positionFor(entityType: BpmnEntityType): EventPosition | null {
	if (entityType === 'event_start') return 'start';
	if (entityType === 'event_intermediate') return 'intermediate_catch';
	if (entityType === 'event_end') return 'end';
	if (entityType === 'event_boundary') return 'boundary';
	return null;
}
