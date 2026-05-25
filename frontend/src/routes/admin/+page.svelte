<svelte:head>
	<title>Admin — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Administration</h1>
<p class="mt-1 text-sm" style="color: var(--color-muted)">System administration and monitoring.</p>

<div class="mt-6 grid grid-cols-2 gap-4" style="max-width: 750px">
	<a
		href="/admin/users"
		class="rounded border p-6 text-center"
		style="border-color: var(--color-border); color: var(--color-fg)"
	>
		<div class="text-lg font-semibold" style="color: var(--color-primary)">User Management</div>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Manage user accounts, roles, and access.</p>
	</a>
	<a
		href="/admin/audit"
		class="rounded border p-6 text-center"
		style="border-color: var(--color-border); color: var(--color-fg)"
	>
		<div class="text-lg font-semibold" style="color: var(--color-primary)">Audit Log</div>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">View system audit trail and verify chain integrity.</p>
	</a>
	<a
		href="/admin/settings"
		class="rounded border p-6 text-center"
		style="border-color: var(--color-border); color: var(--color-fg)"
	>
		<div class="text-lg font-semibold" style="color: var(--color-primary)">Settings</div>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Configure session timeout, themes, AI providers, and extensions.</p>
	</a>
	<a
		href="/admin/settings/aggregation-profiles"
		class="rounded border p-6 text-center"
		style="border-color: var(--color-border); color: var(--color-fg)"
	>
		<div class="text-lg font-semibold" style="color: var(--color-primary)">Aggregation profiles</div>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Manage global aggregation profiles — rulesets that roll up data across many documents (summed quantities, points totals, time-tracking, expenses, and so on).</p>
	</a>
</div>
