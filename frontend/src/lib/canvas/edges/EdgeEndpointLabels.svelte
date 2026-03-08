<script lang="ts">
	/**
	 * EdgeEndpointLabels: Renders cardinality and role name labels near edge endpoints (ADR-086).
	 * Positioned with offsets along and perpendicular to the edge direction.
	 * Accepts optional labelPositions from EA for data-driven positioning (ADR-088).
	 */
	import { EdgeLabel } from '@xyflow/svelte';

	interface LabelPos {
		cx: number;
		cy: number;
	}

	interface LabelPositions {
		llb?: LabelPos;
		llt?: LabelPos;
		lrt?: LabelPos;
		lrb?: LabelPos;
	}

	interface Props {
		sourceX: number;
		sourceY: number;
		targetX: number;
		targetY: number;
		sourceCardinality?: string;
		targetCardinality?: string;
		sourceRole?: string;
		targetRole?: string;
		labelPositions?: LabelPositions;
	}

	let { sourceX, sourceY, targetX, targetY, sourceCardinality, targetCardinality, sourceRole, targetRole, labelPositions }: Props = $props();

	/** Compute offset positions along and perpendicular to the edge. */
	const ALONG = 25;
	const PERP = 14;

	const dx = $derived(targetX - sourceX);
	const dy = $derived(targetY - sourceY);
	const len = $derived(Math.sqrt(dx * dx + dy * dy) || 1);

	// Unit vectors along and perpendicular to the edge
	const ux = $derived(dx / len);
	const uy = $derived(dy / len);
	const px = $derived(-uy); // perpendicular
	const py = $derived(ux);

	// Source cardinality position (LLB = source cardinality)
	const srcLabelX = $derived(labelPositions?.llb ? sourceX + labelPositions.llb.cx : sourceX + ux * ALONG + px * PERP);
	const srcLabelY = $derived(labelPositions?.llb ? sourceY - labelPositions.llb.cy : sourceY + uy * ALONG + py * PERP);

	// Source role position (LLT = source role)
	const srcRoleX = $derived(labelPositions?.llt ? sourceX + labelPositions.llt.cx : sourceX + ux * ALONG - px * PERP);
	const srcRoleY = $derived(labelPositions?.llt ? sourceY - labelPositions.llt.cy : sourceY + uy * ALONG - py * PERP);

	// Target cardinality position (LRT = target cardinality)
	const tgtLabelX = $derived(labelPositions?.lrt ? targetX + labelPositions.lrt.cx : targetX - ux * ALONG + px * PERP);
	const tgtLabelY = $derived(labelPositions?.lrt ? targetY - labelPositions.lrt.cy : targetY - uy * ALONG + py * PERP);

	// Target role position (LRB = target role)
	const tgtRoleX = $derived(labelPositions?.lrb ? targetX + labelPositions.lrb.cx : targetX - ux * ALONG - px * PERP);
	const tgtRoleY = $derived(labelPositions?.lrb ? targetY - labelPositions.lrb.cy : targetY - uy * ALONG - py * PERP);
</script>

{#if sourceCardinality}
	<EdgeLabel x={srcLabelX} y={srcLabelY}>
		<span class="edge-endpoint-label">{sourceCardinality}</span>
	</EdgeLabel>
{/if}
{#if sourceRole}
	<EdgeLabel x={srcRoleX} y={srcRoleY}>
		<span class="edge-endpoint-label edge-endpoint-label--role">{sourceRole}</span>
	</EdgeLabel>
{/if}
{#if targetCardinality}
	<EdgeLabel x={tgtLabelX} y={tgtLabelY}>
		<span class="edge-endpoint-label">{targetCardinality}</span>
	</EdgeLabel>
{/if}
{#if targetRole}
	<EdgeLabel x={tgtRoleX} y={tgtRoleY}>
		<span class="edge-endpoint-label edge-endpoint-label--role">{targetRole}</span>
	</EdgeLabel>
{/if}

<style>
	.edge-endpoint-label {
		font-size: 0.65rem;
		color: var(--color-fg, #333);
		background: var(--color-bg, #fff);
		padding: 0 2px;
		border-radius: 2px;
		white-space: nowrap;
		font-family: monospace;
	}
	.edge-endpoint-label--role {
		font-style: italic;
		color: var(--color-muted, #666);
	}
</style>
