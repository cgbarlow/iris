# ADR-005: Role-Based Access Control Design

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-005 |
| **Initiative** | Iris Security — Access Control |
| **Proposed By** | The CISO (Cat) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** designing the access control model for Iris, an enterprise architectural modelling tool where architects create and edit models while stakeholders browse and navigate, with requirements for auditability, NZ ITSM compliance, and future extensibility,

**facing** the choice between a simple two-role model (editor/viewer) that maps directly to Browse Mode and Edit Mode, a four-role model with granular permission mappings, or a full attribute-based access control (ABAC) system with fine-grained policies,

**we decided for** a four-role permission-mapped RBAC model with the roles Admin, Architect, Reviewer, and Viewer, where permissions are defined as role-to-permission mappings rather than hardcoded role checks, enabling new roles to be added without code changes,

**and neglected** a two-role model (which would be insufficient for enterprise governance — no distinction between who can delete vs edit, no admin role, no review capability), a full ABAC system (which adds significant implementation complexity disproportionate to current requirements), and per-entity ACLs (which add schema complexity and query overhead that can be deferred),

**to achieve** enterprise-appropriate access control that supports distinct user workflows (administration, modelling, review, browsing), complies with NZ ITSM access control requirements, enables future role additions without code changes, and maintains a clean separation between authentication and authorisation,

**accepting that** four roles may need to expand as organisational needs evolve (the mapping-based design supports this), that model-level visibility (public/restricted) is deferred to a future phase but the schema must not preclude it, and that RBAC adds complexity to the Phase A schema and Phase B API.

---

## Role Definitions

| Role | Name | Mode Access | Core Permissions | Use Case |
|------|------|-------------|------------------|----------|
| `admin` | Admin | Full | User management, role assignment, system configuration, all model operations, audit log access | System administrators |
| `architect` | Architect | Edit Mode (Simple + Full View) | Create/edit/delete entities and models, manage relationships, version control operations, commenting | Solution, domain, and enterprise architects |
| `reviewer` | Reviewer | Edit Mode (read) + Comment | View all models, add comments, approve/reject model changes, bookmark/star | Architecture review board, senior stakeholders |
| `viewer` | Viewer | Browse Mode | View published models, navigate relationships, search, bookmark/star | Stakeholders, technologists, business users |

## Permission Model

Permissions are defined as discrete capabilities mapped to roles. This is the canonical permission set for Phase A/B.

### Permission Definitions

| Permission | Description | Admin | Architect | Reviewer | Viewer |
|------------|-------------|:-----:|:---------:|:--------:|:------:|
| `user.create` | Create user accounts | Y | | | |
| `user.read` | View user profiles | Y | Y | Y | Y |
| `user.update` | Modify user accounts | Y | | | |
| `user.delete` | Delete user accounts | Y | | | |
| `user.assign_role` | Assign roles to users | Y | | | |
| `model.create` | Create new models | Y | Y | | |
| `model.read` | View models | Y | Y | Y | Y |
| `model.update` | Edit model metadata | Y | Y | | |
| `model.delete` | Delete models | Y | | | |
| `entity.create` | Create new entities | Y | Y | | |
| `entity.read` | View entities | Y | Y | Y | Y |
| `entity.update` | Modify entities | Y | Y | | |
| `entity.delete` | Delete entities | Y | | | |
| `relationship.create` | Create entity relationships | Y | Y | | |
| `relationship.delete` | Remove entity relationships | Y | Y | | |
| `version.create` | Create new versions | Y | Y | | |
| `version.rollback` | Rollback to previous version | Y | | | |
| `version.read` | View version history | Y | Y | Y | Y |
| `comment.create` | Add comments | Y | Y | Y | |
| `comment.read` | View comments | Y | Y | Y | Y |
| `comment.delete` | Delete comments (own) | Y | Y | Y | |
| `comment.delete_any` | Delete any comment | Y | | | |
| `bookmark.manage` | Star/unstar models | Y | Y | Y | Y |
| `search.execute` | Perform searches | Y | Y | Y | Y |
| `audit.read` | View audit logs | Y | | | |
| `system.configure` | Modify system settings | Y | | | |

### Design Principles

