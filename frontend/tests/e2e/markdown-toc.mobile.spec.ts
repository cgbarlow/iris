import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createDiagram } from './fixtures';

// ADR-229 follow-up: the Table of Contents on Text (markdown) views is a
// 300px right column that would squeeze the content to nothing on a phone.
// On mobile it should open as a fixed right overlay drawer instead.

const MARKDOWN = `# Document Title

## Section One

Some content here.

## Section Two

More content.
`;

let diagramId = '';

test.beforeAll(async () => {
	await seedAdmin();
	const token = await getAuthToken();
	const d = await createDiagram(undefined, token, {
		diagram_type: 'text',
		notation: 'markdown',
		name: 'Mobile TOC Doc',
		data: { content: MARKDOWN }
	});
	diagramId = d.id as string;
});

test('the TOC opens as a full-height right overlay drawer on mobile', async ({ page }) => {
	test.slow();
	await loginAsAdmin(page);
	await page.goto(`/views/${diagramId}`);
	await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });

	const toc = page.locator('aside.md-toc');
	await page.getByRole('button', { name: 'Toggle table of contents' }).first().click();
	await expect(toc).toBeVisible();

	// Fixed overlay (not the inline 300px column) and fills the viewport height.
	await expect(toc).toHaveCSS('position', 'fixed');
	const vh = await page.evaluate(() => window.innerHeight);
	const box = await toc.boundingBox();
	expect(box!.height).toBeGreaterThan(vh * 0.8);

	// Headings are listed.
	await expect(toc.getByRole('button', { name: 'Section One' })).toBeVisible();

	// No horizontal overflow while the overlay is open (content not squeezed).
	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	expect(overflow).toBeLessThanOrEqual(1);

	// Backdrop closes it — tap the strip left of the right-anchored drawer.
	await page.locator('.md-toc-backdrop').click({ position: { x: 20, y: 400 } });
	await expect(toc).toBeHidden();
});
