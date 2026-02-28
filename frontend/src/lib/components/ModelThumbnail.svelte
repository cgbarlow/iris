<script lang="ts">
	interface Props {
		data: Record<string, unknown>;
		modelType: string;
	}

	let { data, modelType }: Props = $props();

	const CANVAS_TYPES = ['simple', 'component', 'uml', 'archimate'];

	interface NodeInfo {
		id: string;
		x: number;
		y: number;
	}

	interface EdgeInfo {
		source: string;
		target: string;
	}

	const canvasData = $derived.by(() => {
		if (!CANVAS_TYPES.includes(modelType)) return null;
		const rawNodes = data?.nodes;
		if (!Array.isArray(rawNodes) || rawNodes.length === 0) return null;

		const nodes: NodeInfo[] = rawNodes.map((n: Record<string, unknown>) => ({
			id: String(n.id),
			x: Number((n.position as Record<string, unknown>)?.x ?? 0),
			y: Number((n.position as Record<string, unknown>)?.y ?? 0),
		}));

		const rawEdges = data?.edges;
		const edges: EdgeInfo[] = Array.isArray(rawEdges)
			? rawEdges.map((e: Record<string, unknown>) => ({
					source: String(e.source),
					target: String(e.target),
				}))
			: [];

		const xs = nodes.map((n) => n.x);
		const ys = nodes.map((n) => n.y);
		const minX = Math.min(...xs);
		const maxX = Math.max(...xs);
		const minY = Math.min(...ys);
		const maxY = Math.max(...ys);

		const nodeW = 24;
		const nodeH = 16;
		const rawW = maxX - minX + nodeW;
		const rawH = maxY - minY + nodeH;
		const padX = Math.max(rawW * 0.1, 20);
		const padY = Math.max(rawH * 0.1, 20);

		const viewBox = `${minX - padX} ${minY - padY} ${rawW + padX * 2} ${rawH + padY * 2}`;

		const nodeMap = new Map(nodes.map((n) => [n.id, n]));

		return { nodes, edges, viewBox, nodeMap, nodeW, nodeH };
	});

	const sequenceData = $derived.by(() => {
		if (modelType !== 'sequence') return null;
		const rawParticipants = data?.participants;
		if (!Array.isArray(rawParticipants) || rawParticipants.length === 0) return null;

		const participants = rawParticipants.map((p: Record<string, unknown>, i: number) => ({
			id: String(p.id ?? i),
			x: 40 + i * 60,
		}));

		const rawMessages = data?.messages;
		const messages: { fromIdx: number; toIdx: number; y: number }[] = [];
		if (Array.isArray(rawMessages)) {
			rawMessages.forEach((m: Record<string, unknown>, i: number) => {
				const fromIdx = participants.findIndex((p) => p.id === String(m.from));
				const toIdx = participants.findIndex((p) => p.id === String(m.to));
				if (fromIdx >= 0 && toIdx >= 0) {
					messages.push({ fromIdx, toIdx, y: 40 + (i + 1) * 25 });
				}
			});
		}

		const width = participants.length * 60 + 20;
		const height = Math.max(120, 40 + (messages.length + 1) * 25 + 20);

		return { participants, messages, width, height };
	});

	const isEmpty = $derived(!canvasData && !sequenceData);
</script>

<svg
	data-testid="model-thumbnail"
	aria-hidden="true"
	class="h-full w-full"
	style="background: var(--color-surface)"
	viewBox={canvasData
		? canvasData.viewBox
		: sequenceData
			? `0 0 ${sequenceData.width} ${sequenceData.height}`
			: '0 0 200 112'}
	preserveAspectRatio="xMidYMid meet"
>
	{#if canvasData}
		{#each canvasData.edges as edge}
			{@const src = canvasData.nodeMap.get(edge.source)}
			{@const tgt = canvasData.nodeMap.get(edge.target)}
			{#if src && tgt}
				<line
					x1={src.x + canvasData.nodeW / 2}
					y1={src.y + canvasData.nodeH / 2}
					x2={tgt.x + canvasData.nodeW / 2}
					y2={tgt.y + canvasData.nodeH / 2}
					stroke="var(--color-border)"
					stroke-width="2"
				/>
			{/if}
		{/each}
		{#each canvasData.nodes as node}
			<rect
				x={node.x}
				y={node.y}
				width={canvasData.nodeW}
				height={canvasData.nodeH}
				rx="3"
				fill="var(--color-primary)"
			/>
		{/each}
	{:else if sequenceData}
		{#each sequenceData.participants as p}
			<circle cx={p.x} cy={20} r="8" fill="var(--color-primary)" />
			<line
				x1={p.x}
				y1={28}
				x2={p.x}
				y2={sequenceData.height - 10}
				stroke="var(--color-border)"
				stroke-width="1"
				stroke-dasharray="4 3"
			/>
		{/each}
		{#each sequenceData.messages as msg}
			{@const fromX = sequenceData.participants[msg.fromIdx].x}
			{@const toX = sequenceData.participants[msg.toIdx].x}
			<line
				x1={fromX}
				y1={msg.y}
				x2={toX}
				y2={msg.y}
				stroke="var(--color-border)"
				stroke-width="1.5"
				marker-end="url(#arrowhead)"
			/>
		{/each}
		<defs>
			<marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
				<polygon points="0 0, 6 2, 0 4" fill="var(--color-border)" />
			</marker>
		</defs>
	{:else if isEmpty}
		<text
			x="100"
			y="56"
			text-anchor="middle"
			dominant-baseline="middle"
			fill="var(--color-muted)"
			font-size="14"
		>
			No diagram
		</text>
	{/if}
</svg>
