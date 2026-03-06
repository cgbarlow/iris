<script lang="ts">
	/**
	 * EdgeEndpointLabels: Renders cardinality and role name labels near edge endpoints (ADR-086).
	 * Positioned with offsets along and perpendicular to the edge direction.
	 */
	import { EdgeLabel } from '@xyflow/svelte';

	interface Props {
		sourceX: number;
		sourceY: number;
		targetX: number;
		targetY: number;
		sourceCardinality?: string;
		targetCardinality?: string;
		sourceRole?: string;
		targetRole?: string;
	}

	let { sourceX, sourceY, targetX, targetY, sourceCardinality, targetCardinality, sourceRole, targetRole }: Props = $props();

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

	// Source label positions (near source endpoint, offset along edge)
	const srcLabelX = $derived(sourceX + ux * ALONG + px * PERP);
	const srcLabelY = $derived(sourceY + uy * ALONG + py * PERP);
	const srcRoleX = $derived(sourceX + ux * ALONG - px * PERP);
	const srcRoleY = $derived(sourceY + uy * ALONG - py * PERP);

	// Target label positions (near target endpoint, offset back along edge)
	const tgtLabelX = $derived(targetX - ux * ALONG + px * PERP);
	const tgtLabelY = $derived(targetY - uy * ALONG + py * PERP);
	const tgtRoleX = $derived(targetX - ux * ALONG - px * PERP);
	const tgtRoleY = $derived(targetY - uy * ALONG - py * PERP);
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
