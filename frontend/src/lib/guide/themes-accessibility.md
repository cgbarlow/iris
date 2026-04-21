# Themes & Accessibility

Iris supports light, dark, and high-contrast themes across the app, plus per-element theming on the canvas. Every canvas operation has a keyboard equivalent — Iris targets WCAG 2.2 Level AA.

## Switching theme

A **theme toggle** sits in the top-right of the header. Cycles between:

- **Light** — default for daytime use.
- **Dark** — default at night / low-light screens.
- **System** — follows your OS preference (auto-switches at sunset on macOS / Windows).

Your choice persists in `localStorage` per browser; open in a new browser and you get System by default.

## High-contrast mode

Some environments (government compliance, screen-reader users) need stronger colour contrast. Iris ships a **High Contrast** theme: black backgrounds, pure-white text, bright primary accents — tested against WCAG 2.2 Level AAA ratios for body text.

Activate from the same theme toggle. All canvas elements re-render against the high-contrast palette.

## Per-diagram / per-element theming

> **Sign in to use this.** Theme overrides require **architect** or above.

Each diagram has a **Theme** dropdown in the toolbar. Pre-seeded themes cover the standard notation palettes (ArchiMate business yellow, C4 blue, DoView soft pastels). Admins can create custom themes under **Admin → Settings → Themes**:

- **Colour overrides** per element type (background, border, text).
- **Font overrides** (family, size, weight).
- **Edge styling** (stroke width, dash pattern).
- **Per-element overrides** on the canvas itself — right-click an element → **Customise appearance**.

Per-element overrides travel with the diagram; opening it on another machine renders identically.

## Accessibility commitments

Iris is designed to meet **WCAG 2.2 Level AA**. Specifically:

- **Keyboard navigation.** Every canvas operation has a keyboard equivalent — see [Keyboard Shortcuts](keyboard-shortcuts).
- **Focus indicators.** Visible 3:1-ratio outline on the currently-focused element. The sidebar, toolbar, dialogs, and canvas all respect browser focus styling.
- **ARIA labels.** Nav items, buttons, and interactive canvas elements carry labels that screen readers announce.
- **Skip links.** The "Skip to main content" link at the top of every page lands keyboard users past the sidebar.
- **Colour contrast.** Body text ≥ 4.5:1 against background in every theme. Interactive elements ≥ 3:1.
- **Reduced motion.** Animations respect `prefers-reduced-motion` — hover-focus, auto-layout, and zoom transitions disable automatically.
- **Alt text.** Every diagram image and thumbnail carries alt text derived from its name and description.

## Screen reader behaviour

Iris targets **VoiceOver** (macOS / iOS), **NVDA** (Windows), and **Orca** (Linux). Tested surfaces include the dashboard counts, the sidebar navigation, the entity list pages, diagram toolbars, and the Ask AI chat.

The canvas is the hardest surface — shapes and arrows don't have a natural linear reading order. The side-tree view gives screen readers a linear alternative: every element and sub-diagram is reachable via the tree.

## Reporting accessibility issues

If you hit something that doesn't work for a screen reader, a keyboard, or a high-contrast user — open an issue on the Iris repo. Iris treats a11y bugs as regressions, not enhancements.

## Next steps

- [Canvas Editing](canvas-editing) — edit operations and their keyboard equivalents.
- [Keyboard Shortcuts](keyboard-shortcuts) — the full shortcut reference.
