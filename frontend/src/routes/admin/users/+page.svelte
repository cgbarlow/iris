<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { UserDetail } from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	let users = $state<UserDetail[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let roleFilter = $state('');

	// Create user form
	let showCreateForm = $state(false);
	let newUsername = $state('');
	let newPassword = $state('');
	let newRole = $state('viewer');
	let createError = $state<string | null>(null);
	let creating = $state(false);

	// Edit user
	let editingUser = $state<UserDetail | null>(null);
	let editRole = $state('');
	let editError = $state<string | null>(null);
	let saving = $state(false);

	// Deactivation dialog
	let deactivatingUser = $state<UserDetail | null>(null);
	let showDeactivateDialog = $state(false);

	$effect(() => {
		loadUsers();
	});

	async function loadUsers() {
		loading = true;
		error = null;
		try {
			users = await apiFetch<UserDetail[]>('/api/users');
		} catch {
			error = 'Failed to load users';
		}
		loading = false;
	}

	const filteredUsers = $derived(
		users.filter((u) => {
			if (roleFilter && u.role !== roleFilter) return false;
			if (searchQuery) {
				return u.username.toLowerCase().includes(searchQuery.toLowerCase());
			}
			return true;
		}),
	);

	async function createUser() {
		creating = true;
		createError = null;
		try {
			await apiFetch<UserDetail>('/api/users', {
				method: 'POST',
				body: JSON.stringify({
					username: newUsername,
					password: newPassword,
					role: newRole,
				}),
			});
			showCreateForm = false;
			newUsername = '';
			newPassword = '';
			newRole = 'viewer';
			await loadUsers();
		} catch (e) {
			createError = e instanceof ApiError ? e.message : 'Failed to create user';
		}
		creating = false;
	}

	function startEdit(user: UserDetail) {
		editingUser = user;
		editRole = user.role;
		editError = null;
	}

	async function saveEdit() {
		if (!editingUser) return;
		saving = true;
		editError = null;
		try {
			await apiFetch<UserDetail>(`/api/users/${editingUser.id}`, {
				method: 'PUT',
				body: JSON.stringify({ role: editRole }),
			});
			editingUser = null;
			await loadUsers();
		} catch (e) {
			editError = e instanceof ApiError ? e.message : 'Failed to update user';
		}
		saving = false;
	}

	function startDeactivate(user: UserDetail) {
		deactivatingUser = user;
		showDeactivateDialog = true;
	}

	async function confirmDeactivate() {
		if (!deactivatingUser) return;
		try {
			await apiFetch<UserDetail>(`/api/users/${deactivatingUser.id}`, {
				method: 'PUT',
				body: JSON.stringify({ is_active: !deactivatingUser.is_active }),
			});
			showDeactivateDialog = false;
			deactivatingUser = null;
			await loadUsers();
		} catch {
			// ignore, reload to show current state
			await loadUsers();
		}
		showDeactivateDialog = false;
	}

	function cancelDeactivate() {
		showDeactivateDialog = false;
		deactivatingUser = null;
	}
</script>

<svelte:head>
	<title>Users — Iris Admin</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">Users</li>
	</ol>
</nav>

<div class="flex items-center justify-between">
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">User Management</h1>
	<button
		onclick={() => (showCreateForm = !showCreateForm)}
		class="rounded px-4 py-2 text-sm font-medium"
		style="background: var(--color-primary); color: var(--color-bg)"
	>
		{showCreateForm ? 'Cancel' : 'Create User'}
	</button>
</div>

<!-- Create User Form -->
{#if showCreateForm}
	<form
		onsubmit={(e) => { e.preventDefault(); createUser(); }}
		class="mt-4 rounded border p-4"
		style="border-color: var(--color-border); max-width: 400px"
	>
		<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Create New User</h2>
		{#if createError}
			<div role="alert" class="mt-2 text-sm" style="color: var(--color-danger)">{createError}</div>
		{/if}
		<div class="mt-3">
			<label for="new-username" class="block text-sm" style="color: var(--color-fg)">Username</label>
			<input
				id="new-username"
				bind:value={newUsername}
				type="text"
				required
				minlength={3}
				autocomplete="username"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>
		<div class="mt-3">
			<label for="new-password" class="block text-sm" style="color: var(--color-fg)">Password</label>
			<input
				id="new-password"
				bind:value={newPassword}
				type="password"
				required
				minlength={12}
				autocomplete="new-password"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">Minimum 12 characters with uppercase, lowercase, number, and special character.</p>
		</div>
		<div class="mt-3">
			<label for="new-role" class="block text-sm" style="color: var(--color-fg)">Role</label>
			<select
				id="new-role"
				bind:value={newRole}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<option value="viewer">Viewer</option>
				<option value="reviewer">Reviewer</option>
				<option value="architect">Architect</option>
				<option value="admin">Admin</option>
			</select>
		</div>
		<button
			type="submit"
			disabled={creating}
			class="mt-4 rounded px-4 py-2 text-sm font-medium"
			style="background: var(--color-primary); color: var(--color-bg)"
		>
			{creating ? 'Creating...' : 'Create'}
		</button>
	</form>
{/if}

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<div>
		<label for="user-search" class="sr-only">Search users</label>
		<input
			id="user-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search by username..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="role-filter" class="sr-only">Filter by role</label>
		<select
			id="role-filter"
			bind:value={roleFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All roles</option>
			<option value="admin">Admin</option>
			<option value="architect">Architect</option>
			<option value="reviewer">Reviewer</option>
			<option value="viewer">Viewer</option>
		</select>
	</div>
</div>

<!-- Users Table -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading users...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if filteredUsers.length === 0}
		<p style="color: var(--color-muted)">No users found.</p>
	{:else}
		<table class="w-full text-sm">
			<thead>
				<tr style="border-bottom: 1px solid var(--color-border)">
					<th class="py-2 text-left" style="color: var(--color-muted)">Username</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Role</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Status</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Created</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Last Login</th>
					<th class="py-2 text-left" style="color: var(--color-muted)">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each filteredUsers as user}
					<tr style="border-bottom: 1px solid var(--color-border)">
						<td class="py-2 font-medium" style="color: var(--color-fg)">{user.username}</td>
						<td class="py-2">
							{#if editingUser?.id === user.id}
								<select
									bind:value={editRole}
									class="rounded border px-2 py-1 text-xs"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
								>
									<option value="viewer">Viewer</option>
									<option value="reviewer">Reviewer</option>
									<option value="architect">Architect</option>
									<option value="admin">Admin</option>
								</select>
							{:else}
								<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{user.role}</span>
							{/if}
						</td>
						<td class="py-2">
							<span
								class="rounded px-2 py-0.5 text-xs"
								style="color: {user.is_active ? 'var(--color-success)' : 'var(--color-danger)'}"
							>
								{user.is_active ? 'Active' : 'Inactive'}
							</span>
						</td>
						<td class="py-2 text-xs" style="color: var(--color-muted)">{user.created_at?.split('T')[0] ?? '—'}</td>
						<td class="py-2 text-xs" style="color: var(--color-muted)">{user.last_login_at?.split('T')[0] ?? 'Never'}</td>
						<td class="py-2">
							{#if editingUser?.id === user.id}
								<div class="flex gap-1">
									<button
										onclick={saveEdit}
										disabled={saving}
										class="rounded px-2 py-1 text-xs"
										style="background: var(--color-primary); color: var(--color-bg)"
									>
										Save
									</button>
									<button
										onclick={() => (editingUser = null)}
										class="rounded px-2 py-1 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-fg)"
									>
										Cancel
									</button>
								</div>
								{#if editError}
									<p class="mt-1 text-xs" style="color: var(--color-danger)">{editError}</p>
								{/if}
							{:else}
								<div class="flex gap-1">
									<button
										onclick={() => startEdit(user)}
										class="rounded px-2 py-1 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-primary)"
									>
										Edit
									</button>
									<button
										onclick={() => startDeactivate(user)}
										class="rounded px-2 py-1 text-xs"
										style="border: 1px solid var(--color-border); color: {user.is_active ? 'var(--color-danger)' : 'var(--color-success)'}"
									>
										{user.is_active ? 'Deactivate' : 'Activate'}
									</button>
								</div>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

{#if deactivatingUser}
	<ConfirmDialog
		open={showDeactivateDialog}
		title="{deactivatingUser.is_active ? 'Deactivate' : 'Activate'} User"
		message="Are you sure you want to {deactivatingUser.is_active ? 'deactivate' : 'activate'} {deactivatingUser.username}?"
		confirmLabel={deactivatingUser.is_active ? 'Deactivate' : 'Activate'}
		onconfirm={confirmDeactivate}
		oncancel={cancelDeactivate}
	/>
{/if}
