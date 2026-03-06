/**
 * Global theme store — manages visual themes per notation.
 * Themes control element/edge colours, stereotype overrides, and global defaults.
 * Style cascade: per-element visual > stereotype override > element type default > global default > renderer hardcoded.
 */

import { apiFetch } from '$lib/utils/api';
import type { NodeVisualOverrides, EdgeVisualOverrides } from '$lib/types/canvas';

export interface ThemeRenderingConfig {
	hideIcons?: boolean;
	borderRadius?: number;
	attrFontColor?: string;
	hideTypeStereotypes?: boolean;
	abstractBoldOverride?: boolean;
}

export interface ThemeConfig {
	element_defaults: Record<string, Record<string, string | number | boolean>>;
	stereotype_overrides: Record<string, Record<string, string | number>>;
	edge_defaults: Record<string, Record<string, string | number>>;
	global: Record<string, string | number>;
	rendering?: ThemeRenderingConfig;
}

export interface Theme {
	id: string;
	name: string;
	description: string | null;
	notation: string;
	config: ThemeConfig;
	is_default: boolean;
	created_at: string;
	updated_at: string;
}

let themes = $state<Theme[]>([]);
let activeThemeIds = $state<Record<string, string>>(
	typeof localStorage !== 'undefined'
		? JSON.parse(localStorage.getItem('iris_active_themes') ?? '{}')
		: {}
);

export function getThemes(): Theme[] {
	return themes;
}

export function getThemesForNotation(notation: string): Theme[] {
	return themes.filter((t) => t.notation === notation);
}

export function getActiveThemeId(notation: string): string | undefined {
	return activeThemeIds[notation];
}

export function getActiveTheme(notation: string): Theme | undefined {
	const id = activeThemeIds[notation];
	if (id) return themes.find((t) => t.id === id);
	// Fall back to first default theme for notation
	return themes.find((t) => t.notation === notation && t.is_default);
}

export function setActiveTheme(notation: string, themeId: string): void {
	activeThemeIds = { ...activeThemeIds, [notation]: themeId };
	localStorage.setItem('iris_active_themes', JSON.stringify(activeThemeIds));
}

export function resolveNodeVisual(
	notation: string,
	entityType: string,
	stereotype?: string,
	preferredThemeId?: string,
): NodeVisualOverrides | undefined {
	// User-selected active theme wins over diagram's preferred theme
	const explicitActive = getActiveThemeId(notation);
	const theme = explicitActive
		? themes.find((t) => t.id === explicitActive) ?? getActiveTheme(notation)
		: preferredThemeId
			? themes.find((t) => t.id === preferredThemeId) ?? getActiveTheme(notation)
			: getActiveTheme(notation);
	if (!theme) return undefined;
	const cfg = theme.config;

	const result: NodeVisualOverrides = {};
	let hasValues = false;

	// Layer 5: global defaults
	if (cfg.global?.defaultBgColor) { result.bgColor = String(cfg.global.defaultBgColor); hasValues = true; }
	if (cfg.global?.defaultBorderColor) { result.borderColor = String(cfg.global.defaultBorderColor); hasValues = true; }
	if (cfg.global?.defaultFontColor) { result.fontColor = String(cfg.global.defaultFontColor); hasValues = true; }

	// Layer 4: element type defaults
	const typeDefaults = cfg.element_defaults?.[entityType];
	if (typeDefaults) {
		if (typeDefaults.bgColor) { result.bgColor = String(typeDefaults.bgColor); hasValues = true; }
		if (typeDefaults.borderColor) { result.borderColor = String(typeDefaults.borderColor); hasValues = true; }
		if (typeDefaults.fontColor) { result.fontColor = String(typeDefaults.fontColor); hasValues = true; }
		if (typeDefaults.borderWidth != null) { result.borderWidth = Number(typeDefaults.borderWidth); hasValues = true; }
		if (typeDefaults.italic) { result.italic = true; hasValues = true; }
	}

	// Layer 3: stereotype override
	if (stereotype && cfg.stereotype_overrides?.[stereotype]) {
		const so = cfg.stereotype_overrides[stereotype];
		if (so.bgColor) { result.bgColor = String(so.bgColor); hasValues = true; }
		if (so.borderColor) { result.borderColor = String(so.borderColor); hasValues = true; }
		if (so.fontColor) { result.fontColor = String(so.fontColor); hasValues = true; }
	}

	return hasValues ? result : undefined;
}

export function getThemeRendering(notation: string, preferredThemeId?: string): ThemeRenderingConfig | undefined {
	// User-selected active theme wins over diagram's preferred theme
	const explicitActive = getActiveThemeId(notation);
	const theme = explicitActive
		? themes.find((t) => t.id === explicitActive) ?? getActiveTheme(notation)
		: preferredThemeId
			? themes.find((t) => t.id === preferredThemeId) ?? getActiveTheme(notation)
			: getActiveTheme(notation);
	return theme?.config?.rendering;
}

export function resolveEdgeVisual(
	notation: string,
	relType: string,
): EdgeVisualOverrides | undefined {
	const theme = getActiveTheme(notation);
	if (!theme) return undefined;
	const cfg = theme.config;

	const edgeDefaults = cfg.edge_defaults?.[relType];
	if (!edgeDefaults) return undefined;

	const result: EdgeVisualOverrides = {};
	if (edgeDefaults.lineColor) result.lineColor = String(edgeDefaults.lineColor);
	if (edgeDefaults.lineWidth) result.lineWidth = Number(edgeDefaults.lineWidth);
	if (edgeDefaults.dashArray) result.dashArray = String(edgeDefaults.dashArray);

	return Object.keys(result).length > 0 ? result : undefined;
}

export async function loadThemes(): Promise<void> {
	try {
		themes = await apiFetch<Theme[]>('/api/themes');
	} catch {
		themes = [];
	}
}
