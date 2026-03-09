/**
 * ADR-089: Comprehensive EA Rendering Fidelity Audit
 * Scans ALL diagrams across AIXM and FIXM, checking for rendering issues.
 */
import { chromium } from '@playwright/test';

// Token is pre-generated and saved to /tmp/iris_token.txt

const SETS = {
  AIXM: '7c4e56d9-a768-4acb-a4d8-199b41f21d25',
  FIXM: '82d9a06d-5452-4759-acf8-f5adc90497b8',
};

async function getToken() {
  const fs = await import('fs');
  return fs.readFileSync('/tmp/iris_token.txt', 'utf-8').trim();
}

async function fetchAllDiagrams(token, setId) {
  const all = [];
  let page = 1;
  while (true) {
    const resp = await fetch(
      `http://localhost:8000/api/diagrams?set_id=${setId}&page_size=100&page=${page}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await resp.json();
    all.push(...data.items);
    if (all.length >= data.total) break;
    page++;
  }
  return all;
}

async function fetchDiagramDetail(token, id) {
  const resp = await fetch(`http://localhost:8000/api/diagrams/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return resp.json();
}

async function auditDiagram(page, diagramId, diagramName, apiData) {
  const issues = [];
  const ok = [];
  const nodes = apiData?.data?.nodes || [];
  const edges = apiData?.data?.edges || [];

  // Navigate to diagram
  await page.goto(`http://localhost:5173/diagrams/${diagramId}`, { timeout: 15000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  // Check for error states
  const errorEl = await page.$('.error-message, [role="alert"]');
  if (errorEl) {
    const errText = await errorEl.textContent();
    issues.push({ type: 'error', detail: `Page error: ${errText?.trim().substring(0, 100)}` });
    return { issues, ok };
  }

  // 1. Check node count matches API
  const renderedNodes = await page.$$('.svelte-flow__node');
  const apiNodeCount = nodes.filter(n => n.type !== 'diagram_frame').length;
  const renderedCount = renderedNodes.length;
  // Diagram frame may or may not be a separate DOM node
  const frameDom = await page.$('[data-type="diagram_frame"]');
  const adjustedRendered = frameDom ? renderedCount - 1 : renderedCount;
  if (Math.abs(adjustedRendered - apiNodeCount) > 0) {
    issues.push({
      type: 'missing_nodes',
      detail: `Node count mismatch: API has ${apiNodeCount} content nodes, DOM has ${adjustedRendered} (${apiNodeCount - adjustedRendered} missing)`,
    });
  } else {
    ok.push(`Node count matches: ${apiNodeCount}`);
  }

  // 2. Check edge count
  const renderedEdges = await page.$$('.svelte-flow__edge');
  if (Math.abs(renderedEdges.length - edges.length) > 0) {
    issues.push({
      type: 'missing_edges',
      detail: `Edge count mismatch: API has ${edges.length}, DOM has ${renderedEdges.length}`,
    });
  } else {
    ok.push(`Edge count matches: ${edges.length}`);
  }

  // 3. Check for clipped content
  const clippedNodes = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node').forEach(node => {
      const label = node.querySelector('.uml-node__label')?.textContent?.trim() || 'unknown';
      const scrollH = node.scrollHeight;
      const clientH = node.clientHeight;
      if (scrollH > clientH + 3) {
        results.push({ label, scrollH, clientH, diff: scrollH - clientH });
      }
    });
    return results;
  });
  if (clippedNodes.length > 0) {
    issues.push({
      type: 'clipped_content',
      detail: `${clippedNodes.length} nodes have clipped content: ${clippedNodes.map(n => `${n.label}(${n.diff}px)`).join(', ')}`,
    });
  } else {
    ok.push('No clipped nodes');
  }

  // 4. Check for text overflow in nodes
  const overflowNodes = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node').forEach(node => {
      const label = node.querySelector('.uml-node__label')?.textContent?.trim() || 'unknown';
      const computed = getComputedStyle(node);
      // Check if any child text overflows horizontally
      for (const child of node.querySelectorAll('.uml-node__attr, .uml-node__label, .uml-node__stereotype')) {
        if (child.scrollWidth > child.clientWidth + 2) {
          results.push({ label, element: child.className, scrollW: child.scrollWidth, clientW: child.clientWidth });
        }
      }
    });
    return results;
  });
  if (overflowNodes.length > 0) {
    issues.push({
      type: 'text_overflow',
      detail: `${overflowNodes.length} nodes have horizontal text overflow: ${overflowNodes.slice(0, 5).map(n => n.label).join(', ')}`,
    });
  }

  // 5. Check for note nodes - duplicate title in body
  const noteIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('[data-type="note"]').forEach(node => {
      const label = node.querySelector('.note-node__label')?.textContent?.trim() || '';
      const body = node.querySelector('.note-node__body, .note-node__description')?.textContent?.trim() || '';
      if (label && body.startsWith(label)) {
        results.push({ label, bodyStart: body.substring(0, 50) });
      }
    });
    return results;
  });
  if (noteIssues.length > 0) {
    issues.push({
      type: 'note_duplicate_title',
      detail: `${noteIssues.length} notes have duplicated title in body: ${noteIssues.map(n => n.label).join(', ')}`,
    });
  }

  // 6. Check diagram frame
  const frameNode = nodes.find(n => n.type === 'diagram_frame');
  if (frameNode) {
    const frameDomEl = await page.$('[data-type="diagram_frame"]');
    if (!frameDomEl) {
      issues.push({ type: 'missing_frame', detail: 'Diagram frame node in API data but not rendered' });
    } else {
      ok.push('Diagram frame present');
      // Check frame participates in zoom/pan
      const frameTransform = await page.evaluate(() => {
        const frame = document.querySelector('[data-type="diagram_frame"]');
        if (!frame) return null;
        const transform = frame.closest('.svelte-flow__node')?.style?.transform;
        return transform || 'none';
      });
      if (frameTransform === 'none' || !frameTransform) {
        issues.push({ type: 'frame_not_transformed', detail: 'Diagram frame does not participate in canvas transforms' });
      }
    }
  }

  // 7. Check edge markers (composition/aggregation should have diamonds)
  const edgeMarkerIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.svelte-flow__edge').forEach(edge => {
      const type = edge.getAttribute('data-type') || '';
      const path = edge.querySelector('path');
      if (!path) return;
      const markerStart = path.getAttribute('marker-start') || '';
      const markerEnd = path.getAttribute('marker-end') || '';

      if ((type === 'composition' || type.includes('composition')) && !markerStart.includes('diamond') && !markerEnd.includes('diamond')) {
        results.push({ type, hasMarkers: { start: markerStart, end: markerEnd } });
      }
      if ((type === 'aggregation' || type.includes('aggregation')) && !markerStart.includes('diamond') && !markerEnd.includes('diamond')) {
        results.push({ type, hasMarkers: { start: markerStart, end: markerEnd } });
      }
    });
    return results;
  });
  if (edgeMarkerIssues.length > 0) {
    issues.push({
      type: 'missing_edge_markers',
      detail: `${edgeMarkerIssues.length} edges missing expected markers (diamonds): types=${[...new Set(edgeMarkerIssues.map(e => e.type))].join(',')}`,
    });
  }

  // 8. Check for italic inheritance on attributes
  const italicAttrIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node--abstract .uml-node__attr, .uml-node--abstract_class .uml-node__attr').forEach(attr => {
      const style = getComputedStyle(attr);
      if (style.fontStyle === 'italic') {
        const label = attr.closest('.uml-node')?.querySelector('.uml-node__label')?.textContent?.trim() || 'unknown';
        results.push({ label, text: attr.textContent?.trim().substring(0, 30) });
      }
    });
    return results;
  });
  if (italicAttrIssues.length > 0) {
    issues.push({
      type: 'italic_attributes',
      detail: `${italicAttrIssues.length} attributes in abstract classes have inherited italic: ${italicAttrIssues.map(a => a.label).join(', ')}`,
    });
  }

  // 9. Check edge labels (cardinality/role) positioning
  const edgeLabels = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.edge-endpoint-label').forEach(label => {
      const text = label.textContent?.trim();
      const rect = label.getBoundingClientRect();
      if (text && (rect.x < 0 || rect.y < 0 || rect.width === 0)) {
        results.push({ text, x: rect.x, y: rect.y, w: rect.width, h: rect.height });
      }
    });
    return results;
  });
  if (edgeLabels.length > 0) {
    issues.push({
      type: 'edge_label_offscreen',
      detail: `${edgeLabels.length} edge labels are off-screen or zero-width`,
    });
  }

  // 10. Check stereotype rendering
  const stereotypeIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node__stereotype').forEach(st => {
      const text = st.textContent?.trim();
      // Stereotypes should be wrapped in guillemets
      if (text && !text.startsWith('\u00AB') && !text.startsWith('<<')) {
        results.push({ text });
      }
    });
    return results;
  });
  if (stereotypeIssues.length > 0) {
    issues.push({
      type: 'stereotype_format',
      detail: `${stereotypeIssues.length} stereotypes not wrapped in guillemets: ${stereotypeIssues.slice(0, 3).map(s => s.text).join(', ')}`,
    });
  }

  // 11. Check qualifier/namespace display
  const qualifierIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node').forEach(node => {
      const label = node.querySelector('.uml-node__label')?.textContent?.trim() || '';
      const qualifier = node.querySelector('.uml-node__qualifier')?.textContent?.trim();
      // Check if qualifier text is visible (not clipped)
      const qualEl = node.querySelector('.uml-node__qualifier');
      if (qualEl) {
        const rect = qualEl.getBoundingClientRect();
        if (rect.height === 0 || rect.width === 0) {
          results.push({ label, qualifier, hidden: true });
        }
      }
    });
    return results;
  });
  if (qualifierIssues.length > 0) {
    issues.push({
      type: 'hidden_qualifier',
      detail: `${qualifierIssues.length} nodes have hidden qualifiers: ${qualifierIssues.map(q => q.label).join(', ')}`,
    });
  }

  // 12. Check package nodes
  const apiPackageNodes = nodes.filter(n => n.type === 'package_uml' || n.type === 'package');
  if (apiPackageNodes.length > 0) {
    const domPackages = await page.$$('[data-type="package_uml"], [data-type="package"]');
    if (domPackages.length < apiPackageNodes.length) {
      issues.push({
        type: 'missing_packages',
        detail: `${apiPackageNodes.length - domPackages.length} package nodes missing from DOM`,
      });
    }
  }

  // 13. Check node background colors match EA conventions
  const colorIssues = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node').forEach(node => {
      const label = node.querySelector('.uml-node__label')?.textContent?.trim() || '';
      const bg = getComputedStyle(node).backgroundColor;
      // Check for default white/no-background when there should be color
      // EA uses specific colors for enums, abstract classes, etc.
      const type = node.closest('.svelte-flow__node')?.getAttribute('data-type') || '';
      // Just collect for analysis
      results.push({ label: label.substring(0, 30), type, bg });
    });
    return results;
  });
  // Group by type to identify color patterns
  const colorByType = {};
  for (const c of colorIssues) {
    if (!colorByType[c.type]) colorByType[c.type] = new Set();
    colorByType[c.type].add(c.bg);
  }

  // 14. Check for overlapping nodes
  const overlaps = await page.evaluate(() => {
    const nodes = [...document.querySelectorAll('.svelte-flow__node')];
    const rects = nodes.map(n => ({
      id: n.getAttribute('data-id'),
      type: n.getAttribute('data-type'),
      rect: n.getBoundingClientRect(),
    }));
    const overlaps = [];
    for (let i = 0; i < rects.length; i++) {
      for (let j = i + 1; j < rects.length; j++) {
        const a = rects[i].rect;
        const b = rects[j].rect;
        if (rects[i].type === 'diagram_frame' || rects[j].type === 'diagram_frame') continue;
        if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) {
          const overlapArea = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
                              Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
          if (overlapArea > 100) { // Significant overlap
            overlaps.push({ id1: rects[i].id, id2: rects[j].id, area: overlapArea });
          }
        }
      }
    }
    return overlaps;
  });
  if (overlaps.length > 0) {
    issues.push({
      type: 'overlapping_nodes',
      detail: `${overlaps.length} node pairs overlap significantly`,
    });
  }

  return { issues, ok, colorByType };
}

