#!/usr/bin/env node
/**
 * Sync Lucide icon metadata (tags + categories) from the lucide-static package
 * and lucide GitHub repo into our iconTags.json and iconTags.ts files.
 *
 * Usage: node scripts/sync-lucide-metadata.mjs
 *
 * This fetches:
 * - tags.json from lucide-static (fast, one HTTP request)
 * - Per-icon categories from GitHub API (bulk, via git trees API)
 *
 * Output: src/lib/icons/iconTags.json (consumed by frontend + backend)
 */

import { writeFileSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_JSON = resolve(__dirname, '../src/lib/icons/iconTags.json');
const OUTPUT_TS = resolve(__dirname, '../src/lib/icons/iconTags.ts');

// Get the installed lucide-svelte version
const lucidePkg = JSON.parse(
  readFileSync(resolve(__dirname, '../node_modules/lucide-svelte/package.json'), 'utf-8')
);
const VERSION = lucidePkg.version;
console.log(`Syncing metadata for lucide-svelte@${VERSION}...`);

// Step 1: Fetch tags.json from lucide-static (all tags in one request)
const tagsUrl = `https://unpkg.com/lucide-static@${VERSION}/tags.json`;
console.log(`Fetching tags from ${tagsUrl}...`);
const tagsResp = await fetch(tagsUrl);
if (!tagsResp.ok) throw new Error(`Failed to fetch tags.json: ${tagsResp.status}`);
const tagsData = await tagsResp.json();
console.log(`  Got tags for ${Object.keys(tagsData).length} icons`);

// Step 2: Fetch categories via GitHub API (git trees for bulk listing)
// We use the GitHub API to list all .json files in the icons/ directory
const treeUrl = `https://api.github.com/repos/lucide-icons/lucide/git/trees/${VERSION}?recursive=1`;
console.log(`Fetching file tree from GitHub for tag ${VERSION}...`);
const treeResp = await fetch(treeUrl, {
  headers: { 'Accept': 'application/vnd.github.v3+json' }
});

let categoriesByIcon = {};

if (treeResp.ok) {
  const treeData = await treeResp.json();
  // Find all icons/*.json files (metadata files)
  const iconJsonFiles = treeData.tree
    .filter(f => f.path.match(/^icons\/[a-z][\w-]*\.json$/) && f.type === 'blob')
    .map(f => ({
      name: f.path.replace('icons/', '').replace('.json', ''),
      sha: f.sha
    }));

  console.log(`  Found ${iconJsonFiles.length} icon metadata files`);

  // Fetch in batches of 50 using raw.githubusercontent.com (no rate limit)
  const BATCH_SIZE = 50;
  let fetched = 0;

  for (let i = 0; i < iconJsonFiles.length; i += BATCH_SIZE) {
    const batch = iconJsonFiles.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(
      batch.map(async ({ name }) => {
        try {
          const url = `https://raw.githubusercontent.com/lucide-icons/lucide/${VERSION}/icons/${name}.json`;
          const resp = await fetch(url);
          if (resp.ok) {
            const data = await resp.json();
            return { name, categories: data.categories || [] };
          }
        } catch { /* ignore */ }
        return { name, categories: [] };
      })
    );
    for (const r of results) {
      if (r.categories.length > 0) {
        categoriesByIcon[r.name] = r.categories;
      }
    }
    fetched += batch.length;
    process.stdout.write(`\r  Fetched categories: ${fetched}/${iconJsonFiles.length}`);
  }
  console.log('');
} else {
  console.warn(`  GitHub API returned ${treeResp.status}, using tags-only mode (no categories)`);
}

// Step 3: Build the merged iconTags array
// Map Lucide categories to our simplified category names
const CATEGORY_MAP = {
  'accessibility': 'people',
  'account': 'people',
  'people': 'people',
  'animals': 'nature',
  'nature': 'nature',
  'arrows': 'navigation',
  'navigation': 'navigation',
  'cursors': 'navigation',
  'brands': 'software',
  'buildings': 'organization',
  'charts': 'data',
  'communication': 'communication',
  'mail': 'communication',
  'notifications': 'communication',
  'connectivity': 'technology',
  'devices': 'technology',
  'design': 'settings',
  'development': 'software',
  'emoji': 'status',
  'files': 'data',
  'finance': 'finance',
  'shopping': 'finance',
  'food-beverage': 'transport',
  'gaming': 'software',
  'home': 'organization',
  'layout': 'structure',
  'math': 'data',
  'medical': 'status',
  'multimedia': 'software',
  'photography': 'software',
  'science': 'data',
  'seasons': 'nature',
  'weather': 'nature',
  'security': 'security',
  'shapes': 'structure',
  'social': 'communication',
  'sports': 'people',
  'sustainability': 'strategy',
  'text': 'data',
  'time': 'process',
  'tools': 'settings',
  'transportation': 'transport',
  'travel': 'transport',
};

const iconTags = [];
for (const [name, tags] of Object.entries(tagsData)) {
  const lucideCategories = categoriesByIcon[name] || [];

  // Pick the best category from the icon's Lucide categories
  let category = 'other';
  for (const lc of lucideCategories) {
    if (CATEGORY_MAP[lc]) {
      category = CATEGORY_MAP[lc];
      break;
    }
  }

  iconTags.push({ name, tags, category });
}

// Sort by category then name for readability
iconTags.sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));

// Step 4: Write iconTags.json
writeFileSync(OUTPUT_JSON, JSON.stringify(iconTags, null, 2) + '\n');
console.log(`Wrote ${iconTags.length} icons to ${OUTPUT_JSON}`);

// Step 5: Print category summary
const catCounts = {};
for (const entry of iconTags) {
  catCounts[entry.category] = (catCounts[entry.category] || 0) + 1;
}
console.log('\nCategory breakdown:');
for (const [cat, count] of Object.entries(catCounts).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${cat}: ${count}`);
}

// Step 6: Regenerate iconTags.ts to import from JSON
const tsContent = `/**
 * Icon tag index for semantic matching (ADR-091-B).
 *
 * AUTO-GENERATED from Lucide metadata.
 * Run: node scripts/sync-lucide-metadata.mjs
 *
 * Maps icon names to search tags/keywords and categories. Used by:
 * - Backend SemanticIconMatcher during EA import
 * - Frontend IconPicker for search and category filtering
 */

import iconTagsJson from './iconTags.json';

export interface IconTagEntry {
\tname: string;
\ttags: string[];
\tcategory: string;
}

/** All Lucide icons with their tags and categories. */
export const ICON_TAGS: IconTagEntry[] = iconTagsJson as IconTagEntry[];

/** Flat lookup: icon name → tags for quick matching. */
export const ICON_TAG_INDEX: Record<string, string[]> = Object.fromEntries(
\tICON_TAGS.map((entry) => [entry.name, entry.tags]),
);

/** All unique categories in the tag index. */
export const ICON_CATEGORIES = [...new Set(ICON_TAGS.map((e) => e.category))].sort();

/** JSON-serializable version for backend consumption. */
export function getIconTagsJSON(): string {
\treturn JSON.stringify(ICON_TAGS);
}
`;

writeFileSync(OUTPUT_TS, tsContent);
console.log(`Wrote ${OUTPUT_TS}`);
