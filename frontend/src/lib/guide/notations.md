# Notations

Iris supports seven diagram notations, each with its own element types, relationship types, and visual conventions. You pick a notation when you create a diagram; the toolbar and relationship types then adapt to that notation.

## Simple

Generic rectangles and lines. No strict semantics — useful for quick whiteboarding or ad-hoc diagrams. Relationships are untyped ("connected to").

## Component (UML stereotype)

Boxes with lollipop and socket connectors — the classical component-diagram shape. Use for structural decomposition of software systems.

Relationship types: `provides`, `requires`, `uses`, `depends-on`.

## UML

Full UML 2.x element set:

- **Structural** — Class, Interface, Component, Package, Node, Artifact.
- **Behavioural** — Activity, UseCase, State, Event.
- **Relationship types** — `association`, `aggregation`, `composition`, `inheritance`, `realisation`, `dependency`.

Class elements support attributes and operations (editable from the element detail page).

## ArchiMate

Full ArchiMate 3.2 element set across all four layers:

- **Business** — Actor, Role, Process, Service, Interface, Event, Contract, Value.
- **Application** — Component, Interaction, Interface, Service, Data Object, Function.
- **Technology** — Node, Device, System Software, Network, Communication Path.
- **Motivation** — Goal, Outcome, Requirement, Constraint, Principle, Stakeholder, Driver, Assessment.

Relationship types match the ArchiMate spec: `composition`, `aggregation`, `assignment`, `realisation`, `used-by`, `access`, `influence`, `triggering`, `flow`, `specialisation`, `association`.

Iris renders each layer with its standard colour scheme (business yellow, application blue, technology green, motivation purple) — override per-element via the [Theme](themes-accessibility) system.

## C4

The C4 model's four zoom levels:

1. **System Context** — one system, its users, and external systems.
2. **Container** — applications, data stores, microservices.
3. **Component** — major building blocks inside a container.
4. **Code** — class or module detail.

Each level has a distinct palette. Click-through navigation lets you drill from a Context diagram into a Container diagram and deeper.

## Sequence

UML Sequence diagrams: lifelines (vertical bars), messages (horizontal arrows), combined fragments (loops, alternatives, parallels). Time flows top-to-bottom.

Sequence diagrams are typically generated from other diagrams (an AI-created DoView outcome chain can emit a sequence of backing interactions).

## DoView

**DoView strategy models** (also known as outcome maps, theory of change) — boxes connected by *causal* arrows showing how activities lead to outputs which lead to intermediate outcomes which lead to final impacts.

Iris has first-class DoView support:

- AI-assisted diagram creation from a plain-text outcome description (**Ask AI** — see that section).
- Specialised element types: `activity`, `output`, `outcome`, `impact`, `indicator`.
- Only the `causal_link` relationship type — DoView maps are strictly outcome-chains.

DoView is the notation used throughout the UAT sample data (the "DoView Strategy Models" collection).

## Roadmap

Via the **Scenia extension** — see [Roadmap (Scenia)](roadmap-scenia). Roadmap diagrams have their own palette (strategies, programmes, initiatives, assets, applications, milestones, resources, dependencies) and a timeline view unique to Scenia.

## Mixing notations

You can't mix notations within a single diagram — the toolbar and valid relationship types are notation-specific. You can link across notations: a DoView outcome can reference a Sparx-imported UML class via an element-to-element reference (though the visual edge won't appear on the canvas).

## Next steps

- [Canvas Editing](canvas-editing) — how to build diagrams in any of these notations.
- [Ask AI](ask-ai) — the AI assistant can generate DoView diagrams from text.
