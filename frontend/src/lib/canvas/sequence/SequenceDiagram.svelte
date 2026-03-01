<script lang="ts">
	/**
	 * Custom sequence diagram renderer with keyboard accessibility.
	 * Renders lifelines, messages, and activation boxes using SVG.
	 */
	import type { SequenceDiagramData, Participant, SequenceMessage, Activation } from './types';
	import { SEQUENCE_LAYOUT as L } from './types';

	interface Props {
		data: SequenceDiagramData;
		selectedMessageId?: string | null;
		onmessageselect?: (messageId: string) => void;
		onparticipantselect?: (participant: Participant) => void;
		viewBox?: string | null;
		onwheel?: (e: WheelEvent) => void;
		onpointerdown?: (e: PointerEvent) => void;
		onpointermove?: (e: PointerEvent) => void;
		onpointerup?: (e: PointerEvent) => void;
	}

	let {
		data,
		selectedMessageId = null,
		onmessageselect,
		onparticipantselect,
		viewBox = null,
		onwheel,
		onpointerdown,
		onpointermove,
		onpointerup,
	}: Props = $props();

	/** Calculate the X center of a participant. */
	function participantX(index: number): number {
		return L.padding + index * (L.participantWidth + L.participantGap) + L.participantWidth / 2;
	}

	/** Calculate the Y position of a message. */
	function messageY(order: number): number {
		return L.messageStartY + order * L.messageGap;
	}

	/** Get participant index by ID. */
	function participantIndex(id: string): number {
		return data.participants.findIndex((p) => p.id === id);
	}

	/** Calculate total diagram width. */
	const diagramWidth = $derived(
		data.participants.length * (L.participantWidth + L.participantGap) -
			L.participantGap +
			L.padding * 2,
	);

	/** Calculate total diagram height. */
	const diagramHeight = $derived(
		L.messageStartY +
			(data.messages.length + 1) * L.messageGap +
			L.participantHeight +
			L.padding,
	);

	/** Sorted messages by order. */
	const sortedMessages = $derived([...data.messages].sort((a, b) => a.order - b.order));

	function handleParticipantClick(participant: Participant) {
		onparticipantselect?.(participant);
	}

	function handleMessageClick(messageId: string) {
		onmessageselect?.(messageId);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (!sortedMessages.length) return;

		const currentIndex = sortedMessages.findIndex((m) => m.id === selectedMessageId);

		if (event.key === 'ArrowDown' || event.key === 'Tab') {
			event.preventDefault();
			const next = currentIndex >= sortedMessages.length - 1 ? 0 : currentIndex + 1;
			onmessageselect?.(sortedMessages[next].id);
		} else if (event.key === 'ArrowUp' || (event.key === 'Tab' && event.shiftKey)) {
			event.preventDefault();
			const prev = currentIndex <= 0 ? sortedMessages.length - 1 : currentIndex - 1;
			onmessageselect?.(sortedMessages[prev].id);
		}
	}

	function messageAriaLabel(msg: SequenceMessage): string {
		const fromName = data.participants.find((p) => p.id === msg.from)?.name ?? msg.from;
		const toName = data.participants.find((p) => p.id === msg.to)?.name ?? msg.to;
		return `Message ${msg.order + 1}: ${fromName} ${msg.type === 'reply' ? 'replies to' : 'calls'} ${toName}, ${msg.label}`;
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	class="sequence-diagram"
	role="application"
	aria-label="Sequence diagram with {data.participants.length} participants and {data.messages.length} messages"
	aria-roledescription="sequence diagram"
	onkeydown={handleKeydown}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<svg
		viewBox={viewBox ?? `0 0 ${diagramWidth} ${diagramHeight}`}
		preserveAspectRatio="xMidYMid meet"
		xmlns="http://www.w3.org/2000/svg"
		role="img"
		aria-label="Sequence diagram"
		onwheel={onwheel}
		onpointerdown={onpointerdown}
		onpointermove={onpointermove}
		onpointerup={onpointerup}
	>
		<!-- Lifelines -->
		{#each data.participants as participant, i}
			{@const cx = participantX(i)}
			<line
				x1={cx}
				y1={L.headerY + L.participantHeight}
				x2={cx}
				y2={diagramHeight - L.padding}
				stroke={L.lifelineStroke}
				stroke-dasharray="6 4"
				aria-hidden="true"
			/>
		{/each}

		<!-- Participant headers -->
		{#each data.participants as participant, i}
			{@const cx = participantX(i)}
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_tabindex -->
			<g
				aria-label="{participant.name}, {participant.type}"
				role={onparticipantselect ? 'button' : undefined}
				tabindex={onparticipantselect ? 0 : undefined}
				onclick={() => handleParticipantClick(participant)}
				onkeydown={(e: KeyboardEvent) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						handleParticipantClick(participant);
					}
				}}
				style={onparticipantselect ? 'cursor: pointer' : undefined}
				class="sequence-participant-header"
			>
				<rect
					x={cx - L.participantWidth / 2}
					y={L.headerY}
					width={L.participantWidth}
					height={L.participantHeight}
					rx="4"
					class="sequence-participant"
				/>
				<text
					x={cx}
					y={L.headerY + L.participantHeight / 2}
					text-anchor="middle"
					dominant-baseline="central"
					class="sequence-participant__label"
				>
					{participant.name}
				</text>
			</g>
		{/each}

		<!-- Activation boxes -->
		{#each data.activations as activation}
			{@const pi = participantIndex(activation.participantId)}
			{@const cx = participantX(pi)}
			<rect
				x={cx - L.activationWidth / 2}
				y={messageY(activation.startOrder) - 5}
				width={L.activationWidth}
				height={messageY(activation.endOrder) - messageY(activation.startOrder) + 10}
				class="sequence-activation"
				aria-hidden="true"
			/>
		{/each}

		<!-- Messages -->
		{#each sortedMessages as msg}
			{@const fromX = participantX(participantIndex(msg.from))}
			{@const toX = participantX(participantIndex(msg.to))}
			{@const y = messageY(msg.order)}
			{@const isSelected = msg.id === selectedMessageId}
			{@const dir = toX > fromX ? 1 : -1}

			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<g
				role="button"
				tabindex="0"
				aria-label={messageAriaLabel(msg)}
				aria-pressed={isSelected}
				onclick={() => handleMessageClick(msg.id)}
				class="sequence-message"
				class:sequence-message--selected={isSelected}
			>
				<line
					x1={fromX}
					y1={y}
					x2={toX}
					y2={y}
					class="sequence-message__line"
					stroke-dasharray={msg.type === 'async' ? '6 3' : msg.type === 'reply' ? '4 4' : 'none'}
				/>

				<polygon
					points="{toX},{y} {toX - 8 * dir},{y - 4} {toX - 8 * dir},{y + 4}"
					class="sequence-message__arrow"
					class:sequence-message__arrow--open={msg.type === 'async'}
				/>

				<text
					x={(fromX + toX) / 2}
					y={y - 8}
					text-anchor="middle"
					class="sequence-message__label"
				>
					{msg.label}
				</text>
			</g>
		{/each}

		<!-- Bottom participant boxes (mirror) -->
		{#each data.participants as participant, i}
			{@const cx = participantX(i)}
			<rect
				x={cx - L.participantWidth / 2}
				y={diagramHeight - L.padding - L.participantHeight}
				width={L.participantWidth}
				height={L.participantHeight}
				rx="4"
				class="sequence-participant"
				aria-hidden="true"
			/>
			<text
				x={cx}
				y={diagramHeight - L.padding - L.participantHeight / 2}
				text-anchor="middle"
				dominant-baseline="central"
				class="sequence-participant__label"
				aria-hidden="true"
			>
				{participant.name}
			</text>
		{/each}
	</svg>
</div>
