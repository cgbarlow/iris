import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Element templates frontend wiring tests (v6.8.0, ADR-191, issue
 * #153). Static-parser style — mirrors the dashboardHierarchy /
 * packageRelationshipsTab patterns. Verifies that the three new
 * affordances exist and reach the right backend endpoints.
 */

const elementsListSrc = readFileSync(
	resolve(__dirname, '../../src/routes/elements/+page.svelte'),
	'utf-8',
);
const elementDetailSrc = readFileSync(
	resolve(__dirname, '../../src/routes/elements/[id]/+page.svelte'),
	'utf-8',
);
const templateDetailSrc = readFileSync(
	resolve(__dirname, '../../src/routes/element-templates/[id]/+page.svelte'),
	'utf-8',
);
const templatesListDialogSrc = readFileSync(
	resolve(__dirname, '../../src/lib/components/TemplatesListDialog.svelte'),
	'utf-8',
);
const createTemplateDialogSrc = readFileSync(
	resolve(__dirname, '../../src/lib/components/CreateTemplateDialog.svelte'),
	'utf-8',
);

describe('Elements list — Templates button + dialog', () => {
	it('imports TemplatesListDialog', () => {
		expect(elementsListSrc).toContain('TemplatesListDialog');
	});

	it('exposes a Templates button next to New Element', () => {
		// The button toggles a state flag — verify both.
		expect(elementsListSrc).toContain('showTemplatesDialog = true');
		expect(elementsListSrc).toMatch(/>\s*Templates\s*</);
	});

	it('passes the current set_id to the dialog', () => {
		expect(elementsListSrc).toContain('setId={currentSetId}');
	});

	it('navigates to the created element after Use', () => {
		expect(elementsListSrc).toContain('goto(`/elements/${newId}`)');
	});
});

describe('Element detail — Save as template action', () => {
	it('imports CreateTemplateDialog', () => {
		expect(elementDetailSrc).toContain('CreateTemplateDialog');
	});

	it('has a Save-as-template button that opens the dialog', () => {
		expect(elementDetailSrc).toContain('showSaveTemplateDialog = true');
		expect(elementDetailSrc).toContain('Save as template');
	});

	it('routes to the new template detail page on creation', () => {
		expect(elementDetailSrc).toContain('goto(`/element-templates/${templateId}`)');
	});
});

describe('TemplatesListDialog — API contract', () => {
	it('calls GET /api/element-templates with set_id + include_global', () => {
		expect(templatesListDialogSrc).toContain('/api/element-templates?');
		expect(templatesListDialogSrc).toContain("params.set('include_global', 'true')");
		expect(templatesListDialogSrc).toContain("params.set('set_id', setId)");
	});

	it('POSTs to /api/elements with template_id when Use is confirmed', () => {
		expect(templatesListDialogSrc).toContain("'/api/elements'");
		expect(templatesListDialogSrc).toContain('template_id: useTarget.id');
	});

	it('sanitises the new element name with DOMPurify before sending', () => {
		expect(templatesListDialogSrc).toContain('DOMPurify');
		expect(templatesListDialogSrc).toContain('DOMPurify.sanitize(newName.trim())');
	});

	it('shows an empty-state when no templates exist', () => {
		expect(templatesListDialogSrc).toContain('No templates available');
	});
});

describe('CreateTemplateDialog — field whitelist + scoping', () => {
	it('lists the eight whitelisted fields from INCLUDED_FIELD_WHITELIST', () => {
		// Mirrors backend/app/element_templates/models.py:INCLUDED_FIELD_WHITELIST.
		for (const f of [
			'name',
			'description',
			'element_type',
			'notation',
			'data',
			'metadata',
			'package_id',
			'tags',
		]) {
			expect(createTemplateDialogSrc).toContain(`value: '${f}'`);
		}
	});

	it('POSTs to /api/element-templates with source_element_id + included_fields', () => {
		expect(createTemplateDialogSrc).toContain("'/api/element-templates'");
		expect(createTemplateDialogSrc).toContain('source_element_id: sourceElementId');
		expect(createTemplateDialogSrc).toContain('included_fields: included');
	});

	it('blocks save when global is off and no set_id is supplied', () => {
		expect(createTemplateDialogSrc).toContain('only Global scope is available');
	});

	it('flips set_id to null when promoting to global', () => {
		expect(createTemplateDialogSrc).toContain('set_id: isGlobal ? null : setId');
	});

	it("clarifies the 'data' label so users know it covers class attributes (issue #165)", () => {
		// The opaque "Data payload" label hid the fact that class
		// attributes / operations / literals all live in element.data.
		expect(createTemplateDialogSrc).not.toMatch(/label:\s*'Data payload'/);
		expect(createTemplateDialogSrc).toMatch(/label:\s*'Data \(attributes, operations, visual…\)'/);
	});

	it('renders help text explaining what Data vs Metadata capture', () => {
		expect(createTemplateDialogSrc).toContain('class elements');
		expect(createTemplateDialogSrc).toContain('attributes and operations');
	});
});

describe('Element template detail page', () => {
	it('loads template by id from GET /api/element-templates/{id}', () => {
		expect(templateDetailSrc).toContain('/api/element-templates/${id}');
	});

	it('has a Create-element-from-template form that POSTs to /api/elements', () => {
		expect(templateDetailSrc).toContain('template_id: tpl.id');
		expect(templateDetailSrc).toContain("'/api/elements'");
	});

	it('has a Delete affordance calling DELETE /api/element-templates/{id}', () => {
		expect(templateDetailSrc).toContain('/api/element-templates/${tpl.id}');
		expect(templateDetailSrc).toContain("method: 'DELETE'");
	});

	it('renders included_fields against template_data in a table', () => {
		expect(templateDetailSrc).toContain('Captured fields');
		expect(templateDetailSrc).toContain('tpl.included_fields');
		expect(templateDetailSrc).toContain('tpl.template_data');
	});

	it('shows a Global badge for global templates and the set name otherwise', () => {
		expect(templateDetailSrc).toMatch(/>\s*Global\s*</);
		expect(templateDetailSrc).toContain('tpl.set_name');
	});
});
