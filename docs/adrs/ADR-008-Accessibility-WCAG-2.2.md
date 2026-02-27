# ADR-008: Accessibility — WCAG 2.2 Compliance

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-008 |
| **Initiative** | Iris Accessibility |
| **Proposed By** | The CISO (Cat) / The Architect (Bear) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** building Iris as an enterprise architectural modelling tool that must be accessible to all users — including architects and stakeholders with visual, motor, cognitive, or auditory disabilities — across interactive canvas editing, model browsing, and administrative interfaces,

**facing** the choice between WCAG 2.1 Level AA (the previous standard and common legal baseline), WCAG 2.2 Level AA (the current W3C Recommendation with 9 new success criteria addressing cognitive disabilities, motor impairments, and mobile accessibility), and WCAG 2.2 Level AAA (the maximum conformance level with 87 total criteria),

**we decided for** WCAG 2.2 Level AA as the conformance target, which requires meeting all 56 Level A and AA success criteria (32 A + 24 AA), with selected Level AAA criteria adopted where they directly benefit interactive modelling tool users — specifically 2.4.13 Focus Appearance and 2.1.3 Keyboard (No Exception),

**and neglected** WCAG 2.1 Level AA (which lacks the 9 new criteria in 2.2 that directly address Iris's interaction patterns — dragging movements, target sizes, focus visibility, and accessible authentication), full WCAG 2.2 Level AAA (which includes criteria impractical for an interactive canvas tool — e.g., 1.2.6 Sign Language for all media, 3.1.5 Reading Level requiring lower secondary education level, 1.4.8 Visual Presentation requiring user-selectable foreground/background colours), and no formal standard (which contradicts success criterion 3 and NZ ITSM requirements),

**to achieve** full accessibility for all users of Iris regardless of ability, compliance with NZ ITSM requirements and international accessibility law, a concrete and testable conformance target that the Dragon can evaluate against, and specific guidance for the interactive canvas (drag alternatives, keyboard navigation, focus management) that WCAG 2.2's new criteria provide,

**accepting that** WCAG 2.2 Level AA compliance on an interactive modelling canvas is significantly more challenging than on a standard web application, that some canvas interactions will require custom ARIA patterns not covered by existing component libraries, that automated testing covers approximately 30-40% of WCAG criteria with the remainder requiring manual and assistive technology testing, and that two selected AAA criteria add scope but are essential for a keyboard-heavy modelling tool.

---

## Conformance Target

### Level AA (Mandatory) — 56 Criteria

All 32 Level A and 24 Level AA success criteria from WCAG 2.2 must be met.

### Selected Level AAA (Adopted) — 2 Additional Criteria

| Criterion | Level | Rationale for Adoption |
|-----------|-------|----------------------|
| 2.4.13 Focus Appearance | AAA | Interactive modelling requires strong focus indicators. Users must see exactly where focus is on a complex canvas with many interactive elements. |
| 2.1.3 Keyboard (No Exception) | AAA | All canvas functionality must be keyboard-operable without exception. An interactive modelling tool that requires a mouse for any operation excludes motor-impaired users. |

---

## WCAG 2.2 Principles Applied to Iris

### 1. Perceivable

| Guideline | Iris-Specific Concerns |
|-----------|----------------------|
| 1.1 Text Alternatives | Every entity, relationship, and diagram element on the canvas needs text alternatives. SVG-based canvas elements need `<title>` and `<desc>`. Icons need `aria-label`. |
| 1.3 Adaptable | Canvas layout must convey relationships through structure, not just visual position. ARIA landmarks for canvas regions. Meaningful DOM order. |
| 1.4 Distinguishable | 4.5:1 contrast ratio for text, 3:1 for non-text UI (entity borders, relationship lines, canvas controls). Colour must not be the sole means of conveying entity types or relationship states. Text resize to 200% without loss of content. Reflow at 320px width for non-canvas content. |

### 2. Operable

| Guideline | Iris-Specific Concerns |
|-----------|----------------------|
| 2.1 Keyboard Accessible | **Critical for Iris.** Every canvas operation must have a keyboard equivalent: entity selection (Tab/Arrow), entity creation (keyboard shortcut), relationship drawing (keyboard mode), zoom (Ctrl+/Ctrl-), pan (Arrow keys when canvas focused). No keyboard traps in canvas or modal dialogs. |
| 2.4 Navigable | Skip links to canvas, sidebar, and toolbar regions. Logical focus order through canvas entities. Focus not obscured by toolbars or panels (2.4.11 — new in 2.2). |
| 2.5 Input Modalities | **2.5.7 Dragging Movements (new in 2.2) is critical.** Entity repositioning, relationship drawing, and canvas panning all use drag. Every drag operation must have a non-drag alternative (arrow keys, coordinate input, click-click-connect for relationships). Target sizes minimum 24x24 CSS pixels (2.5.8). |

### 3. Understandable

| Guideline | Iris-Specific Concerns |
|-----------|----------------------|
| 3.1 Readable | Page language declared. Technical terms (UML, ArchiMate) are domain-expected. |
| 3.2 Predictable | Consistent navigation across Browse Mode and Edit Mode. Help mechanism in consistent location (3.2.6 — new in 2.2). No unexpected context changes on focus or input. |
| 3.3 Input Assistance | Entity property forms need labels, error identification, and error suggestions. Redundant entry avoided in multi-step entity creation (3.3.7 — new in 2.2). Authentication without cognitive function tests (3.3.8 — new in 2.2). |

### 4. Robust

| Guideline | Iris-Specific Concerns |
|-----------|----------------------|
| 4.1 Compatible | All interactive canvas elements expose name, role, and value to assistive technologies (4.1.2). Status messages for canvas operations use `aria-live` regions (4.1.3). Custom canvas components use appropriate ARIA roles and states. |

---

## WCAG 2.2 New Criteria — Iris Impact Assessment

| New Criterion | Level | Impact on Iris | Implementation Phase |
|---------------|-------|---------------|---------------------|
| 2.4.11 Focus Not Obscured (Minimum) | AA | High — floating toolbars and panels must not obscure focused canvas elements | Phase D, E |
| 2.4.12 Focus Not Obscured (Enhanced) | AAA | Not adopted — minimum is sufficient | — |
| 2.4.13 Focus Appearance | AAA | **Adopted** — canvas focus indicators must be visible with 3:1 contrast and 2px perimeter | Phase D, E |
| 2.5.7 Dragging Movements | AA | **Critical** — every drag operation on canvas needs a non-drag alternative | Phase E |
| 2.5.8 Target Size (Minimum) | AA | High — entity handles, toolbar buttons, canvas controls all need 24x24px minimum | Phase D, E |
| 3.2.6 Consistent Help | A | Low — help mechanism in consistent location across pages | Phase D |
| 3.3.7 Redundant Entry | A | Low — auto-populate previously entered data in multi-step forms | Phase D, E |
| 3.3.8 Accessible Authentication (Minimum) | AA | Medium — login must not require cognitive tests, support password managers | Phase D |
| 3.3.9 Accessible Authentication (Enhanced) | AAA | Not adopted | — |

---

## Theme System

| Mode | Requirement | Rationale |
|------|------------|-----------|
| Light | Default theme | Standard presentation |
| Dark | User-selectable | Reduced eye strain, low-light environments |
| System | Follows OS `prefers-color-scheme` | Automatic matching to user preference |
| High Contrast | User-selectable | WCAG 1.4.6 Enhanced contrast (7:1 text, 4.5:1 non-text) for low-vision users |

All modes must independently meet WCAG 2.2 Level AA contrast requirements. Theme switching must not cause loss of content or functionality.

---

## Testing Strategy

| Method | Coverage | When |
|--------|----------|------|
| **Automated (axe-core / Lighthouse)** | ~30-40% of criteria (structure, ARIA, contrast, alt text) | CI pipeline on every commit |
| **Manual keyboard testing** | Keyboard access, focus order, focus visibility, trap detection | Every feature branch |
| **Screen reader testing** | NVDA (Windows), VoiceOver (macOS), Orca (Linux) | Phase E completion, Phase G |
| **Colour contrast analyser** | All colour combinations in all themes | Phase D, theme changes |
| **Reduced motion testing** | `prefers-reduced-motion` respected, no essential motion | Phase E |
| **Zoom testing** | 200% text zoom, 400% page zoom, reflow at 320px | Phase D, E, F |
| **WCAG 2.2 audit** | Full criterion-by-criterion review | Phase G |

---

## Options Considered

### Option 1: WCAG 2.2 Level AA + Selected AAA (Selected)

**Pros:**
- Current W3C Recommendation (October 2023) — most up-to-date standard
- 9 new criteria directly address Iris's interaction patterns (dragging, focus, target sizes, auth)
- Level AA is the standard legal/regulatory baseline internationally
- Selected AAA criteria (Focus Appearance, Keyboard No Exception) are essential for a modelling tool
- Concrete, testable — the Dragon can evaluate against it

**Cons:**
- More challenging than WCAG 2.1 AA (9 additional criteria)
- Canvas accessibility is the hardest category of web accessibility
- Two adopted AAA criteria add scope

### Option 2: WCAG 2.1 Level AA (Rejected)

**Pros:**
- Well-established, widely understood
- Easier to achieve (fewer criteria)

**Cons:**
- Missing 9 criteria that directly address Iris's needs (drag alternatives, focus management, target sizes)
- Already superseded by WCAG 2.2

**Why rejected:** WCAG 2.2's new criteria are not optional extras for Iris — they directly address the interaction patterns of an interactive modelling tool. Building without drag alternatives (2.5.7) or focus visibility (2.4.11) and then retrofitting is more expensive than building them in.

### Option 3: WCAG 2.2 Level AAA (Rejected)

**Pros:**
- Maximum accessibility
- Exceeds all regulatory requirements

**Cons:**
- 31 additional AAA criteria, many impractical for interactive canvas (sign language for media, reading level constraints, visual presentation requiring user-selectable colours)
- W3C itself notes that "it is not possible to satisfy all Level AAA Success Criteria for some content"
- Disproportionate effort for marginal accessibility gain beyond AA + selected AAA

**Why rejected:** Full AAA includes criteria that cannot reasonably be met for an interactive canvas application. Selective adoption of relevant AAA criteria is the pragmatic approach.

### Option 4: No Formal Standard (Rejected)

**Why rejected:** Contradicts success criterion 3 ("Full WCAG accessibility"), NZ ITSM requirements, and the quest's commitment to quality.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | WCAG 2.2 AA + selected AAA as conformance target | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The CISO (Cat) / The Architect (Bear) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | SvelteKit/shadcn-svelte accessibility capabilities |
| Depends On | ADR-003 | Architectural Vision | The Lens layer implements accessibility |
| Relates To | ADR-005 | RBAC Design | 3.3.8 Accessible Authentication applies to login |
| Relates To | TBD | NZ ITSM Control Mapping | Accessibility is part of compliance |
| Enables | TBD | Canvas Accessibility Implementation | Phase E requires drag alternatives and keyboard canvas |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-008-A | WCAG 2.2 Compliance Matrix | Technical Specification | [specs/SPEC-008-A-WCAG-2.2-Compliance.md](specs/SPEC-008-A-WCAG-2.2-Compliance.md) |
| EXT-001 | [WCAG 2.2 W3C Recommendation](https://www.w3.org/TR/WCAG22/) | External Standard | W3C |
| EXT-002 | [What's New in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) | External Reference | W3C WAI |
| EXT-003 | [How to Meet WCAG (Quick Reference)](https://www.w3.org/WAI/WCAG22/quickref/) | External Reference | W3C WAI |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
