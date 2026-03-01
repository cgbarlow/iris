/** Sequence diagram type definitions. */

/** A participant (lifeline) in a sequence diagram. */
export interface Participant {
	id: string;
	name: string;
	type: 'actor' | 'component' | 'service';
	entityId?: string;
}

/** A message between participants. */
export interface SequenceMessage {
	id: string;
	from: string;
	to: string;
	label: string;
	type: 'sync' | 'async' | 'reply';
	order: number;
}

/** An activation bar on a lifeline. */
export interface Activation {
	participantId: string;
	startOrder: number;
	endOrder: number;
}

/** Full sequence diagram data model. */
export interface SequenceDiagramData {
	participants: Participant[];
	messages: SequenceMessage[];
	activations: Activation[];
}

/** Layout constants for sequence diagram rendering. */
export const SEQUENCE_LAYOUT = {
	participantWidth: 120,
	participantHeight: 40,
	participantGap: 60,
	headerY: 20,
	messageStartY: 100,
	messageGap: 50,
	activationWidth: 12,
	lifelineStroke: '#94a3b8',
	padding: 40,
} as const;
