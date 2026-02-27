# ADR-002: Frontend Technology Stack Selection

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-002 |
| **Initiative** | Iris Frontend Tech Stack |
| **Proposed By** | The Architect (Bear) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** selecting a frontend technology stack for Iris, a web-based architectural modelling tool requiring an interactive canvas with UML and ArchiMate support, full WCAG accessibility, light/dark/system theming, and complex state management for entity versioning and undo/redo,

**facing** the challenge that no single library provides built-in UML, ArchiMate, and sequence diagram support out of the box, that commercial diagramming libraries (GoJS at $3,995/license, JointJS+ at $2,990/license, tldraw at $6,000/year) conflict with the open-source-only constraint, and that the framework choice impacts accessibility tooling maturity, state management patterns, developer experience, and long-term maintainability for a small team of 2-5,

**we decided for** SvelteKit/Svelte 5 with Svelte Flow (xyflow), shadcn-svelte + Bits UI, Tailwind CSS, and TypeScript as the frontend stack,

**and neglected** React + Vite + React Flow (which offered the largest ecosystem, most mature accessibility tooling with ARIAKit/React Aria/Radix UI, and strongest state management with Zustand, but at the cost of more boilerplate and lower raw performance), React + JointJS (which offered built-in UML and sequence diagram shapes but required commercial JointJS+ licensing for essential UI plugins), Vue 3 + Nuxt (which offered a good middle ground but lacked the performance characteristics and canvas library pairing), and Angular (which offered the best TypeScript integration and built-in accessibility CDK but had the steepest learning curve and declining market share),

**to achieve** superior runtime performance for canvas-heavy interactive modelling (Svelte 5 benchmarks at 96 Lighthouse score with no virtual DOM overhead), cleaner developer experience with less boilerplate (Svelte 5 runes for reactive state), smaller bundle sizes for the interactive canvas application, and a modern compiler-first architecture that benefits interactive visualisation applications,

**accepting that** the Svelte ecosystem is significantly smaller than React's (2.07M vs 28.5M weekly npm downloads), accessibility primitives are less mature and will require more custom building, the Svelte Flow library is younger than React Flow (same xyflow team but smaller community), the developer talent pool is approximately 10x smaller than React's (affecting hiring), and UML, ArchiMate, and sequence diagram notation layers must be built entirely from scratch as custom Svelte Flow nodes.

---

## Options Considered

### Option 1: SvelteKit + Svelte Flow (Selected)

| Aspect | Detail |
|--------|--------|
| **Framework** | SvelteKit / Svelte 5 |
| **Canvas** | Svelte Flow (xyflow) — MIT, same API as React Flow |
| **UI Components** | shadcn-svelte + Bits UI |
| **State** | Svelte 5 runes ($state, $derived, $effect) |
| **Styling** | Tailwind CSS |
| **Performance** | 96 Lighthouse score, no virtual DOM, compiler-first |
| **NPM Downloads** | ~2.07M weekly (Svelte) |

**Pros:**
- Best raw runtime performance for canvas-heavy interactive apps
- Compiler-first approach: smaller bundles, faster execution, lower CPU during UI updates
- Svelte 5 runes provide built-in reactive state management without external libraries
- Less boilerplate, faster developer velocity
- xyflow team maintains Svelte Flow with same API design as React Flow
- Compile-time accessibility warnings (unique to Svelte)
- CSS custom properties for clean theming architecture

**Cons:**
- Smallest ecosystem of the evaluated frameworks
- Accessibility tooling less mature — no equivalent to ARIAKit or React Aria
- Svelte Flow community ~10x smaller than React Flow
- Smaller developer talent pool affects hiring
- TypeScript support historically weakest (improving rapidly with Svelte 5)
- All UML/ArchiMate/sequence diagram shapes must be custom-built

### Option 2: React + Vite + React Flow (Rejected)

| Aspect | Detail |
|--------|--------|
| **Framework** | React 19 + Vite |
| **Canvas** | React Flow (xyflow) — MIT, 35k GitHub stars, 4.38M weekly downloads |
| **UI Components** | shadcn/ui + Radix UI |
| **State** | Zustand (bypasses React render cycle for 60fps) |
| **Styling** | Tailwind CSS |
| **Performance** | Lower Lighthouse scores than Svelte, virtual DOM overhead |
| **NPM Downloads** | ~28.5M weekly (React) |

**Pros:**
- Largest ecosystem by far (847k+ job postings, 28.5M weekly downloads)
- Most mature accessibility tooling (ARIAKit, React Aria by Adobe, Radix UI)
- Zustand provides 60fps canvas updates bypassing React's render cycle
- React Foundation (Feb 2026) under Linux Foundation — strongest long-term viability signal
- React Flow has 4.38M weekly downloads and extensive documentation
- Deepest state management ecosystem (Zustand, XState, Immer)
- shadcn/ui + Radix UI provides accessible, minimalistic components with dark mode

