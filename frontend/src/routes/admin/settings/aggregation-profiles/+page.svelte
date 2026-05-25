<script lang="ts">
	/**
	 * Admin → Aggregation profiles (v6.25.0, SPEC-212-d).
	 *
	 * Manage global aggregation profiles. Set-scoped profiles are
	 * managed on the set edit page.
	 */
	import AggregationProfileEditor from '$lib/components/AggregationProfileEditor.svelte';
</script>

<svelte:head>
	<title>Aggregation Profiles — Iris Admin</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex items-baseline gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li><span aria-hidden="true">/</span></li>
		<li aria-current="page">Aggregation profiles</li>
	</ol>
</nav>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Aggregation profiles</h1>
<p class="mt-1 text-sm" style="color: var(--color-muted)">
	Global aggregation profiles available across all sets (ADR-212). For set-scoped profiles, edit the set directly.
</p>

<div class="mt-6" style="max-width: 1024px">
	<AggregationProfileEditor globalsMode={true} />
</div>
