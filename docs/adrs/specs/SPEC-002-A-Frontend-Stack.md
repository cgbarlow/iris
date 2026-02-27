# SPEC-002-A: Frontend Stack Configuration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-002-A |
| **ADR** | [ADR-002](../ADR-002-Frontend-Tech-Stack.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the frontend technology stack configuration for Iris, as decided in ADR-002.

## Stack Components

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | SvelteKit | Latest stable | Application framework with routing, SSR capabilities |
| UI Framework | Svelte 5 | Latest stable | Component framework with runes-based reactivity |
| Canvas | Svelte Flow (xyflow) | Latest stable | Interactive node-based canvas for diagram rendering |
| UI Components | shadcn-svelte | Latest stable | Accessible, minimalistic component library |
| UI Primitives | Bits UI | Latest stable | Headless accessible component primitives |
| Styling | Tailwind CSS | v4+ | Utility-first CSS with CSS custom properties for theming |
| Language | TypeScript | 5.x+ | Type safety across the entire frontend |
| Build Tool | Vite | Via SvelteKit | Development server and production bundling |

## Theming

- Light mode, dark mode, and system mode via `mode-watcher` (shadcn-svelte integration)
- CSS custom properties for theme tokens
- High-contrast mode per WCAG requirements
- Tailwind CSS `darkMode: 'class'` strategy

## State Management

- Svelte 5 runes (`$state`, `$derived`, `$effect`) for component and application state
- No external state management library required for most use cases
- Canvas state managed through Svelte Flow's built-in store

## Accessibility Approach

- shadcn-svelte + Bits UI provide baseline accessible components
- Svelte compiler accessibility warnings enabled
- Additional ARIA patterns to be built for canvas interactions
- Keyboard navigation for diagram elements
- Screen reader announcements for canvas state changes
- Custom focus management for modal dialogs and panels

## Project Structure

```
src/
├── lib/
│   ├── components/    # Shared UI components
│   ├── canvas/        # Diagram canvas components
│   │   ├── nodes/     # Custom Svelte Flow node types
│   │   ├── edges/     # Custom edge types
│   │   └── controls/  # Canvas control components
│   ├── stores/        # Svelte stores and state
│   ├── types/         # TypeScript type definitions
│   └── utils/         # Utility functions
├── routes/            # SvelteKit routes
├── app.css            # Global styles and Tailwind
└── app.html           # HTML template
```

## Configuration Files

- `svelte.config.js` — SvelteKit configuration
- `vite.config.ts` — Vite configuration
- `tailwind.config.ts` — Tailwind CSS configuration
- `tsconfig.json` — TypeScript configuration
- `components.json` — shadcn-svelte configuration
