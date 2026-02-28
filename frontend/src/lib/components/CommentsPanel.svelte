<script lang="ts">
	/**
	 * Comments panel for model and entity detail pages.
	 * Supports viewing, adding, editing, and deleting comments.
	 */
	import DOMPurify from 'dompurify';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Comment } from '$lib/types/api';

	interface Props {
		targetType: 'model' | 'entity';
		targetId: string;
	}

	let { targetType, targetId }: Props = $props();

	let comments = $state<Comment[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let newComment = $state('');
	let submitting = $state(false);
	let editingId = $state<string | null>(null);
	let editContent = $state('');

	$effect(() => {
		if (targetId) loadComments();
	});

	async function loadComments() {
		loading = true;
		error = null;
		try {
			comments = await apiFetch<Comment[]>(
				`/api/comments?target_type=${targetType}&target_id=${targetId}`,
			);
		} catch {
			error = 'Failed to load comments';
			comments = [];
		}
		loading = false;
	}

	async function handleAdd(event: SubmitEvent) {
		event.preventDefault();
		const sanitized = DOMPurify.sanitize(newComment.trim());
		if (!sanitized) return;

		submitting = true;
		error = null;
		try {
			await apiFetch('/api/comments', {
				method: 'POST',
				body: JSON.stringify({
					target_type: targetType,
					target_id: targetId,
					content: sanitized,
				}),
			});
			newComment = '';
			await loadComments();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to add comment';
		}
		submitting = false;
	}

	function startEdit(comment: Comment) {
		editingId = comment.id;
		editContent = comment.content;
	}

	function cancelEdit() {
		editingId = null;
		editContent = '';
	}

	async function handleEdit(commentId: string) {
		const sanitized = DOMPurify.sanitize(editContent.trim());
		if (!sanitized) return;

		error = null;
		try {
			await apiFetch(`/api/comments/${commentId}`, {
				method: 'PUT',
				body: JSON.stringify({ content: sanitized }),
			});
			editingId = null;
			editContent = '';
			await loadComments();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update comment';
		}
	}

	async function handleDelete(commentId: string) {
		error = null;
		try {
			await apiFetch(`/api/comments/${commentId}`, { method: 'DELETE' });
			await loadComments();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete comment';
		}
	}
</script>

<div class="comments-panel">
	<h3 class="text-base font-semibold" style="color: var(--color-fg)">Comments</h3>

	{#if error}
		<div role="alert" class="mt-2 rounded border p-2 text-sm" style="border-color: var(--color-danger); color: var(--color-danger)">
			{error}
		</div>
	{/if}

	{#if loading}
		<p class="mt-3 text-sm" style="color: var(--color-muted)">Loading comments...</p>
	{:else}
		{#if comments.length === 0}
			<p class="mt-3 text-sm" style="color: var(--color-muted)">No comments yet.</p>
		{:else}
			<ul class="mt-3 flex flex-col gap-3">
				{#each comments as comment}
					<li
						class="rounded border p-3"
						style="border-color: var(--color-border)"
					>
						{#if editingId === comment.id}
							<div class="flex flex-col gap-2">
								<textarea
									bind:value={editContent}
									rows="2"
									class="w-full rounded border px-3 py-2 text-sm"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
								></textarea>
								<div class="flex gap-2">
									<button
										onclick={() => handleEdit(comment.id)}
										class="rounded px-3 py-1 text-xs text-white"
										style="background-color: var(--color-primary)"
									>
										Save
									</button>
									<button
										onclick={cancelEdit}
										class="rounded px-3 py-1 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-fg)"
									>
										Cancel
									</button>
								</div>
							</div>
						{:else}
							<p class="text-sm" style="color: var(--color-fg)">{comment.content}</p>
							<div class="mt-2 flex items-center gap-3">
								<span class="text-xs" style="color: var(--color-muted)">
									{comment.created_at}
								</span>
								<button
									onclick={() => startEdit(comment)}
									class="text-xs"
									style="color: var(--color-primary)"
								>
									Edit
								</button>
								<button
									onclick={() => handleDelete(comment.id)}
									class="text-xs"
									style="color: var(--color-danger)"
								>
									Delete
								</button>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}

		<!-- Add comment form -->
		<form onsubmit={handleAdd} class="mt-4 flex flex-col gap-2">
			<label for="new-comment" class="text-sm font-medium" style="color: var(--color-fg)">Add a comment</label>
			<textarea
				id="new-comment"
				bind:value={newComment}
				rows="2"
				required
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			></textarea>
			<button
				type="submit"
				disabled={submitting || !newComment.trim()}
				class="self-start rounded px-4 py-1.5 text-sm text-white disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{submitting ? 'Posting...' : 'Post Comment'}
			</button>
		</form>
	{/if}
</div>
