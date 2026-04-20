# ADR-115: Session-Scoped File Upload for AI Context

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-115 |
| **Initiative** | File Upload AI Context |
| **Proposed By** | Engineering |
| **Date** | 2026-03-30 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** enabling users to bring external documents (PDFs, spreadsheets, Word docs, text files) into Ask AI conversations as additional context,

**facing** the need for users to ask questions about documents they have on hand without importing them permanently into Iris, and the limitation that the current AI context is restricted to Iris sets, collections, and DocRef legislation,

**we decided for** a session-scoped file upload facility on the Ask AI Context tab with a stateless backend extraction endpoint (`POST /api/ai/files/extract`) that accepts a file, extracts text server-side, and returns the extracted text to the frontend, where it is held in Svelte component state and included in chat requests as a `file_contexts` field on `MultiSetQARequest`,

**and neglected** server-side session storage for uploaded files (would require session management, cleanup, and GC complexity), multimodal/vision sending of images to LLMs (requires provider capability detection and message format changes), and permanent file storage in the database (conflicts with the ephemeral session intent),

**to achieve** a zero-persistence file upload workflow where users can upload any file, have its text extracted automatically, and use that content alongside sets and legislation as AI context — all within a single page session that resets on refresh,

**accepting that** binary files (images, executables) without extractable text will show an error message, very large documents may be truncated at 100k characters, and the extracted text travels over the wire twice (extract response then chat request), which is acceptable given the 5 MB file limit.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| File Extraction Endpoint | Stateless `POST /api/ai/files/extract` that extracts text from PDF, DOCX, XLSX, PPTX, CSV, and text files | [SPEC-115-A](./specs/SPEC-115-A-File-Upload-AI-Context.md) |
| FileUploader Component | Drag-and-drop file upload UI on the Context tab with status indicators | [SPEC-115-A](./specs/SPEC-115-A-File-Upload-AI-Context.md) |
| Chat Integration | `file_contexts` field on `MultiSetQARequest` appended to system prompt context | [SPEC-115-A](./specs/SPEC-115-A-File-Upload-AI-Context.md) |
| Files-Only Context | Users can chat with only uploaded files, no sets or legislation required | [SPEC-115-A](./specs/SPEC-115-A-File-Upload-AI-Context.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-093 | AI Model Management | Adds files as AI context source |
| Extends | ADR-113 | Ask AI Tabbed Layout | FileUploader sits on the Context tab |
| Pattern From | ADR-112 | DocRef Legislation | Follows same context integration pattern |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-115-A | File Upload AI Context | Technical Specification | [specs/SPEC-115-A-File-Upload-AI-Context.md](./specs/SPEC-115-A-File-Upload-AI-Context.md) |

---

## Status History

| Date | Status | Notes |
|------|--------|-------|
| 2026-03-30 | Approved | Initial decision |
