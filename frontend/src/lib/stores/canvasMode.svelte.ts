/** Canvas mode store — controls whether the canvas is in edit or browse mode. */

export type CanvasMode = 'edit' | 'browse';

let currentMode = $state<CanvasMode>('browse');

/** Get the current canvas mode. */
export function getCanvasMode(): CanvasMode {
	return currentMode;
}

/** Set the canvas mode. */
export function setCanvasMode(mode: CanvasMode): void {
	currentMode = mode;
}

/** Check if the canvas is in edit mode. */
export function isEditMode(): boolean {
	return currentMode === 'edit';
}

/** Check if the canvas is in browse (read-only) mode. */
export function isBrowseMode(): boolean {
	return currentMode === 'browse';
}
