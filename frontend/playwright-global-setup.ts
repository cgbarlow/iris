/**
 * Playwright global setup — ensures a clean backend database before each test run.
 *
 * Without this, stale database state (locked accounts, leftover data) from previous
 * runs causes cascading test failures.
 */

import { execSync } from 'child_process';
import { existsSync, rmSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

export default async function globalSetup() {
	const __filename = fileURLToPath(import.meta.url);
	const __dirname = path.dirname(__filename);
	const dataDir = path.resolve(__dirname, '../backend/data');

	// Kill any existing backend server so we start fresh
	try {
		execSync('pkill -f "uvicorn app.main" || true', { stdio: 'ignore' });
	} catch {
		// Process may not exist — that's fine
	}

	// Brief pause for the process to fully exit and release the port
	await new Promise((resolve) => setTimeout(resolve, 500));

	// Delete backend database files to guarantee clean state
	if (existsSync(dataDir)) {
		rmSync(dataDir, { recursive: true, force: true });
	}
}
