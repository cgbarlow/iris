<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>Model Detail — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">{page.params.id}</li>
	</ol>
</nav>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Model Detail</h1>
<p class="mt-2" style="color: var(--color-muted)">Model ID: {page.params.id}</p>
