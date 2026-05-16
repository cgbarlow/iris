<!--
  Unified diagram export menu (ADR-181, v6.5.0).

  Server-rendered Markdown / Docx / PDF via the Phase 2 endpoints +
  client-rasterised SVG / PNG (retained from the pre-v6.5.0 inline
  menu) when a flow element is provided.

  Replaces the inline Export dropdown in
  frontend/src/routes/views/[id]/+page.svelte (lines 2459-2482 and
  2781-2789 pre-v6.5.0).
-->
<script lang="ts">
	import { exportToPng, exportToSvg } from '$lib/utils/export';

	interface Props {
		diagramId: string;
		diagramName: string;
		isMarkdownContent?: boolean;
		/** Returns the current `.svelte-flow` HTMLElement, or null if no canvas. */
		flowElement?: () => HTMLElement | null;
	}

	let {
		diagramId,
		diagramName,
		isMarkdownContent = false,
		flowElement,
	}: Props = $props();

	let open = $state(false);
	let busy = $state<string | null>(null);
	let errorMsg = $state<string | null>(null);

	const showVisualOptions = $derived(!isMarkdownContent && flowElement !== undefined);

	async function renderServerSide(format: 'md' | 'docx' | 'pdf') {
		busy = format;
		errorMsg = null;
		try {
			const resp = await fetch(`/api/export/diagram/${diagramId}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ format }),
				credentials: 'include',
			});
			if (!resp.ok) {
				const detail = await resp.text();
				throw new Error(
					`Render failed (${resp.status}): ${detail.slice(0, 200)}`,
				);
			}
			const meta = (await resp.json()) as { id: string; filename: string };
			// Browser-native download via Content-Disposition: attachment.
			const a = document.createElement('a');
			a.href = `/api/artefacts/${meta.id}`;
			a.download = meta.filename;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			open = false;
		} catch (err) {
			errorMsg = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}

	async function captureClientSide(kind: 'svg' | 'png') {
		if (!flowElement) return;
		const el = flowElement();
		if (!el) {
			errorMsg = 'No canvas element to capture.';
			return;
		}
		busy = kind;
		errorMsg = null;
		try {
			if (kind === 'svg') {
				await exportToSvg(el, diagramName);
			} else {
				await exportToPng(el, diagramName);
			}
			open = false;
		} catch (err) {
			errorMsg = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}
</script>

<div class="relative">
	<button
		onclick={() => (open = !open)}
		class="rounded px-3 py-1.5 text-sm"
		style="border: 1px solid var(--color-border); color: var(--color-fg)"
		aria-haspopup="true"
		aria-expanded={open}
		data-testid="diagram-export-menu-trigger"
	>
		Export
	</button>
	{#if open}
		<div
			class="absolute right-0 z-50 mt-1 min-w-[180px] rounded border py-1 shadow-lg"
			style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
			role="menu"
			data-testid="diagram-export-menu"
		>
			<!-- Server-rendered text artefacts — always available. -->
			<button
				onclick={() => renderServerSide('md')}
				disabled={busy !== null}
				class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80 disabled:opacity-50"
				style="color: var(--color-fg)"
				role="menuitem"
				data-testid="export-md"
			>
				Markdown{busy === 'md' ? '…' : ''}
			</button>
			<button
				onclick={() => renderServerSide('docx')}
				disabled={busy !== null}
				class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80 disabled:opacity-50"
				style="color: var(--color-fg)"
				role="menuitem"
				data-testid="export-docx"
			>
				Word document (.docx){busy === 'docx' ? '…' : ''}
			</button>
			<button
				onclick={() => renderServerSide('pdf')}
				disabled={busy !== null}
				class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80 disabled:opacity-50"
				style="color: var(--color-fg)"
				role="menuitem"
				data-testid="export-pdf"
			>
				PDF (.pdf){busy === 'pdf' ? '…' : ''}
			</button>

			{#if showVisualOptions}
				<!-- Client-rasterised options — visual diagrams only. -->
				<div
					class="my-1 border-t"
					style="border-color: var(--color-border)"
				></div>
				<button
					onclick={() => captureClientSide('svg')}
					disabled={busy !== null}
					class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80 disabled:opacity-50"
					style="color: var(--color-fg)"
					role="menuitem"
					data-testid="export-svg"
				>
					SVG (canvas){busy === 'svg' ? '…' : ''}
				</button>
				<button
					onclick={() => captureClientSide('png')}
					disabled={busy !== null}
					class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80 disabled:opacity-50"
					style="color: var(--color-fg)"
					role="menuitem"
					data-testid="export-png"
				>
					PNG (canvas){busy === 'png' ? '…' : ''}
				</button>
			{/if}

			<div
				class="my-1 border-t"
				style="border-color: var(--color-border)"
			></div>
			<button
				disabled
				title="Coming soon"
				class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50"
				style="color: var(--color-fg)"
				role="menuitem"
			>
				Visio
			</button>
			<button
				disabled
				title="Coming soon"
				class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50"
				style="color: var(--color-fg)"
				role="menuitem"
			>
				Draw.io
			</button>

			{#if errorMsg}
				<div
					class="border-t px-4 py-1.5 text-xs"
					style="border-color: var(--color-border); color: #b91c1c"
					role="alert"
				>
					{errorMsg}
				</div>
			{/if}
		</div>
	{/if}
</div>
