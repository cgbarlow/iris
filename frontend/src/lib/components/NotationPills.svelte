<script lang="ts">
  interface Props {
    value: string;
    onchange: (notation: string) => void;
    /** Restrict the visible pills (default: all). EntityDialog excludes 'markdown' since text views have no entities. */
    notations?: string[];
  }

  let { value, onchange, notations }: Props = $props();

  const ALL_NOTATIONS = [
    { key: 'simple', label: 'Simple' },
    { key: 'uml', label: 'UML' },
    { key: 'archimate', label: 'ArchiMate' },
    { key: 'c4', label: 'C4' },
    { key: 'bpmn', label: 'BPMN' },
    { key: 'doview', label: 'DoView' },
    { key: 'markdown', label: 'Markdown' },
  ];

  const visible = $derived(
    notations && notations.length > 0
      ? ALL_NOTATIONS.filter((n) => notations.includes(n.key))
      : ALL_NOTATIONS
  );
</script>

<div class="flex flex-wrap gap-2" role="radiogroup" aria-label="Notation">
  {#each visible as n}
    <button
      type="button"
      role="radio"
      aria-checked={value === n.key}
      class="rounded-full px-3 py-1 text-sm font-medium transition-colors"
      style={value === n.key
        ? 'background: var(--color-primary); color: #fff; border: 1px solid var(--color-primary)'
        : 'background: transparent; border: 1px solid var(--color-border); color: var(--color-fg)'}
      onclick={() => onchange(n.key)}
    >
      {n.label}
    </button>
  {/each}
</div>
