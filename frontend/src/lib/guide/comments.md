# Comments

> **Sign in to use this.** Anyone can read comments on any diagram; only signed-in users can post, edit, or delete.

Iris has per-diagram and per-element comment threads. Use them for review feedback ("this outcome needs a measurable indicator"), design notes ("decided to split this component — see Jira-123"), or simple acknowledgement.

## Where to find comments

- **Diagrams.** Open any diagram; the toolbar has a **Comments** button with a badge showing the thread count. Click to open the side panel.
- **Elements.** Open an element detail page; the right-hand panel shows comments on that specific element.
- **Packages.** Package detail pages have a comments section at the bottom.

Comments live beside the content — you never leave the page to read or respond.

## Posting a comment

1. Open the comments panel (toolbar button or right-hand panel).
2. Type into the text field at the bottom.
3. Press **Post Comment** or `Ctrl + Enter`.

Your comment appears immediately with your username and a relative timestamp ("2m ago", "3h ago", "Yesterday"). All other users with the diagram open see it within a few seconds (a polling refresh).

## Editing and deleting

Hover your own comment to reveal **Edit** and **Delete** buttons. You can only edit or delete comments you posted yourself — even admins can't edit other users' comments (audit-log integrity). Deleted comments are removed entirely, not soft-deleted.

## Formatting

Plain text only. No Markdown, no HTML — the input is sanitised through DOMPurify on render so any accidentally-pasted HTML is escaped. Keep comments concise; use the element or diagram description fields for longer-form notes.

## Mentions and threading

Not currently supported. The comments list is flat, in chronological order. If mentions become important, raise an issue — this is a deliberately small feature at v4.2.

## Comments vs. the audit log

- **Comments** are conversations between users — visible to every viewer, editable by their author.
- **Audit log** is an append-only record of *every write action* against the system (created, updated, deleted, renamed), including changes made via the API. Only admins see the audit log (**Admin → Audit**).

If you're looking for "who changed this last?" the audit log is the authoritative answer, not the comments thread.

## Next steps

- [Canvas Editing](canvas-editing) — the Comments button sits alongside edit-mode and save actions.
- [Bookmarks](bookmarks) — bookmark a diagram to track a conversation over time.
