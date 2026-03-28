# ADR-110: Scenia Render Service

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-110 |
| **Initiative** | Scenia Cloud Deployment |
| **Proposed By** | Engineering |
| **Date** | 2026-03-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** deploying the Scenia roadmapping app alongside Iris on Render,

**facing** the need to serve the Scenia React SPA as a standalone web application that Iris opens in a new browser tab, with the Scenia fork living in a separate GitHub repository (`cgbarlow/waylonkenning_scenia`),

**we decided for** adding a third Render Blueprint service using `repo` and `branch` fields to pull from the external fork, building it as a static site that receives the Iris API URL and auth token at runtime via query parameters,

**and neglected** bundling Scenia into the Iris frontend build (would tightly couple the two apps and require complex Vite multi-entry configuration), deploying Scenia on a separate platform (would fragment infrastructure management), and proxying Scenia through the Iris backend (unnecessary complexity for static assets),

**to achieve** independent deployment and build cycles for the Scenia and Iris frontends, clean separation of concerns between the two React/Svelte apps, and a single Render Blueprint that provisions all three services,

**accepting that** the Render GitHub integration must have access to the external fork, the operator must configure CORS origins and cross-service URLs manually (`sync: false`), and a branch rename on the fork requires updating `render.yaml`.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Scenia Static Site | Third Render Blueprint service building from external fork | [SPEC-110-A](./specs/SPEC-110-A-Scenia-Render-Service.md) |
| Cross-Service URLs | `VITE_SCENIA_URL` on frontend, `VITE_API_BASE_URL` on Scenia | [SPEC-110-A](./specs/SPEC-110-A-Scenia-Render-Service.md) |
| CORS Configuration | Backend allows Scenia origin via `IRIS_CORS_ORIGINS` | [SPEC-110-A](./specs/SPEC-110-A-Scenia-Render-Service.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-096 | Render Replaces Netlify | Adds third service to existing Blueprint |
| Extends | ADR-106 | Scenia React Embedding | Deploys the standalone window mode to cloud |
| Relates To | ADR-104 | Scenia Schema Mapping | Scenia calls `/api/scenia/data` on iris-api |
| Relates To | ADR-103 | Extensions Framework | Scenia is gated by the extension registry |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-110-A | Scenia Render Service | Technical Specification | [specs/SPEC-110-A-Scenia-Render-Service.md](./specs/SPEC-110-A-Scenia-Render-Service.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-27 |
| Approved | Engineering | 2026-03-27 |
