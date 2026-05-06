// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.5.0 (issue #48): the extension manager page renders source method
 * (GitHub badge), the source URL link, installed-vs-latest version pair,
 * an "Update available" pill, and Check Updates / Upgrade buttons for
 * github-sourced extensions.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/admin/settings/extensions/+page.svelte'),
	'utf-8',
);

describe('Extension manager fields (v5.5.0, issue #48)', () => {
	it('imports isNewerSemver helper', () => {
		expect(SRC).toMatch(/import\s*\{\s*isNewerSemver\s*\}\s*from\s*['"]\$lib\/utils\/semverCompare['"]/);
	});

	it('renders a GitHub source badge', () => {
		expect(SRC).toMatch(/>\s*GitHub\s*</);
	});

	it('renders an "Update available" pill gated on updateAvailable()', () => {
		expect(SRC).toMatch(/updateAvailable\s*\(\s*installed\s*\)/);
		expect(SRC).toMatch(/>\s*Update available\s*</);
	});

	it('renders the source URL link', () => {
		// Look for `target="_blank"` with `href` referencing the source_url.
		expect(SRC).toMatch(/href=\{[^}]*source_url[^}]*\}[\s\S]{0,400}?target="_blank"/);
	});

	it('renders Check for updates + Upgrade buttons', () => {
		expect(SRC).toMatch(/['"]Check for updates['"]/);
		expect(SRC).toMatch(/['"]Checking…['"]/);
		expect(SRC).toMatch(/Upgrade to v.*installed\.latest_version/);
	});

	it('checkForUpdates and upgradeExtension handlers exist', () => {
		expect(SRC).toMatch(/async\s+function\s+checkForUpdates/);
		expect(SRC).toMatch(/async\s+function\s+upgradeExtension/);
		expect(SRC).toMatch(/\/api\/extensions\/\$\{extensionId\}\/check-update/);
		expect(SRC).toMatch(/\/api\/extensions\/\$\{extensionId\}\/upgrade/);
	});

	it('mnemos KNOWN_EXTENSIONS entry points at MNEMOSv2 with auto-upgrade', () => {
		// Extract just the mnemos object body from KNOWN_EXTENSIONS.
		const mnemosMatch = SRC.match(/id:\s*['"]mnemos['"][\s\S]*?\}/);
		expect(mnemosMatch).not.toBeNull();
		const block = mnemosMatch![0];
		expect(block).toMatch(/source_method\s*:\s*['"]github['"]/);
		expect(block).toMatch(/MNEMOSv2/);
		expect(block).toMatch(/supports_auto_upgrade\s*:\s*true/);
	});
});
