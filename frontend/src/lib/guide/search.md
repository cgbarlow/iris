# Search

Iris indexes every entity name and description for full-text search. The dashboard search bar and list-page search boxes both call the same index.

![Search](/guide/search.png)

## Global vs scoped

- The dashboard search bar is **always global**. Typing on `/` with no URL params returns results from every set and every collection.
- When you click into a specific set or collection, the URL gains a `?set_id=…` or `?collection_id=…` query and the search bar on that page scopes to it.

## Result types

Results include collections, sets, packages, diagrams, and elements. Each result shows its type with a coloured tag. Click to open the entity; the deep link preserves the entity's set scope.

## Add to AI context

Click **Add to AI context** on any result to stage that entity for your next Ask AI question. See the **Ask AI** section for how context is used.
