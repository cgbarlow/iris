<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>Page Not Found — Iris</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center p-4">
	<div class="text-center">
		<h1 class="text-6xl font-bold" style="color: var(--color-muted)">{page.status}</h1>
		<p class="mt-4 text-xl" style="color: var(--color-fg)">{page.error?.message}</p>
		<a
			href="/"
			class="mt-6 inline-block rounded px-4 py-2 font-medium text-white"
			style="background-color: var(--color-primary)"
		>
			Go home
		</a>
	</div>
</main>
