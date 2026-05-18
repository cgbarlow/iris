<script lang="ts">
	import type { GraphSettings } from '$lib/types/api';
	import { NODE_TYPE_LABELS, getNodeTypeColor } from '$lib/utils/graphColors';

	interface Props {
		settings: GraphSettings;
		onchange: (settings: GraphSettings) => void;
		isAdmin?: boolean;
		onSaveDefault?: (settings: GraphSettings) => void | Promise<void>;
		onResetToDefaults?: (tab: 'nodes' | 'relationships' | 'display') => void;
	}

	let { settings, onchange, isAdmin = false, onSaveDefault, onResetToDefaults }: Props = $props();

	// Issue #173 item 4: split former 'visibility' tab into 'nodes' and
	// 'relationships' so node-type and relationship-type toggles each
	// own their own column. Default opens on 'nodes' (preserves the
	// "first thing you see" behaviour).
	let activeTab = $state<'nodes' | 'relationships' | 'display'>('nodes');

	const EDGE_GROUPS: { label: string; items: { key: string; label: string }[] }[] = [
		{
			label: 'Containment',
			items: [
				{ key: 'collection_membership', label: 'Collection \u2192 Sets' },
				{ key: 'set_membership', label: 'Set \u2192 Contents' },
				{ key: 'direct_diagram_links', label: 'Direct diagram links' },
			],
		},
		{
			label: 'Package',
			items: [
				{ key: 'hierarchy', label: 'Nesting' },
				{ key: 'package_relationship', label: 'Relationships' },
				// Issue #173 item 5: elements belonging to packages get
				// their own toggle here so users can hide membership
				// edges without losing package-to-package relationships.
				{ key: 'element_package', label: 'Elements (membership)' },
			],
		},
		{
			label: 'Diagram',
			items: [
				{ key: 'diagram_element', label: 'Elements' },
				{ key: 'diagram_package', label: 'References' },
				{ key: 'diagram_link', label: 'Navigation' },
			],
		},
		{
			label: 'Element',
			items: [
				{ key: 'element_relationship', label: 'Relationships' },
			],
		},
	];

	function toggleNode(key: string) {
		const updated = { ...settings, nodes: { ...settings.nodes, [key]: !settings.nodes[key] } };
		onchange(updated);
	}

	function toggleEdge(key: string) {
		const updated = { ...settings, edges: { ...settings.edges, [key]: !settings.edges[key] } };
		onchange(updated);
	}

	function updateSetting(key: string, value: number) {
		const updated = { ...settings, [key]: value };
		onchange(updated);
	}

	function toggleGroup(group: { items: { key: string }[] }) {
		const allOn = group.items.every((i) => settings.edges[i.key] !== false);
		const newEdges = { ...settings.edges };
		for (const item of group.items) {
			newEdges[item.key] = !allOn;
		}
		onchange({ ...settings, edges: newEdges });
	}
</script>

<div
	style="position: absolute; top: 100%; right: 0; z-index: 20; margin-top: 4px; min-width: 220px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-surface); box-shadow: 0 4px 16px rgba(0,0,0,0.18); padding: 0"
