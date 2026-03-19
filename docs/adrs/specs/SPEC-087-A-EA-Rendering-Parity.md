# SPEC-087-A: EA Rendering Parity Implementation

**ADR:** [ADR-087](../ADR-087-EA-Rendering-Parity-Fixes.md)
**Version:** 1.0

## Overview

Detailed implementation spec for achieving visual parity between Iris rendering and EA ground truth for UML class diagrams.

## ThemeRenderingConfig Extensions

New fields added to `ThemeRenderingConfig`:
- `hideTypeStereotypes: boolean` - suppress type-derived stereotypes (abstract, interface, enumeration)
- `abstractBoldOverride: boolean` - when false, abstract names render italic-only (not bold)

## Theme Selector Fix

Priority order changed: user-selected active theme > diagram preferred theme > notation default.

## Node Rendering

- Stereotype text only shown from `data.stereotype` (EA-imported) when `hideTypeStereotypes` is true
- Header uses flex column layout for centered labels
- Abstract class label gets `font-weight: 400` when `abstractBoldOverride` is false

## Note Rendering

- Remove 1.4x scale factor on note dimensions during import
- Note background uses CSS variables for theme support

## Connector Improvements

- All SVG markers get `overflow="visible"`
- EA `t_diagramlinks` geometry parsed for waypoints and connection point offsets
- EA `t_connector` Start_Edge/End_Edge mapped to handle sides
- Edge rendering supports polyline paths through waypoints

## Diagram Frame

- Import stores diagramFrame data (type, name, width, height) in canvas model_data
- DiagramFrame.svelte renders border + title tab as background layer

## Attribute Sort

- ViewConfig canvas gets `sort_attributes?: 'pos' | 'alpha'`
- UmlRenderer sorts attributes when alpha mode selected

## Edit Mode

- On save, persist active theme ID to diagram metadata if not already set
