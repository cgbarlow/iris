# Knowledge Graph

The knowledge graph visualises every entity and relationship in your current scope as an interactive force-directed layout.

![Knowledge graph](/guide/knowledge-graph.png)

## Hierarchy flow

Nodes are laid out in concentric bands around their governing collection centre:

- **Collection** at the centre
- **Sets** in a close ring
- **Packages** further out
- **Diagrams** further still
- **Elements** at the outer edge

This layer ordering is enforced by a radial force so it stays consistent even at UAT scale (hundreds of diagrams). See ADR-120 / SPEC-120-A for details.

## Spread slider

The `Spread` slider controls the overall scale. At low spread (0.2) galaxies are compact; at high spread (3.0) they fan wide and individual clusters become easier to read.

## Label density

The `Labels` slider controls how many labels are drawn at each zoom level. Higher values draw more labels at the cost of overlap.

## Hover focus

Hover any node for 400 ms — Iris dims all unrelated nodes and highlights the hovered node's immediate neighbours. Move off the node to restore full visibility.

## Direct diagram links

By default, every set draws a link to every diagram and element within it. This creates visible "petals" of children around each set. Turn this toggle off in the settings panel to de-clutter the view without changing the physics — the underlying forces still run.
