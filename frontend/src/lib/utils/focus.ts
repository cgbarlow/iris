/** Focus management utilities for accessibility. */

/** Move focus to an element by ID. */
export function focusElement(id: string): void {
	const el = document.getElementById(id);
	if (el) {
		el.focus();
	}
}

/** Move focus to the main content area. */
export function focusMain(): void {
	focusElement('main-content');
}

/**
 * Trap focus within a container element.
 * Returns a cleanup function to remove the trap.
 */
export function trapFocus(container: HTMLElement): () => void {
	const focusable = container.querySelectorAll<HTMLElement>(
		'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
	);

	const first = focusable[0];
	const last = focusable[focusable.length - 1];

	function handleKeydown(event: KeyboardEvent) {
		if (event.key !== 'Tab') return;

		if (event.shiftKey) {
			if (document.activeElement === first) {
				event.preventDefault();
				last?.focus();
			}
		} else {
			if (document.activeElement === last) {
				event.preventDefault();
				first?.focus();
			}
		}
	}

	container.addEventListener('keydown', handleKeydown);
	first?.focus();

	return () => {
		container.removeEventListener('keydown', handleKeydown);
	};
}
