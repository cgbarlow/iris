<script lang="ts">
	/**
	 * BpmnEdgeRenderer: Renders BPMN 2.0 connecting objects (ADR-136).
	 *
	 * Sequence flow:             solid line, filled arrowhead
	 * Default sequence flow:     solid line + diagonal slash near source
	 * Conditional sequence flow: solid line + small diamond at source
	 * Message flow:              dashed line, open arrowhead
	 * Association:               dotted line, no arrowhead (or open if directional)
	 * Data association:          dotted line, open arrowhead
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	const edgeType = $derived((props.data?.bpmnEdgeType as string) ?? props.data?.relationshipType ?? 'sequence_flow');

	const DASH_PATTERNS: Record<string, string> = {
		sequence_flow:             'none',
		sequence_flow_default:     'none',
		sequence_flow_conditional: 'none',
		message_flow:              '6 4',
		association:               '2 3',
		data_association:          '2 3',
	};

	const dashArray = $derived(DASH_PATTERNS[edgeType] ?? 'none');
</script>

<IrisBaseEdge {...props} {dashArray} />
