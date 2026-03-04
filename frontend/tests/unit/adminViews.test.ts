import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Admin-Configurable Views tests (ADR-075).
 * Verifies backend views module, migration, frontend store, selector, and admin page.
 */

/* ── Backend: Migration ── */

describe('Views migration (m017)', () => {
	const migrationSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/migrations/m017_views.py'),
		'utf-8',
	);

	it('creates views table', () => {
		expect(migrationSrc).toContain('CREATE TABLE views');
	});

	it('has id, name, description, config columns', () => {
		expect(migrationSrc).toContain('id TEXT PRIMARY KEY');
		expect(migrationSrc).toContain('name TEXT NOT NULL UNIQUE');
		expect(migrationSrc).toContain('description TEXT');
		expect(migrationSrc).toContain('config TEXT NOT NULL');
	});

	it('has is_default flag', () => {
		expect(migrationSrc).toContain('is_default INTEGER NOT NULL DEFAULT 0');
	});

	it('has created_by and timestamp columns', () => {
		expect(migrationSrc).toContain('created_by TEXT');
		expect(migrationSrc).toContain('created_at TEXT');
		expect(migrationSrc).toContain('updated_at TEXT');
	});

	it('is idempotent — checks if table exists before creating', () => {
		expect(migrationSrc).toContain("SELECT name FROM sqlite_master WHERE type='table' AND name='views'");
	});
});

/* ── Backend: Service ── */

describe('Views service', () => {
	const serviceSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/views/service.py'),
		'utf-8',
	);

	it('has create_view function', () => {
		expect(serviceSrc).toContain('async def create_view');
	});

	it('has list_views function', () => {
		expect(serviceSrc).toContain('async def list_views');
	});

	it('has get_view function', () => {
		expect(serviceSrc).toContain('async def get_view');
	});

	it('has update_view function', () => {
		expect(serviceSrc).toContain('async def update_view');
	});

	it('has delete_view function', () => {
		expect(serviceSrc).toContain('async def delete_view');
	});

	it('prevents deletion of default views', () => {
		expect(serviceSrc).toContain('is_default');
		expect(serviceSrc).toContain('return False');
	});

	it('has seed_default_views function', () => {
		expect(serviceSrc).toContain('async def seed_default_views');
	});

	it('seeds Standard view with simplified config', () => {
		expect(serviceSrc).toContain('"Standard"');
		expect(serviceSrc).toContain('"show_extended": False');
	});

	it('seeds Advanced view with full config', () => {
		expect(serviceSrc).toContain('"Advanced"');
		expect(serviceSrc).toContain('"show_extended": True');
	});

	it('Standard view hides cardinality and roles', () => {
		expect(serviceSrc).toContain('"show_cardinality": False');
		expect(serviceSrc).toContain('"show_role_names": False');
	});

	it('Advanced view shows cardinality and roles', () => {
		expect(serviceSrc).toContain('"show_cardinality": True');
		expect(serviceSrc).toContain('"show_role_names": True');
	});
});

/* ── Backend: Router ── */

describe('Views router', () => {
	const routerSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/views/router.py'),
		'utf-8',
	);

	it('has GET /api/views route', () => {
		expect(routerSrc).toContain('prefix="/api/views"');
		expect(routerSrc).toContain('@router.get("",');
	});

	it('has POST /api/views route', () => {
		expect(routerSrc).toContain('@router.post("",');
	});

	it('has PUT /api/views/{view_id} route', () => {
		expect(routerSrc).toContain('@router.put("/{view_id}"');
	});

	it('has DELETE /api/views/{view_id} route', () => {
		expect(routerSrc).toContain('@router.delete("/{view_id}"');
	});

	it('requires authentication on all routes', () => {
		expect(routerSrc).toContain('get_current_user');
	});

	it('returns 403 when deleting default view', () => {
		expect(routerSrc).toContain('403');
		expect(routerSrc).toContain('Cannot delete default views');
	});
});

/* ── Backend: Models ── */

describe('Views Pydantic models', () => {
	const modelsSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/views/models.py'),
		'utf-8',
	);

	it('has ViewConfig model with toolbar, metadata, canvas', () => {
		expect(modelsSrc).toContain('class ViewConfig');
		expect(modelsSrc).toContain('toolbar');
		expect(modelsSrc).toContain('metadata');
		expect(modelsSrc).toContain('canvas');
	});

	it('has ViewCreate and ViewUpdate models', () => {
		expect(modelsSrc).toContain('class ViewCreate');
		expect(modelsSrc).toContain('class ViewUpdate');
	});

	it('has ViewResponse model with all fields', () => {
		expect(modelsSrc).toContain('class ViewResponse');
		expect(modelsSrc).toContain('is_default');
		expect(modelsSrc).toContain('created_at');
		expect(modelsSrc).toContain('updated_at');
	});
});

