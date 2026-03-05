/** Lock manager composable for edit locking (ADR-080). */
import { apiFetch } from '$lib/utils/api';
import { beforeNavigate } from '$app/navigation';
import type { LockCheckResponse, EditLock } from '$lib/types/api';

const HEARTBEAT_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export interface LockManager {
	readonly lockId: string | null;
	readonly isLocked: boolean;
	readonly lockHolder: string | null;
	readonly isOwner: boolean;
	checkLock(): Promise<void>;
	acquireLock(): Promise<boolean>;
	releaseLock(): Promise<void>;
	startHeartbeat(): void;
	stopHeartbeat(): void;
	destroy(): void;
}

export function createLockManager(targetType: string, targetId: string): LockManager {
	let lockId = $state<string | null>(null);
	let isLocked = $state(false);
	let lockHolder = $state<string | null>(null);
	let isOwner = $state(false);
	let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

	function handleBeforeUnload() {
		if (lockId && isOwner) {
			// Fire-and-forget release on page close
			navigator.sendBeacon(`/api/locks/${lockId}/release`, '');
		}
	}

	async function checkLock(): Promise<void> {
		try {
			const data = await apiFetch<LockCheckResponse>(
				`/api/locks/check?target_type=${targetType}&target_id=${targetId}`
			);
			isLocked = data.locked;
			isOwner = data.is_owner;
			lockHolder = data.lock?.username ?? null;
			if (data.is_owner && data.lock) {
				lockId = data.lock.id;
			}
		} catch {
			isLocked = false;
			isOwner = false;
			lockHolder = null;
		}
	}

	async function acquireLock(): Promise<boolean> {
		try {
			const response = await apiFetch<EditLock>('/api/locks', {
				method: 'POST',
				body: JSON.stringify({
					target_type: targetType,
					target_id: targetId,
				}),
			});
			lockId = response.id;
			isLocked = true;
			isOwner = true;
			lockHolder = response.username;
			startHeartbeat();
			window.addEventListener('beforeunload', handleBeforeUnload);
			return true;
		} catch {
			// 409 Conflict — someone else holds the lock
			await checkLock();
			return false;
		}
	}

	async function releaseLock(): Promise<void> {
		if (!lockId) return;
		stopHeartbeat();
		window.removeEventListener('beforeunload', handleBeforeUnload);
		try {
			await apiFetch(`/api/locks/${lockId}`, { method: 'DELETE' });
		} catch {
			// Lock may already be expired
		}
		lockId = null;
		isLocked = false;
		isOwner = false;
		lockHolder = null;
	}

	function startHeartbeat(): void {
		stopHeartbeat();
		heartbeatTimer = setInterval(async () => {
			if (!lockId) return;
			try {
				await apiFetch(`/api/locks/${lockId}/heartbeat`, { method: 'PUT' });
			} catch {
				// Lock expired
				stopHeartbeat();
				lockId = null;
				isLocked = false;
				isOwner = false;
			}
		}, HEARTBEAT_INTERVAL_MS);
	}

	function stopHeartbeat(): void {
		if (heartbeatTimer) {
			clearInterval(heartbeatTimer);
			heartbeatTimer = null;
		}
	}

	function destroy(): void {
		stopHeartbeat();
		window.removeEventListener('beforeunload', handleBeforeUnload);
	}

	return {
		get lockId() { return lockId; },
		get isLocked() { return isLocked; },
		get lockHolder() { return lockHolder; },
		get isOwner() { return isOwner; },
		checkLock,
		acquireLock,
		releaseLock,
		startHeartbeat,
		stopHeartbeat,
		destroy,
	};
}
