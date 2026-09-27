/**
 * Provider reasoning effort (ADR-256). Mirrors `ModelParameters.reasoning_effort`
 * in backend/app/ai/models.py. Blank ('') means "omit from the request".
 */
export const REASONING_EFFORTS = ['none', 'low', 'medium', 'high'] as const;

export type ReasoningEffort = (typeof REASONING_EFFORTS)[number];

export function reasoningEffortFromParams(params: Record<string, unknown>): ReasoningEffort | '' {
	const v = params.reasoning_effort;
	return (REASONING_EFFORTS as readonly unknown[]).includes(v) ? (v as ReasoningEffort) : '';
}