/* ── Backend: Registration ── */

describe('Views registration', () => {
	const mainSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/main.py'),
		'utf-8',
	);
	const startupSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/startup.py'),
		'utf-8',
	);

	it('views router is registered in main.py', () => {
		expect(mainSrc).toContain('views_router');
		expect(mainSrc).toContain('include_router(views_router)');
	});

	it('m017 migration runs in startup.py', () => {
		expect(startupSrc).toContain('m017_up');
	});

	it('seed_default_views runs in startup.py', () => {
		expect(startupSrc).toContain('seed_default_views');
	});
});

/* ── Frontend: View Store ── */

describe('View store', () => {
	const storeSrc = readFileSync(
		resolve(__dirname, '../../src/lib/stores/viewStore.svelte.ts'),
		'utf-8',
	);

	it('exports View and ViewConfig interfaces', () => {
		expect(storeSrc).toContain('export interface View');
		expect(storeSrc).toContain('export interface ViewConfig');
	});

	it('has toolbar, metadata, canvas in ViewConfig', () => {
		expect(storeSrc).toContain('toolbar');
		expect(storeSrc).toContain('metadata');
		expect(storeSrc).toContain('canvas');
	});

	it('exports getViews function', () => {
		expect(storeSrc).toContain('export function getViews');
	});

	it('exports getActiveViewId function', () => {
		expect(storeSrc).toContain('export function getActiveViewId');
	});

	it('exports getActiveView function', () => {
		expect(storeSrc).toContain('export function getActiveView');
	});

	it('exports getActiveConfig function', () => {
		expect(storeSrc).toContain('export function getActiveConfig');
	});

	it('exports setActiveView function', () => {
		expect(storeSrc).toContain('export function setActiveView');
	});

	it('persists active view in localStorage', () => {
		expect(storeSrc).toContain('localStorage');
		expect(storeSrc).toContain('iris_active_view');
	});

	it('fetches views from /api/views', () => {
		expect(storeSrc).toContain('/api/views');
	});

	it('returns sensible defaults when no view is active', () => {
		expect(storeSrc).toContain('show_overview: true');
		expect(storeSrc).toContain('show_details: true');
	});
});

/* ── Frontend: ViewSelector ── */

describe('ViewSelector component', () => {
	const selectorSrc = readFileSync(
		resolve(__dirname, '../../src/lib/components/ViewSelector.svelte'),
		'utf-8',
	);

	it('imports view store functions', () => {
		expect(selectorSrc).toContain('getViews');
		expect(selectorSrc).toContain('getActiveViewId');
		expect(selectorSrc).toContain('setActiveView');
	});

	it('renders a select element with aria-label', () => {
		expect(selectorSrc).toContain('aria-label="Active view"');
		expect(selectorSrc).toContain('<select');
	});

	it('renders options from views list', () => {
		expect(selectorSrc).toContain('{#each views as view}');
		expect(selectorSrc).toContain('<option');
		expect(selectorSrc).toContain('view.name');
	});

	it('handles view change events', () => {
		expect(selectorSrc).toContain('onchange');
		expect(selectorSrc).toContain('setActiveView');
	});

	it('loads views on mount', () => {
		expect(selectorSrc).toContain('loadViews');
	});
});

/* ── Frontend: Admin Views Page ── */

describe('Admin views page', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/admin/views/+page.svelte'),
		'utf-8',
	);

	it('fetches views from /api/views', () => {
		expect(pageSrc).toContain('/api/views');
	});

	it('has New View button', () => {
		expect(pageSrc).toContain('New View');
	});

	it('supports creating a new view', () => {
		expect(pageSrc).toContain("method: 'POST'");
		expect(pageSrc).toContain('startCreate');
	});

	it('supports editing an existing view', () => {
		expect(pageSrc).toContain("method: 'PUT'");
		expect(pageSrc).toContain('startEdit');
	});

	it('supports deleting a non-default view', () => {
		expect(pageSrc).toContain("method: 'DELETE'");
		expect(pageSrc).toContain('confirmDelete');
	});

	it('shows Default badge on default views', () => {
		expect(pageSrc).toContain('is_default');
		expect(pageSrc).toContain('Default');
	});

	it('prevents deleting default views (no delete button for defaults)', () => {
		expect(pageSrc).toContain('!view.is_default');
	});

	it('has config JSON textarea for editing', () => {
		expect(pageSrc).toContain('textarea');
		expect(pageSrc).toContain('editConfigJson');
	});

	it('uses ConfirmDialog for delete confirmation', () => {
		expect(pageSrc).toContain('ConfirmDialog');
		expect(pageSrc).toContain('Delete View');
	});

	it('has name and description input fields', () => {
		expect(pageSrc).toContain('editName');
		expect(pageSrc).toContain('editDescription');
	});
});
