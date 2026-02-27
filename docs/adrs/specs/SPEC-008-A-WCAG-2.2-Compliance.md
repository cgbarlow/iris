# SPEC-008-A: WCAG 2.2 Compliance Matrix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-008-A |
| **ADR Reference** | [ADR-008: Accessibility — WCAG 2.2 Compliance](../ADR-008-Accessibility-WCAG-2.2.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification provides the complete WCAG 2.2 compliance matrix for Iris, mapping every applicable success criterion to Iris-specific implementation requirements, responsible build phase, and compliance status.

**Conformance Target:** WCAG 2.2 Level AA + selected Level AAA (2.4.13, 2.1.3)
**Total Applicable Criteria:** 58 (56 AA + 2 adopted AAA)

---

## Principle 1: Perceivable

> Information and user interface components must be presentable to users in ways they can perceive.

### 1.1 Text Alternatives

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **1.1.1 Non-text Content** | A | All canvas entities have text alternatives via `aria-label` or `<title>/<desc>` in SVG. Icons use `aria-label`. Decorative images use `aria-hidden="true"`. Entity type icons include accessible names. Diagram thumbnails have alt text describing the model. | D, E | Pending |

### 1.2 Time-based Media

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **1.2.1 Audio-only and Video-only** | A | Not applicable — Iris does not include audio or video content. | — | N/A |
| **1.2.2 Captions (Prerecorded)** | A | Not applicable. | — | N/A |
| **1.2.3 Audio Description or Media Alternative** | A | Not applicable. | — | N/A |
| **1.2.4 Captions (Live)** | AA | Not applicable. | — | N/A |
| **1.2.5 Audio Description (Prerecorded)** | AA | Not applicable. | — | N/A |

### 1.3 Adaptable

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **1.3.1 Info and Relationships** | A | Semantic HTML for all non-canvas UI. ARIA landmarks for page regions (nav, main, aside). Canvas entity relationships conveyed programmatically via ARIA tree or grid patterns, not just visual lines. Headings used for section structure. Tables use `<th>` with scope. Form inputs use `<label>`. | D, E, F | Pending |
| **1.3.2 Meaningful Sequence** | A | DOM order matches visual order. Canvas entity tab order follows logical reading sequence (left-to-right, top-to-bottom by default, user-configurable). | D, E | Pending |
| **1.3.3 Sensory Characteristics** | A | Instructions do not rely solely on shape, colour, size, visual location, or sound. "Click the blue button" → "Click the Save button". Entity types distinguished by label + icon, not colour alone. | D, E, F | Pending |
| **1.3.4 Orientation** | AA | Content displays in both portrait and landscape. Canvas adapts to viewport orientation. No orientation lock. | D, E | Pending |
| **1.3.5 Identify Input Purpose** | AA | Login form inputs use `autocomplete` attributes (`username`, `current-password`, `new-password`). Entity property form inputs use appropriate `autocomplete` where applicable. | D | Pending |

### 1.4 Distinguishable

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **1.4.1 Use of Color** | A | Entity types are not distinguished by colour alone — always include icon + label. Relationship types use line style (solid/dashed/dotted) in addition to colour. Error states use icon + text, not just red colour. Selected state uses outline + colour. | D, E | Pending |
| **1.4.2 Audio Control** | A | Not applicable — Iris does not include auto-playing audio. | — | N/A |
| **1.4.3 Contrast (Minimum)** | AA | Text: 4.5:1 contrast ratio (3:1 for large text ≥18pt or ≥14pt bold). Applies in all four themes (light, dark, system, high contrast). All entity labels, toolbar text, sidebar text, form labels. | D | Pending |
| **1.4.4 Resize Text** | AA | Text resizes to 200% without loss of content or functionality. Canvas entity labels scale with zoom. Non-canvas UI uses relative units (rem/em). | D, E | Pending |
| **1.4.5 Images of Text** | AA | No images of text. All text rendered as actual text, including canvas entity labels (SVG `<text>` or HTML overlay, not rasterised). | E | Pending |
| **1.4.10 Reflow** | AA | At 400% zoom (320px equivalent width), non-canvas content reflows to single column without horizontal scrolling. Canvas itself may scroll (canvas is inherently 2D) but controls, sidebar, and navigation reflow. | D, F | Pending |
| **1.4.11 Non-text Contrast** | AA | Canvas entity borders, relationship lines, focus indicators, form field boundaries, and interactive control boundaries all meet 3:1 contrast ratio against adjacent colours. In all themes. | D, E | Pending |
| **1.4.12 Text Spacing** | AA | Content remains functional with user-overridden text spacing: line height 1.5x, paragraph spacing 2x, letter spacing 0.12em, word spacing 0.16em. No text clipping or overlap. | D | Pending |
| **1.4.13 Content on Hover or Focus** | AA | Tooltips and popovers: dismissible (Escape key), hoverable (user can move pointer to tooltip without it closing), persistent (remains visible until user dismisses or moves focus). | D, E | Pending |

---

## Principle 2: Operable

> User interface components and navigation must be operable.

### 2.1 Keyboard Accessible

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **2.1.1 Keyboard** | A | All functionality operable via keyboard. Canvas: Tab/Shift+Tab for entity focus, Arrow keys for navigation between entities, Enter/Space for selection, keyboard shortcuts for create/delete/connect. Toolbar: standard Tab navigation. Forms: standard Tab + Enter. | D, E | Pending |
| **2.1.2 No Keyboard Trap** | A | Focus can always be moved away from any component using standard keys (Tab, Shift+Tab, Escape). Canvas does not trap focus — Escape exits canvas focus to surrounding UI. Modal dialogs trap focus within the dialog but Escape closes them. | D, E | Pending |
| **2.1.3 Keyboard (No Exception)** | AAA | **Adopted.** Every single canvas operation has a keyboard equivalent, no exceptions. Entity creation, repositioning (arrow keys), resizing, relationship drawing (keyboard connection mode), zoom, pan, selection, multi-select. | E | Pending |
| **2.1.4 Character Key Shortcuts** | A | Single-character keyboard shortcuts (if any) can be turned off or remapped. Canvas shortcuts documented and configurable. | D, E | Pending |

### 2.2 Enough Time

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **2.2.1 Timing Adjustable** | A | Session timeout (JWT expiry) provides warning before expiration with option to extend. No time limits on canvas operations. | D | Pending |
| **2.2.2 Pause, Stop, Hide** | A | No auto-updating content. Canvas animations (if any) respect `prefers-reduced-motion`. Loading indicators can be paused. | D, E | Pending |

### 2.3 Seizures and Physical Reactions

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **2.3.1 Three Flashes or Below Threshold** | A | No content flashes more than 3 times per second. Canvas transitions use smooth animations, not flashing. Theme transitions are instant, not animated. | D, E | Pending |

### 2.4 Navigable

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **2.4.1 Bypass Blocks** | A | Skip links: "Skip to canvas", "Skip to sidebar", "Skip to main content". ARIA landmarks for all page regions. | D | Pending |
| **2.4.2 Page Titled** | A | Every page has a descriptive `<title>`: "Entity Name — Model Name — Iris", "Browse Models — Iris", "Edit: Model Name — Iris". | D | Pending |
| **2.4.3 Focus Order** | A | Tab order follows logical visual sequence: skip links → header → sidebar navigation → main content/canvas → footer. Within canvas: entities follow spatial order (configurable). | D, E | Pending |
| **2.4.4 Link Purpose (In Context)** | A | All links have descriptive text. "View model" not "Click here". Entity links include entity name. Breadcrumbs use meaningful text. | D, F | Pending |
| **2.4.5 Multiple Ways** | AA | Models accessible via: navigation sidebar, search, deep link URL, bookmarks/stars, entity relationship web, breadcrumbs. | D, F | Pending |
| **2.4.6 Headings and Labels** | AA | Descriptive headings for all sections. Form labels describe purpose. Canvas regions labelled with `aria-label`. | D, E, F | Pending |
| **2.4.7 Focus Visible** | AA | Custom focus indicator: 2px solid outline, high contrast colour per theme, visible on all interactive elements including canvas entities. Never hidden by `outline: none` without replacement. | D, E | Pending |
| **2.4.11 Focus Not Obscured (Minimum)** | AA | **New in 2.2.** Floating toolbar, sticky header, and property panel must not entirely obscure focused canvas elements. Auto-scroll or auto-reposition to keep focused element visible. | D, E | Pending |
| **2.4.13 Focus Appearance** | AAA | **Adopted.** Focus indicator: area ≥ 2px perimeter of the component, contrast ratio ≥ 3:1 between focused and unfocused states. Custom focus ring on all canvas entities, toolbar buttons, form elements. | D, E | Pending |

### 2.5 Input Modalities

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **2.5.1 Pointer Gestures** | A | No multipoint or path-based gestures required. Pinch-to-zoom has keyboard alternative (Ctrl+/Ctrl-). | E | Pending |
| **2.5.2 Pointer Cancellation** | A | Drag operations: `pointerup` completes the action, not `pointerdown`. Moving pointer away cancels. Undo available for completed operations. | E | Pending |
| **2.5.3 Label in Name** | A | Visible button text matches accessible name. "Save Model" button has `aria-label="Save Model"` (or uses visible text as accessible name). | D | Pending |
| **2.5.4 Motion Actuation** | A | No motion-activated features (shake, tilt). | — | N/A |
| **2.5.6 Concurrent Input Mechanisms** | A | Input modality not restricted — users can switch between keyboard, mouse, touch, and voice at any time. | D, E | Pending |
| **2.5.7 Dragging Movements** | AA | **New in 2.2 — Critical for Iris.** Every drag operation has a non-drag alternative: (1) Entity reposition → arrow keys or coordinate input dialog, (2) Relationship drawing → keyboard connection mode (select source, press Connect, select target), (3) Canvas pan → arrow keys or scroll, (4) Resize → keyboard resize mode with arrow keys, (5) Reorder in lists → up/down buttons. | E | Pending |
| **2.5.8 Target Size (Minimum)** | AA | **New in 2.2.** All interactive targets: minimum 24x24 CSS pixels. Applies to: toolbar buttons, canvas entity handles, resize handles, connection points, sidebar items, form controls. Smaller inline links excepted if adequate spacing. | D, E | Pending |

---

## Principle 3: Understandable

> Content must be comprehensible to users.

### 3.1 Readable

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **3.1.1 Language of Page** | A | `<html lang="en">` on all pages. | D | Pending |
| **3.1.2 Language of Parts** | AA | Content in other languages (if any) marked with `lang` attribute. Entity names/descriptions entered by users are assumed to be in the page language. | D | Pending |

### 3.2 Predictable

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **3.2.1 On Focus** | A | No context change on focus. Focusing a canvas entity does not navigate away or open a modal. | D, E | Pending |
| **3.2.2 On Input** | A | No context change on input unless user is advised. Selecting an entity type in a dropdown does not auto-submit. | D, E | Pending |
| **3.2.3 Consistent Navigation** | AA | Navigation sidebar, header, and toolbar in same position across all pages. Browse Mode and Edit Mode share consistent navigation structure. | D | Pending |
| **3.2.4 Consistent Identification** | AA | Same function has same label everywhere. "Save" is always "Save", not sometimes "Submit" or "Update". | D | Pending |
| **3.2.6 Consistent Help** | A | **New in 2.2.** Help link/button in consistent location (header or footer) across all pages. Same relative position to other navigation elements. | D | Pending |

### 3.3 Input Assistance

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **3.3.1 Error Identification** | A | Form errors identified in text, associated with the input via `aria-describedby` or `aria-errormessage`. Error icon + text description. | D | Pending |
| **3.3.2 Labels or Instructions** | A | All form inputs have visible labels. Required fields indicated. Entity property forms include instructions where needed. | D, E | Pending |
| **3.3.3 Error Suggestion** | AA | When input error is detected and correction is known, suggest correction. "Entity name must be unique — 'Payment Service' already exists. Try 'Payment Service v2'." | D, E | Pending |
| **3.3.4 Error Prevention (Legal, Financial, Data)** | AA | Entity deletion requires confirmation dialog. Rollback requires confirmation with impact summary. Bulk operations are reversible or require confirmation. | D, E | Pending |
| **3.3.7 Redundant Entry** | A | **New in 2.2.** Previously entered entity data auto-populated in multi-step creation. Search terms preserved when navigating back. | D, E | Pending |
| **3.3.8 Accessible Authentication (Minimum)** | AA | **New in 2.2.** Login does not require cognitive function tests (CAPTCHAs, puzzles). Password field supports paste (for password managers). Copy-paste of one-time codes supported if MFA added. | D | Pending |

---

## Principle 4: Robust

> Content must be robust enough to be interpreted by assistive technologies.

### 4.1 Compatible

| Criterion | Level | Iris Implementation | Phase | Status |
|-----------|-------|---------------------|-------|--------|
| **4.1.2 Name, Role, Value** | A | All interactive elements expose accessible name, role, and state. Canvas entities: `role="treeitem"` or custom ARIA. Toolbar buttons: `role="button"` with `aria-pressed` for toggles. Sidebar tree: `role="tree"` with `role="treeitem"`. Custom components use appropriate ARIA patterns. | D, E, F | Pending |
| **4.1.3 Status Messages** | AA | Canvas operation feedback via `aria-live="polite"` region: "Entity created", "Relationship added", "Model saved", "3 entities selected". Error notifications via `aria-live="assertive"`. No focus movement for status messages. | D, E | Pending |

---

## Canvas-Specific Accessibility Patterns

The interactive modelling canvas is the highest-risk area for accessibility. These patterns address the unique challenges:

### Entity Navigation

| Operation | Mouse | Keyboard | Screen Reader |
|-----------|-------|----------|---------------|
| Focus entity | Click | Tab / Arrow keys | Announces: "[Entity name], [type], [position]" |
| Select entity | Click | Enter / Space | Announces: "[Entity name] selected" |
| Multi-select | Ctrl+Click | Ctrl+Enter | Announces: "[Entity name] added to selection, [N] selected" |
| Move entity | Drag | Arrow keys (with Shift for larger steps) | Announces: "Moved to [x], [y]" |
| Resize entity | Drag handle | Enter resize mode, Arrow keys | Announces: "Resized to [w] by [h]" |
| Create entity | Double-click canvas | Ctrl+N / Insert | Opens creation dialog |
| Delete entity | Delete key | Delete key (with confirmation) | Announces: "[Entity name] deleted" |
| Connect entities | Drag from port | Select source → C key → select target | Announces: "Connected [source] to [target]" |

### Canvas Zoom and Pan

| Operation | Mouse | Keyboard | Touch |
|-----------|-------|----------|-------|
| Zoom in | Scroll up / Ctrl+Click | Ctrl+= / Ctrl+Plus | Pinch out |
| Zoom out | Scroll down | Ctrl+- / Ctrl+Minus | Pinch in |
| Pan | Middle-click drag / Scroll | Arrow keys (when no entity focused) | Two-finger drag |
| Fit to screen | — | Ctrl+0 | — |
| Zoom to entity | Double-click entity | F key on focused entity | Double-tap entity |

### ARIA Live Region for Canvas

```html
<div aria-live="polite" aria-atomic="false" class="sr-only" id="canvas-announcer">
  <!-- Dynamically updated with canvas operation feedback -->
</div>
```

All canvas operations update this region with human-readable status messages.

---

## Theme Contrast Requirements

| Element | Light Mode | Dark Mode | High Contrast |
|---------|-----------|-----------|---------------|
| Body text | #1a1a1a on #ffffff (15.3:1) | #e5e5e5 on #1a1a1a (13.3:1) | #000000 on #ffffff (21:1) |
| Entity label | 4.5:1 minimum | 4.5:1 minimum | 7:1 minimum |
| Entity border | 3:1 minimum vs background | 3:1 minimum vs background | 4.5:1 minimum |
| Relationship line | 3:1 minimum vs canvas | 3:1 minimum vs canvas | 4.5:1 minimum |
| Focus indicator | 3:1 vs adjacent colours | 3:1 vs adjacent colours | 4.5:1 vs adjacent |
| Interactive control border | 3:1 minimum | 3:1 minimum | 4.5:1 minimum |

---

## Assistive Technology Support Matrix

| AT | Browser | Priority | Testing Phase |
|----|---------|----------|---------------|
| NVDA | Firefox, Chrome (Windows) | Primary | E, G |
| VoiceOver | Safari (macOS, iOS) | Primary | E, G |
| JAWS | Chrome (Windows) | Secondary | G |
| Orca | Firefox (Linux) | Secondary | G |
| Dragon NaturallySpeaking | Chrome (Windows) | Tertiary | G |
| Switch access | Chrome | Tertiary | G |

---

## Automated Testing Tools

| Tool | Purpose | Integration |
|------|---------|-------------|
| axe-core | Runtime accessibility scanning | Vitest unit tests via @axe-core/playwright |
| Playwright | End-to-end accessibility testing | CI pipeline |
| Lighthouse CI | Performance + accessibility audit | CI pipeline |
| pa11y | Automated WCAG compliance checking | CI pipeline |
| Colour Contrast Analyser | Manual contrast verification | Development workflow |

---

## Compliance Tracking

Each criterion status transitions through: `Pending` → `In Progress` → `Implemented` → `Tested` → `Verified`.

Final verification occurs in Phase G as part of the WCAG 2.2 audit (success criterion 3).

---

*This specification implements [ADR-008](../ADR-008-Accessibility-WCAG-2.2.md). WCAG 2.2 reference: [W3C Recommendation](https://www.w3.org/TR/WCAG22/).*
