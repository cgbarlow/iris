<script lang="ts">
	/**
	 * v5.2.0 (issue #37): minimal aria-live toast used by the BPMN authoring
	 * shell to surface canConnect rejection reasons. Two-way bindable
	 * `message` prop — the parent sets it on rejection, the toast clears it
	 * after a timeout so a subsequent identical rejection can still re-fire.
	 *
	 * Iris doesn't have a toast library (per DRY survey), and this is the
	 * only consumer in v5.2.0. Kept inline to avoid pulling a dep for a
	 * single use site; can be lifted into a shared library later.
	 */
	interface Props {
		/** Bindable message. Setting to a non-empty string shows the toast;
		 *  the toast clears itself back to '' after `duration` ms. */
		message: string;
		duration?: number;
	}

	let { message = $bindable(''), duration = 3500 }: Props = $props();

	let timer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		if (timer) {
			clearTimeout(timer);
			timer = null;
		}
		if (message) {
			timer = setTimeout(() => {
				message = '';
				timer = null;
			}, duration);
		}
		return () => {
			if (timer) {
				clearTimeout(timer);
				timer = null;
			}
		};
	});
</script>

{#if message}
	<div class="bpmn-toast" role="status" aria-live="polite">
		{message}
		<button
			type="button"
			class="bpmn-toast__dismiss"
			aria-label="Dismiss"
			onclick={() => (message = '')}
		>×</button>
	</div>
{/if}

<style>
	.bpmn-toast {
		position: fixed;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		display: inline-flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px 10px 16px;
		max-width: 420px;
		font-size: 13px;
		line-height: 1.4;
		color: #fff;
		background: rgba(20, 20, 20, 0.92);
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
		z-index: 1000;
	}
	.bpmn-toast__dismiss {
		all: unset;
		cursor: pointer;
		font-size: 18px;
		line-height: 1;
		opacity: 0.8;
	}
	.bpmn-toast__dismiss:hover { opacity: 1; }
	.bpmn-toast__dismiss:focus-visible {
		outline: 2px solid #fff;
		outline-offset: 2px;
	}
</style>