>
	<!-- Tabs (issue #173 item 4: Nodes / Relationships / Display) -->
	<div class="flex" style="border-bottom: 1px solid var(--color-border)">
		<button
			onclick={() => (activeTab = 'nodes')}
			class="flex-1 px-3 py-2 text-xs font-medium"
			style="color: {activeTab === 'nodes' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'nodes' ? 'var(--color-primary)' : 'transparent'}; background: none; border-top: none; border-left: none; border-right: none; cursor: pointer; margin-bottom: -1px"
		>Nodes</button>
		<button
			onclick={() => (activeTab = 'relationships')}
			class="flex-1 px-3 py-2 text-xs font-medium"
			style="color: {activeTab === 'relationships' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'relationships' ? 'var(--color-primary)' : 'transparent'}; background: none; border-top: none; border-left: none; border-right: none; cursor: pointer; margin-bottom: -1px"
		>Relationships</button>
		<button
			onclick={() => (activeTab = 'display')}
			class="flex-1 px-3 py-2 text-xs font-medium"
			style="color: {activeTab === 'display' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'display' ? 'var(--color-primary)' : 'transparent'}; background: none; border-top: none; border-left: none; border-right: none; cursor: pointer; margin-bottom: -1px"
		>Display</button>
	</div>

	<div style="padding: 12px">
		{#if activeTab === 'nodes'}
			<!-- Node Types -->
			<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Node Types</h4>
			{#each Object.entries(NODE_TYPE_LABELS) as [key, label]}
				<label class="mb-1 flex cursor-pointer items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input type="checkbox" checked={settings.nodes[key]} onchange={() => toggleNode(key)} />
					<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {getNodeTypeColor(key)}"></span>
					{label}
				</label>
			{/each}
		{:else if activeTab === 'relationships'}
			<!-- Relationship Types -->
			<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Relationship Types</h4>
			{#each EDGE_GROUPS as group}
				{@const allOn = group.items.every((i) => settings.edges[i.key] !== false)}
				{@const someOn = group.items.some((i) => settings.edges[i.key] !== false)}
				<label class="mb-0.5 flex cursor-pointer items-center gap-2 text-sm font-medium" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={allOn}
						indeterminate={!allOn && someOn}
						onchange={() => toggleGroup(group)}
					/>
					{group.label}
				</label>
				{#each group.items as item}
					<label class="mb-0.5 flex cursor-pointer items-center gap-2 text-sm" style="color: var(--color-fg); padding-left: 20px">
						<input type="checkbox" checked={settings.edges[item.key] !== false} onchange={() => toggleEdge(item.key)} />
						{item.label}
					</label>
				{/each}
			{/each}
		{:else}
			<!-- Display Settings -->
			<label class="mb-3 flex cursor-pointer items-center justify-between gap-2 text-sm" style="color: var(--color-fg)">
				Label density
				<input type="number" min="1" max="50" value={settings.label_density ?? 10}
					onchange={(e) => updateSetting('label_density', parseInt(e.currentTarget.value) || 10)}
					style="width: 50px; padding: 2px 4px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); color: var(--color-fg); text-align: center; font-size: 0.75rem" />
			</label>
			<label class="mb-3 flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
				<span class="flex justify-between"><span>Spread</span><span style="color: var(--color-muted)">{(settings.node_spacing ?? 1.0).toFixed(2)}x</span></span>
				<input type="range" min="0.2" max="3" step="0.01" value={settings.node_spacing ?? 1.0}
					oninput={(e) => { const v = parseFloat(e.currentTarget.value); onchange({ ...settings, node_spacing: v, link_length: v }); }}
					style="width: 100%; accent-color: var(--color-primary)" />
			</label>
			<label class="mb-3 flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
				<span class="flex justify-between"><span>Size contrast</span><span style="color: var(--color-muted)">{(settings.size_contrast ?? 1.0).toFixed(2)}x</span></span>
				<input type="range" min="0" max="3" step="0.01" value={settings.size_contrast ?? 1.0}
					oninput={(e) => updateSetting('size_contrast', parseFloat(e.currentTarget.value))}
					style="width: 100%; accent-color: var(--color-primary)" />
			</label>
		{/if}

		<!-- Action buttons (always visible) -->
		{#if onResetToDefaults || (isAdmin && onSaveDefault)}
			<hr class="my-2" style="border-color: var(--color-border)" />
			<div class="flex gap-2">
				{#if onResetToDefaults}
					<button
						onclick={() => onResetToDefaults(activeTab)}
						style="flex: 1; padding: 4px 8px; border-radius: 4px; border: 1px solid var(--color-border); background: var(--color-surface); color: var(--color-muted); font-size: 0.7rem; cursor: pointer"
					>Reset</button>
				{/if}
				{#if isAdmin && onSaveDefault}
					<button
						onclick={async (e) => {
							const btn = e.currentTarget as HTMLButtonElement;
							const original = 'Save as default';
							const origBg = btn.style.background;
							const origBorder = btn.style.borderColor;
							try {
								await onSaveDefault(settings);
								btn.textContent = 'Saved';
								setTimeout(() => { btn.textContent = original; }, 1500);
							} catch (err) {
								// v5.7.2: surface save failures so the admin sees them.
								// Previously the error was swallowed and the button
								// always showed "Saved", masking PUT failures.
								const message = err instanceof Error ? err.message : String(err);
								btn.textContent = 'Save failed';
								btn.style.background = 'var(--color-danger, #dc2626)';
								btn.style.borderColor = 'var(--color-danger, #dc2626)';
								btn.title = message;
								console.error('Save as default failed:', err);
								setTimeout(() => {
									btn.textContent = original;
									btn.style.background = origBg;
									btn.style.borderColor = origBorder;
									btn.title = '';
								}, 4000);
							}
						}}
						style="flex: 1; padding: 4px 8px; border-radius: 4px; border: 1px solid var(--color-primary); background: var(--color-primary); color: white; font-size: 0.7rem; cursor: pointer"
					>Save as default</button>
				{/if}
			</div>
		{/if}
	</div>
</div>
