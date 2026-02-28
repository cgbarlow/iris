/** Svelte 5 runes module for sequence diagram viewport (zoom/pan) via SVG viewBox. */

const ZOOM_STEP = 0.2;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4;
const PAN_SPEED = 40;

export interface SequenceViewport {
	readonly viewBox: string;
	readonly zoom: number;
	zoomIn: () => void;
	zoomOut: () => void;
	fitView: () => void;
	handleWheel: (e: WheelEvent) => void;
	handlePointerDown: (e: PointerEvent) => void;
	handlePointerMove: (e: PointerEvent) => void;
	handlePointerUp: (e: PointerEvent) => void;
}

export function createSequenceViewport(contentWidth: number, contentHeight: number): SequenceViewport {
	let zoom = $state(1);
	let panX = $state(0);
	let panY = $state(0);
	let dragging = $state(false);
	let lastX = 0;
	let lastY = 0;

	const viewBox = $derived(
		`${panX} ${panY} ${contentWidth / zoom} ${contentHeight / zoom}`,
	);

	function zoomIn() {
		zoom = Math.min(ZOOM_MAX, zoom + ZOOM_STEP);
	}

	function zoomOut() {
		zoom = Math.max(ZOOM_MIN, zoom - ZOOM_STEP);
	}

	function fitView() {
		zoom = 1;
		panX = 0;
		panY = 0;
	}

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		if (e.ctrlKey || e.metaKey) {
			// Ctrl+wheel = zoom
			if (e.deltaY < 0) {
				zoomIn();
			} else {
				zoomOut();
			}
		} else {
			// Plain wheel = pan
			panY += (e.deltaY / zoom) * 0.5;
			panX += (e.deltaX / zoom) * 0.5;
		}
	}

	function handlePointerDown(e: PointerEvent) {
		// Middle button or Shift+left button = drag pan
		if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
			e.preventDefault();
			dragging = true;
			lastX = e.clientX;
			lastY = e.clientY;
			(e.target as Element)?.setPointerCapture?.(e.pointerId);
		}
	}

	function handlePointerMove(e: PointerEvent) {
		if (!dragging) return;
		const dx = e.clientX - lastX;
		const dy = e.clientY - lastY;
		panX -= dx / zoom;
		panY -= dy / zoom;
		lastX = e.clientX;
		lastY = e.clientY;
	}

	function handlePointerUp(e: PointerEvent) {
		if (dragging) {
			dragging = false;
			(e.target as Element)?.releasePointerCapture?.(e.pointerId);
		}
	}

	return {
		get viewBox() {
			return viewBox;
		},
		get zoom() {
			return zoom;
		},
		zoomIn,
		zoomOut,
		fitView,
		handleWheel,
		handlePointerDown,
		handlePointerMove,
		handlePointerUp,
	};
}
