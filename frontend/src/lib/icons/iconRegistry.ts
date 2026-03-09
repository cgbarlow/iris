/**
 * Central icon registry (ADR-091-B).
 *
 * Maps IconRef → Lucide icon component. Supports multiple icon sets
 * with lazy resolution.
 */

import type { IconRef } from '$lib/types/canvas';
import * as lucideIcons from 'lucide-svelte';
import type { Component } from 'svelte';

/**
 * Convert kebab-case icon name to PascalCase component name.
 * e.g. "bar-chart-3" → "BarChart3"
 */
function toPascalCase(name: string): string {
	return name
		.split('-')
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join('');
}

/**
 * Convert PascalCase component name to kebab-case icon name.
 * e.g. "BarChart3" → "bar-chart-3"
 */
function toKebabCase(name: string): string {
	return name
		.replace(/([a-z0-9])([A-Z])/g, '$1-$2')
		.replace(/([A-Z]+)([A-Z][a-z])/g, '$1-$2')
		.toLowerCase();
}

/** Non-component exports to exclude from the icon list. */
const NON_ICON_EXPORTS = new Set([
	'default',
	'icons',
	'defaultAttributes',
	'Icon',
	'createIcons',
]);

/** All available Lucide icon names (kebab-case), lazily computed. */
let _allIconNames: string[] | null = null;

export function getAllLucideIconNames(): string[] {
	if (!_allIconNames) {
		_allIconNames = Object.keys(lucideIcons as Record<string, unknown>)
			.filter(
				(key) =>
					!NON_ICON_EXPORTS.has(key) &&
					key[0] === key[0].toUpperCase() &&
					typeof (lucideIcons as Record<string, unknown>)[key] !== 'string',
			)
			.map(toKebabCase)
			.sort();
	}
	return _allIconNames;
}

/**
 * Resolve an IconRef to its Svelte component.
 * Returns undefined if the icon is not found in the registry.
 */
export function resolveIcon(ref: IconRef): Component | undefined {
	if (ref.set === 'lucide') {
		const componentName = toPascalCase(ref.name);
		const icon = (lucideIcons as Record<string, unknown>)[componentName];
		if (typeof icon === 'function' || (typeof icon === 'object' && icon !== null)) {
			return icon as Component;
		}
		return undefined;
	}
	// Future: archimate, custom sets
	return undefined;
}

/**
 * Check if an IconRef resolves to a valid icon component.
 */
export function isValidIcon(ref: IconRef): boolean {
	return resolveIcon(ref) !== undefined;
}
