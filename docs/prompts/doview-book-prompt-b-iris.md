Prompt B (Iris): Outcomes Theory Diagram Retriever Prompt
for use directly after Prompt A response has been generated

Version: 2.0.0

Use the Iris "DoView Book" set as the source for retrieving the original mermaid diagrams associated with the outcomes theory tools cited in the preceding response.

Iris set: DoView Book (set_id 33032180-d77a-4ce4-88cf-b49cd643e093)

Use this prompt after Prompt A: Outcomes Theory Text Response Prompt has produced a response. Look at the response immediately above and locate the heading:

Image-retrieval seed list for Prompt B

Under that heading are one or more lines in this exact format:

iris-diagram: <uuid> (pair: <paircode>)

Use each `<uuid>` to fetch the diagram directly from Iris. The `<paircode>` is for human reference and for constructing the reader-facing page URL.

If the seed-list heading is absent, state exactly: "No image-retrieval seed list was present in the preceding response." Then stop. Do not attempt to recover by guessing or searching.

If Iris is unreachable or any seed UUID cannot be fetched, state exactly: "The Iris DoView Book set is not currently available, so the original diagrams cannot be retrieved." Then stop.

SOURCE RESTRICTION

Use only the Iris "DoView Book" set. Do not use any other source. Do not use general knowledge. Do not invent, redraw, simplify, improve, or approximate a diagram. Do not use the rest of the internet.

TASK

For each `iris-diagram: <uuid>` in the seed list:

1. Call mcp__iris__get_diagram with that UUID.

2. Confirm the diagram is a tool-kind diagram by checking its `description` field for "kind: tool". If it is not, skip it and note "Skipped non-tool diagram <uuid>" in the response.

3. In `data.content`, locate the fenced mermaid code block. It begins with ```` ```mermaid ```` and ends with ```` ``` ````. If no mermaid block is present, note "No mermaid diagram found in <uuid>" and skip that entry.

4. Extract the mermaid block verbatim.

OUTPUT FORMAT

Begin the response with this heading:

Diagrams from the DoView Planning and Outcomes Theory Handbook, Duignan, P. (2025), https://doviewplanning.org/book

Begin with this note:

This diagram-retrieval response reproduces the original mermaid diagrams from the Iris DoView Book set. Rendering depends on the AI system's ability to render mermaid. Where the diagram does not render visually, the mermaid source remains visible and can be copied into any mermaid-capable system.

Then, for each successfully retrieved diagram, in the order they appear in the seed list, output:

### Tool <PAIRCODE_UPPERCASE>: <diagram-name-from-iris>

Page URL: https://doviewplanning.org/<paircode>doviewtool

```mermaid
<verbatim mermaid block from data.content>
```

Formal relevance note: <one short formal sentence explaining the diagram's relevance to the preceding outcomes theory answer>

Rules for each entry:

- The page URL must be written as raw visible plain text beginning with https:// — not hidden behind linked words, not in markdown link syntax.
- The mermaid block must be copied verbatim from `data.content`. Do not relabel nodes. Do not change arrow direction. Do not reformat. Do not add nodes. Do not remove nodes. Do not translate.
- The formal relevance note must use formal language. Do not address the user. Do not say "I would" or "you could".
- Do not include the question-kind diagram for any pair, only the tool-kind diagram.

If a seed-list entry could not be retrieved (Iris error, missing mermaid, wrong kind), include a short note in place of the entry:

Tool <PAIRCODE_UPPERCASE>: original diagram could not be retrieved from Iris.

Page URL: https://doviewplanning.org/<paircode>doviewtool

After all entries, end the response with the full handbook reference in raw visible plain text:

Duignan, P. (2025). DoView Planning and Outcomes Theory Handbook: 100+ Innovative, Integrated Tools for Solving Key Issues in Planning, Implementation, Contracting, Measurement, Evaluation and Reporting (for Humans and AI Agents). DoViewPlanning.Org. https://doviewplanning.org/book

HUMAN-FACING URL RULE — COPY-SAFE URLS FOR HUMANS

Every page URL and the handbook reference must be written as raw, visible, copy-safe plain text beginning with https://

Do not hide page URLs behind words.
Do not use reference-style links such as "[1]".
Do not use footnotes.
Do not use source icons.
Do not use citation markers.
Do not use embedded hyperlinks for page URLs.
Do not write "see above".
Do not write "see links above".
Do not use shortened URLs.

The mermaid code block itself is not a URL and is not subject to this rule. It is reproduced as a fenced code block.

DIAGRAM FAITHFULNESS RULES

The mermaid block must be copied verbatim from the Iris diagram's `data.content`. The only acceptable transformations are:
- preserving whitespace
- preserving the original opening ```` ```mermaid ```` fence and closing ```` ``` ```` fence

Do not redraw the diagram from memory.
Do not simplify it.
Do not improve it.
Do not rename or translate labels.
Do not change arrow directions or edge styles.
Do not add explanatory nodes.
Do not create a new substitute diagram.
Do not use a diagram from outside the Iris DoView Book set.

If the source diagram has no mermaid block, do not synthesise one. Note the absence and continue.

FINAL COMPLIANCE CHECK BEFORE ANSWERING

Before giving the response, check and correct it so that:

1. It begins with the required heading and the diagram-retrieval note.
2. Every retrieved diagram is from the Iris DoView Book set (set_id 33032180-d77a-4ce4-88cf-b49cd643e093).
3. Every mermaid block has been copied verbatim from the diagram's `data.content`, with no redrawing, simplification, or relabelling.
4. Every entry pairs the mermaid block with a raw visible plain-text page URL of the form https://doviewplanning.org/<paircode>doviewtool.
5. Only tool-kind diagrams (description contains "kind: tool") have been reproduced; question-kind diagrams have not been reproduced.
6. Every URL is raw visible plain text. Scan the response for "](https://" and "[http"; if either appears, rewrite the URL as raw plain text.
7. The response ends with the full handbook reference and https://doviewplanning.org/book in raw visible plain text.
8. No content from outside the Iris DoView Book set appears in the response.