**Cons:**
- Virtual DOM introduces overhead for high-frequency canvas updates
- More boilerplate than Svelte
- Larger bundle sizes
- Still requires custom UML/ArchiMate/sequence diagram shapes

**Why rejected:** The team prioritised runtime performance and developer experience over ecosystem size. For a small team of 2-5 building a canvas-heavy interactive application, Svelte's performance advantages and cleaner DX were deemed more valuable than React's larger ecosystem. The accessibility gap is acknowledged as a trade-off that requires additional custom work.

### Option 3: React + JointJS (Rejected)

| Aspect | Detail |
|--------|--------|
| **Canvas** | JointJS (MPL 2.0 open source) / JointJS+ ($2,990/license commercial) |
| **UML Support** | Built-in UML class diagrams, sequence diagrams |

**Pros:**
- Built-in UML and sequence diagram shapes out of the box
- Purpose-built for diagramming with shape libraries
- SVG-based rendering aids accessibility
- Virtual rendering for large diagrams

**Cons:**
- Open source version lacks essential UI plugins (snapping, zooming, context menus)
- JointJS+ required for full functionality at $2,990/license + $1,490/year renewal
- Smaller community than React Flow (4.9k stars, 20.7k weekly downloads)
- Less flexible for custom rendering

**Why rejected:** Open-source-only constraint eliminates JointJS+ features. The open source version requires building all UI interaction plugins from scratch, negating the advantage of built-in diagram shapes.

### Other Eliminated Candidates

| Library | Reason for Elimination |
|---------|----------------------|
| **GoJS** | Commercial — $3,995 per developer licensing |
| **tldraw** | Commercial — $6,000/year per team |
| **Excalidraw** | Hand-drawn aesthetic wrong for enterprise architecture; accessibility audit issues |
| **Konva** | Canvas-based (bitmap) rendering fails WCAG — screen readers cannot traverse canvas elements |
| **mxGraph** | Archived/deprecated since November 2020 |
| **D3.js** | Too low-level — data visualisation library, not a diagramming framework |
| **Rete.js** | Designed for visual programming/node editors, not architectural diagramming |

---

## Key Research Data

### Framework Comparison

| Metric | React | SvelteKit | Vue 3 | Angular |
|--------|-------|-----------|-------|---------|
| NPM Weekly Downloads | 28.5M | 2.07M | 6.4M | 2.5M |
| GitHub Stars | 207-223K | ~85K | ~matches React | 90-98K |
| Job Postings | 847K+ | Smallest | ~80K | ~120K |
| Lighthouse Performance | Lower | 96 | Moderate | Lower |
| TypeScript | Good (not native) | Improving | Good (Composition API) | Best (native) |
| A11y Ecosystem | Best | Decent (compiler warnings) | Good | Strong (CDK a11y) |

### Canvas Library Comparison

| Metric | React Flow | Svelte Flow | JointJS (open source) |
|--------|-----------|-------------|----------------------|
| GitHub Stars | 35.2K (shared xyflow repo) | Same repo | 4.9K |
| NPM Weekly Downloads | 4.38M | Younger, smaller | 20.7K |
| License | MIT | MIT | MPL 2.0 |
| Built-in UML | No | No | Yes |
| Built-in Sequence | No | No | Yes |
| Custom Nodes | Full React components | Full Svelte components | JointJS element model |
| Accessibility | Good (keyboard, ARIA) | Good (keyboard, ARIA) | Good (SVG-based) |

---

## Custom Build Requirements

With the selected stack, the following must be built from scratch:

1. **UML shape components** — Custom Svelte Flow nodes for UML notation
2. **ArchiMate shape components** — Custom Svelte Flow nodes for ArchiMate notation
3. **Sequence diagram engine** — Svelte Flow is node-based, not timeline-based; sequence diagram support requires a custom rendering approach
4. **Accessibility layer** — Additional ARIA patterns, focus management, and screen reader support beyond what shadcn-svelte provides
5. **Entity relationship web visualisation** — Force-directed or hierarchical graph view of entity relationships

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Proceed with SvelteKit stack | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The Architect (Bear) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Enables | TBD | Data Foundation Schema | Tech stack informs API contract design |
| Enables | TBD | Accessibility Strategy | Framework choice shapes accessibility approach |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-002-A | Frontend Stack Configuration | Technical Specification | [specs/SPEC-002-A-Frontend-Stack.md](./specs/SPEC-002-A-Frontend-Stack.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