1. **Permissions are additive.** A role has only the permissions explicitly granted. No implicit inheritance between roles.
2. **Role checks are never hardcoded.** All access control checks query the permission mapping, not role names. Code checks `has_permission("entity.update")`, never `role == "architect"`.
3. **Roles are assigned per user.** A user has exactly one role. Multi-role is not supported in Phase A but the schema does not preclude it.
4. **Permission changes require Admin.** Only Admin can assign or change user roles.
5. **Delete is restricted.** Only Admin can delete entities and models. Architects can create and edit but not delete — this prevents accidental data loss in a shared repository.
6. **Rollback is Admin-only.** Given the cascading implications of rolling back shared entities (per CISO risk assessment), rollback is restricted to Admin.

### Schema Implications (Phase A)

The permission model requires three tables in the data foundation:

```
users (id, username, password_hash, role, created_at, updated_at, is_active)
roles (id, name, description)
role_permissions (role_id, permission)
```

- `role_permissions` is the mapping table. Adding a new role means inserting a row in `roles` and the corresponding permission rows in `role_permissions`.
- The `permission` column stores the permission string (e.g., `entity.update`). This is validated at the application layer.
- Default roles and permissions are seeded on database initialisation.

### Future Extensibility

The following extensions are **deferred but not precluded** by this design:

| Extension | What It Adds | When Needed |
|-----------|-------------|-------------|
| Model-level visibility | `model_access` table with `(model_id, role/user, access_level)` | When sensitive models need restricted access |
| Multi-role per user | Junction table `user_roles` replacing `users.role` column | When users need multiple role capabilities |
| Custom roles | Admin UI for creating roles with selected permissions | When organisations need bespoke role definitions |
| Permission delegation | Architect-level users granting temporary access | When workflow-based access is needed |

---

## Options Considered

### Option 1: Four-Role Permission-Mapped RBAC (Selected)

**Pros:**
- Maps cleanly to Iris's user personas (admin, architect, reviewer, stakeholder)
- Permission mappings enable role additions without code changes
- Granular enough for enterprise governance (delete restrictions, rollback control)
- Compliant with NZ ITSM access control requirements (principle of least privilege, separation of duties)
- Clean schema with three tables

**Cons:**
- Four roles may not cover all organisational structures
- Permission checking adds a database query per request (mitigated by caching)
- More complex than a simple two-role model

### Option 2: Two-Role Model — Editor/Viewer (Rejected)

**Pros:**
- Simple to implement
- Maps directly to Browse Mode / Edit Mode

**Cons:**
- No admin role — who manages users?
- No distinction between destructive operations (delete, rollback) and creative operations (create, edit)
- No review capability — reviewers and editors are conflated
- Insufficient for NZ ITSM compliance (no separation of duties)
- Would need to be replaced within weeks of real enterprise use

**Why rejected:** Insufficient granularity for enterprise use. Does not support separation of duties. Would create technical debt that requires a breaking schema change to fix.

### Option 3: Full ABAC / Policy-Based Access Control (Rejected)

**Pros:**
- Maximum flexibility — policies can express any access rule
- Supports entity-level, attribute-level, and context-aware access control
- Industry standard for complex enterprises

**Cons:**
- Significant implementation complexity (policy engine, evaluation, caching)
- Overkill for current requirements — the four-role model covers all defined use cases
- Slower time to market
- Harder to audit and debug than explicit role-permission mappings

**Why rejected:** Disproportionate complexity for the current scope. The four-role model with permission mappings provides a clear upgrade path to ABAC if needed, without the upfront cost.

### Option 4: Per-Entity ACLs (Rejected)

**Pros:**
- Fine-grained control over individual models and entities
- Supports sensitive content restrictions

**Cons:**
- Adds ACL checking to every entity query — performance impact
- Complex schema (ACL table, inheritance rules, default policies)
- Management overhead — who maintains per-entity permissions?
- Premature for current requirements

**Why rejected:** Deferred, not dismissed. The schema design leaves room for a future `model_access` table without breaking changes. Current requirements do not specify per-entity access control.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Implement four-role RBAC in Phase A schema | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The CISO (Cat) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-003 | Architectural Vision | RBAC is part of The Engine layer (Phase B) but schema is in The Foundation (Phase A) |
| Depends On | ADR-004 | Backend Language and Framework | FastAPI security utilities implement the permission checks |
| Relates To | TBD | NZ ITSM Control Mapping | RBAC design addresses access control requirements |
| Enables | TBD | Authentication Implementation | Auth module uses the role and permission model |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-005-A | RBAC Permission Matrix | Technical Specification | specs/SPEC-005-A-RBAC-Permissions.md (TBD) |
| SPEC-005-B | Authentication and Session Management | Technical Specification | specs/SPEC-005-B-Auth-Sessions.md (TBD) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
