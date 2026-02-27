<svelte:head>
	<title>Help — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Help</h1>
<p class="mt-2" style="color: var(--color-muted)">
	Iris is an architectural modelling tool for managing entities, relationships, and models.
</p>

<section class="mt-6">
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Keyboard Shortcuts</h2>
	<dl class="mt-3 grid gap-2" style="grid-template-columns: auto 1fr">
		<dt class="font-mono text-sm" style="color: var(--color-muted)">Tab / Shift+Tab</dt>
		<dd style="color: var(--color-fg)">Navigate between canvas entities</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Arrow keys</dt>
		<dd style="color: var(--color-fg)">Move selected entity (Shift for larger steps)</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Ctrl+N</dt>
		<dd style="color: var(--color-fg)">Create a new entity</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">C</dt>
		<dd style="color: var(--color-fg)">Toggle connect mode to draw relationships</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Delete</dt>
		<dd style="color: var(--color-fg)">Delete selected entity</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Escape</dt>
		<dd style="color: var(--color-fg)">Deselect or cancel current operation</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Ctrl+=  /  Ctrl+-</dt>
		<dd style="color: var(--color-fg)">Zoom in / out</dd>

		<dt class="font-mono text-sm" style="color: var(--color-muted)">Ctrl+0</dt>
		<dd style="color: var(--color-fg)">Fit canvas to screen</dd>
	</dl>
</section>

<section class="mt-6">
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Navigation</h2>
	<ul class="mt-2 list-inside list-disc" style="color: var(--color-fg)">
		<li><a href="/models" style="color: var(--color-primary)">Models</a> — Browse and manage architectural models</li>
		<li><a href="/entities" style="color: var(--color-primary)">Entities</a> — Browse and manage architectural entities</li>
	</ul>
</section>

<section class="mt-6">
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Accessibility</h2>
	<p class="mt-2" style="color: var(--color-fg)">
		Iris is designed to meet WCAG 2.2 Level AA standards. All canvas operations are available
		via keyboard. Use the theme toggle in the header to switch between light, dark, and
		high-contrast modes.
	</p>
</section>
