/**
 * ADR-253: how far out every canvas can zoom. Svelte Flow's default
 * minZoom of 0.5 also caps `fitView`, so large diagrams (a 274-node
 * family tree) opened at 50% with most of the diagram off screen.
 * 0.05 fits a diagram roughly 20 viewports across.
 */
export const CANVAS_MIN_ZOOM = 0.05;
