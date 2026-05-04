<script lang="ts">
	/**
	 * ProblemsPanel: bottom-docked panel listing active BPMN warnings (ADR-136).
	 *
	 * Click a problem to focus the canvas on the offending element(s).
	 * Empty state when there are no problems. Severity counts in the header.
	 */
	import { validateBpmn, type BpmnDiagramData, type BpmnProblem } from './bpmnRules';

	interface Props {
		data: BpmnDiagramData;
		onfocus?: (elementIds: string[]) => void;
	}

	let { data, onfocus }: Props = $props();

	const problems = $derived(validateBpmn(data));
	const counts = $derived.by(() => {
		const c = { error: 0, warning: 0, info: 0 };
		for (const p of problems) c[p.severity]++;
		return c;
	});

	function severityGlyph(s: BpmnProblem['severity']): string {
		return s === 'error' ? '✖' : s === 'warning' ? '⚠' : 'ℹ';
	}
</script>

<section class="bpmn-problems" aria-label="BPMN validation problems">
	<header class="bpmn-problems__header">
		<span class="bpmn-problems__title">Problems</span>
		<span class="bpmn-problems__counts">
			<span class="bpmn-problems__count bpmn-problems__count--error">{counts.error}</span>
			<span class="bpmn-problems__count bpmn-problems__count--warning">{counts.warning}</span>
			<span class="bpmn-problems__count bpmn-problems__count--info">{counts.info}</span>
		</span>
	</header>
	{#if problems.length === 0}
		<div class="bpmn-problems__empty">No problems detected.</div>
	{:else}
		<ul class="bpmn-problems__list" role="list">
			{#each problems as p (p.ruleId + ':' + p.elementIds.join(','))}
				<li class="bpmn-problems__item bpmn-problems__item--{p.severity}">
					<button type="button" onclick={() => p.elementIds.length && onfocus?.(p.elementIds)}>
						<span class="bpmn-problems__glyph" aria-hidden="true">{severityGlyph(p.severity)}</span>
						<span class="bpmn-problems__msg">{p.message}</span>
						<span class="bpmn-problems__rule">{p.ruleId}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.bpmn-problems {
		max-height: 200px; min-height: 80px;
		display: flex; flex-direction: column;
		background: var(--color-surface, #ffffff);
		border-top: 1px solid var(--color-border, #e5e7eb);
		font-size: 12px;
	}
	.bpmn-problems__header {
		display: flex; justify-content: space-between; align-items: center;
		padding: 6px 12px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
	}
	.bpmn-problems__title { font-weight: 600; }
	.bpmn-problems__counts { display: flex; gap: 4px; }
	.bpmn-problems__count { padding: 1px 6px; border-radius: 8px; font-size: 11px; min-width: 20px; text-align: center; }
	.bpmn-problems__count--error { background: #FEE2E2; color: #B91C1C; }
	.bpmn-problems__count--warning { background: #FEF3C7; color: #92400E; }
	.bpmn-problems__count--info { background: #DBEAFE; color: #1E40AF; }
	.bpmn-problems__empty { padding: 16px; color: var(--color-muted, #6b7280); text-align: center; }
	.bpmn-problems__list { list-style: none; margin: 0; padding: 0; overflow-y: auto; }
	.bpmn-problems__item button {
		display: grid; grid-template-columns: 20px 1fr auto;
		gap: 8px; align-items: center;
		width: 100%; padding: 6px 12px;
		background: transparent; border: 0; text-align: left; cursor: pointer;
		color: var(--color-fg, #202931);
	}
	.bpmn-problems__item button:hover { background: var(--color-surface-hover, #f3f4f6); }
	.bpmn-problems__item--error button .bpmn-problems__glyph { color: #B91C1C; }
	.bpmn-problems__item--warning button .bpmn-problems__glyph { color: #92400E; }
	.bpmn-problems__item--info button .bpmn-problems__glyph { color: #1E40AF; }
	.bpmn-problems__rule { font-family: monospace; font-size: 10px; opacity: 0.55; }
</style>