async function run() {
  console.log('=== ADR-089: Comprehensive EA Rendering Fidelity Audit ===\n');

  const token = await getToken();
  console.log('Fetching diagram inventories...');

  const [aixmDiagrams, fixmDiagrams] = await Promise.all([
    fetchAllDiagrams(token, SETS.AIXM),
    fetchAllDiagrams(token, SETS.FIXM),
  ]);
  console.log(`AIXM: ${aixmDiagrams.length} diagrams, FIXM: ${fixmDiagrams.length} diagrams\n`);

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });

  // Login
  const loginPage = await context.newPage();
  await loginPage.goto('http://localhost:5173/login');
  await loginPage.waitForLoadState('networkidle');
  await loginPage.fill('input[name="username"], input[type="text"]', 'admin');
  await loginPage.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await loginPage.click('button[type="submit"]');
  await loginPage.waitForTimeout(2000);

  const allDiagrams = [
    ...aixmDiagrams.map(d => ({ ...d, model: 'AIXM' })),
    ...fixmDiagrams.map(d => ({ ...d, model: 'FIXM' })),
  ];

  const allIssues = [];
  const page = loginPage;

  for (let i = 0; i < allDiagrams.length; i++) {
    const d = allDiagrams[i];
    const pct = Math.round((i / allDiagrams.length) * 100);
    process.stdout.write(`\r[${pct}%] Auditing ${d.model}/${d.name} (${i + 1}/${allDiagrams.length})...`);

    try {
      const apiData = await fetchDiagramDetail(token, d.id);
      const result = await auditDiagram(page, d.id, d.name, apiData);

      if (result.issues.length > 0) {
        allIssues.push({
          model: d.model,
          id: d.id,
          name: d.name,
          diagramType: d.diagram_type,
          issues: result.issues,
          ok: result.ok,
        });
      }
    } catch (err) {
      allIssues.push({
        model: d.model,
        id: d.id,
        name: d.name,
        diagramType: d.diagram_type,
        issues: [{ type: 'audit_error', detail: err.message?.substring(0, 200) }],
        ok: [],
      });
    }
  }

  console.log('\n\n=== AUDIT RESULTS ===\n');

  // Categorize issues
  const issuesByType = {};
  for (const d of allIssues) {
    for (const issue of d.issues) {
      if (!issuesByType[issue.type]) issuesByType[issue.type] = [];
      issuesByType[issue.type].push({ ...issue, diagram: d.name, model: d.model, id: d.id });
    }
  }

  // Print summary
  const totalDiagrams = allDiagrams.length;
  const diagWithIssues = allIssues.length;
  console.log(`Total diagrams: ${totalDiagrams}`);
  console.log(`Diagrams with issues: ${diagWithIssues}`);
  console.log(`Diagrams clean: ${totalDiagrams - diagWithIssues}\n`);

  console.log('--- Issue Categories ---\n');
  for (const [type, items] of Object.entries(issuesByType).sort((a, b) => b[1].length - a[1].length)) {
    console.log(`### ${type} (${items.length} occurrences)`);
    // Show affected diagrams
    const uniqueDiagrams = [...new Set(items.map(i => `${i.model}/${i.diagram}`))];
    console.log(`  Affected diagrams: ${uniqueDiagrams.length}`);
    // Show sample details
    for (const item of items.slice(0, 3)) {
      console.log(`  - ${item.model}/${item.diagram}: ${item.detail}`);
    }
    if (items.length > 3) console.log(`  ... and ${items.length - 3} more`);
    console.log();
  }

  // Write detailed results to JSON
  const output = {
    timestamp: new Date().toISOString(),
    summary: { totalDiagrams, diagWithIssues, cleanDiagrams: totalDiagrams - diagWithIssues },
    issuesByType: Object.fromEntries(
      Object.entries(issuesByType).map(([type, items]) => [
        type,
        { count: items.length, affectedDiagrams: [...new Set(items.map(i => i.diagram))].length, samples: items.slice(0, 10) },
      ])
    ),
    allFindings: allIssues,
  };

  const fs = await import('fs');
  fs.writeFileSync('/tmp/adr089-audit-results.json', JSON.stringify(output, null, 2));
  console.log('\nDetailed results saved to /tmp/adr089-audit-results.json');

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
