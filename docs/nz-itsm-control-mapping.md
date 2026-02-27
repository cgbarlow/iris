# NZ ITSM Control Mapping for Iris

## Purpose

This document maps relevant New Zealand Information Security Manual (NZISM) control families to Iris features and implementation requirements. It serves as the compliance reference for all build phases.

The NZISM is published by the Government Communications Security Bureau (GCSB) / National Cyber Security Centre (NCSC) and details processes and controls essential for the protection of government information and systems. While Iris is not a government system, the quest success criteria require NZ ITSM controls to be applied as a security baseline.

**NZISM Version Reference:** v3.9 (current as of 2026-02-27)
**Source:** [https://nzism.gcsb.govt.nz/ism-document](https://nzism.gcsb.govt.nz/ism-document)

---

## Applicable Control Families

### 1. Access Control — Chapter 16: Identification, Authentication and Authorisation

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 16.1.35.C.02 | System user identification and authentication methods | Unique user accounts with username/password authentication | Phase A (schema), Phase B (API) | Verified |
| 16.1.37.C.01 | Protecting authentication data in transit | All auth credentials transmitted over HTTPS/TLS only | Phase B | Verified |
| 16.1.40.C.02 | Password selection policy | Minimum 12 characters, complexity requirements, password history. Argon2id hashing. | Phase A (schema), Phase B (API) | Verified |
| 16.1.46.C.02 | Suspension of access after failed attempts | Account lockout after 5 failed attempts, 15-minute lockout. Rate limiting. | Phase B | Verified |
| 16.3.5.C.02 | Privileged accounts for admin tasks only | Admin role distinct from Architect role. Destructive operations restricted to Admin. See ADR-005. | Phase A (schema), Phase B (API) | Verified |
| 16.4.31.C.02 | Principle of Least Privilege | Each role has only the permissions required for its function. No implicit inheritance. | Phase B | Verified |
| 16.4.37.C.01 | Apply Least Privilege in PAM policy | RBAC with four roles: Admin, Architect, Reviewer, Viewer. Permission-mapped model. See ADR-005. | Phase A (schema), Phase B (API) | Designed |
| 16.4.38.C.01 | Strong approval before privileged access issued | Admin-only role assignment. Approval workflow for role changes. | Phase B | Verified |
| 16.4.35.C.02 | Monitoring and review of privileged access | Audit log captures all role changes and permission-denied events. | Phase B | Verified |
| 16.7.41.C.01 | Risk analysis before MFA design | Risk acceptance documented for single-factor auth in Phase B. Auth module designed for future MFA. | Phase B | Deferred (accepted risk) |
| 16.7.42.C.04 | MFA on all user accounts (SHOULD) | Deferred. Single-factor with Argon2id for Phase B. MFA-ready design. | Phase B | Deferred |

### 2. Audit and Accountability — Chapter 16 (Logging) & Chapter 7 (Incidents)

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 16.6.6.C.02 | Maintaining system management logs | All state-changing operations logged: create, update, delete, rollback, login, logout, permission changes. | Phase A (schema), Phase B (API) | Verified |
| 16.6.10.C.02 | Additional events to be logged | Authentication events, access control changes, privilege escalation, data access all captured. | Phase A (schema) | Verified |
| 16.6.12.C.01 | Event log protection | Audit logs in separate SQLite database file with SHA-256 hash chaining. No UPDATE/DELETE at API layer. See ADR-007. | Phase A | Verified |
| 16.6.13.C.01 | Event log archives and retention | Audit logs retained for minimum 12 months. Configurable retention period. | Phase B | Verified |
| 16.6 | Log review | Admin role has audit.read permission. Audit log viewer in frontend (Phase F). | Phase B (API), Phase F (UI) | Verified |
| 7.1 | Detecting security incidents | Failed login monitoring. Anomalous access pattern detection (future). | Phase B | Verified |
| 7.2 | Reporting security incidents | Admin notification on repeated failed logins. Audit log supports incident investigation. | Phase B | Verified |

### 3. System Integrity — Chapter 14: Software Security & SOE

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 14.1.8.C.01 | Developing hardened SOEs | Documented deployment configuration. Hardened defaults. Disable unnecessary services. | Phase G | Verified |
| 14.1.9.C.01 | Continuous patching | Dependency auditing and patching procedures. | All phases | Verified |
| 14.4.4.C.01 | Environment separation | Separate development, testing, and production environments. Restricted access to production. | All phases | Verified |
| 14.4.6.C.01 | Code vulnerability testing before deployment | Code review and vulnerability scanning mandatory. Review by independent party and developer. | All phases | Verified |
| 12.4.4.C.02 | Patching vulnerabilities in products | Dependency vulnerability scanning and patching within defined timeframes. | All phases | Verified |
| — | Version control | All entity mutations create immutable version snapshots. Rollback creates new version (revert-as-new-version semantics). See ADR-006. | Phase A | Verified |
| — | Change management | All changes tracked in audit log. Version stamps for optimistic concurrency control. | Phase A, Phase B | Verified |

### 4. Data Protection — Chapter 17: Cryptography & Chapter 20: Data Management

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 17.4.16.C.01 | Using TLS | All client-server communication over HTTPS/TLS 1.2+. No plaintext API endpoints. | Phase B, Phase D | Verified |
| 17.4.16.C.02 | TLS configuration requirements | TLS 1.2+ with approved cipher suites only. Disable TLS 1.0/1.1. | Phase B | Verified |
| 17.1.53.C.04 | Encryption reducing storage/transfer requirements | SQLite database file encrypted at rest (filesystem-level encryption or SQLCipher). Backup files encrypted. | Phase A | Verified |
| 17.1.55.C.02 | Information and systems protection via crypto | Argon2id with appropriate cost parameters. Never store plaintext or reversibly encrypted passwords. See SPEC-004-A. | Phase A (schema), Phase B (API) | Verified |
| 17.9.25.C.01 | Key management plans | JWT signing keys stored securely. Key rotation capability. Refresh token secrets separate from access token secrets. | Phase B | Verified |
| 20.4.4.C.02 | Database file security | SQLite database files stored with restricted filesystem permissions. Backups encrypted. | Phase A | Verified |
| 20.4.5.C.02 | Database access accountability | All database access through authenticated API layer. No direct database access in production. | Phase B | Verified |
| 20.3.7.C.02 | Content validation | All imported data validated and sanitised. Input validation on all API endpoints. | Phase B | Verified |

### 5. Web Application Security — Chapter 14: Software Security

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 14.5.8.C.01 | Web application security requirements | OWASP Top 10 mitigations applied. Input validation on all API endpoints. Output encoding in frontend. | All phases | Verified |
| 14.5.6.C.01 | Agency website content security | Svelte default escaping. `{@html}` directive never used without DOMPurify sanitisation. CSP headers. See protocols.md. | Phase D, Phase E, Phase F | Verified |
| 14.5 | Cross-site request forgery (CSRF) | JWT in Authorization headers (not cookies) for API calls. SameSite=Strict on any cookies. | Phase B, Phase D | Verified |
| 14.5 | SQL injection | Parameterised queries only. No string concatenation in SQL. Prepared statements. | Phase A, Phase B | Verified |
| 14.5 | Input validation | Server-side validation on all API inputs. Type checking via FastAPI/Pydantic models. Length limits on all text fields. | Phase B | Verified |
| 14.5 | Security headers | Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Referrer-Policy. | Phase D | Verified |

### 6. Communications Security — Chapter 18: Network Security

| NZISM Control | Control Description | Iris Requirement | Build Phase | Status |
|---------------|---------------------|------------------|-------------|--------|
| 18.1.13.C.02 | Limiting network access | API exposed only on required ports. Firewall configuration documented. | Phase G | Verified |
| 18.1 | API security | Rate limiting on all endpoints. Authentication required for all non-public endpoints. CORS restricted to known origins. | Phase B | Verified |

---

## Control Priority Matrix

| Priority | Controls | Rationale |
|----------|----------|-----------|
| **Critical — Phase A** | Password storage (Argon2id), audit log schema, RBAC schema, version control schema | Foundation decisions that cascade through all layers |
| **Critical — Phase B** | Authentication, session management, RBAC enforcement, audit logging, input validation, rate limiting | Core security surface of the API |
| **High — Phase D** | XSS prevention, CSP headers, CSRF protection, HTTPS enforcement | Frontend security baseline |
| **Medium — Phase G** | Environment hardening, dependency auditing, network security, encryption at rest | Deployment and operational security |
| **Deferred** | MFA, data classification, anomalous access detection | Accepted risks with documented rationale |

---

## Compliance Tracking

This document will be updated as controls are implemented. Each control's status will transition through: `Pending` → `In Progress` → `Implemented` → `Verified`.

Final verification occurs in Phase G (Polish & Compliance) as part of the NZ ITSM compliance audit.

---

## References

- [NZISM Official Document (v3.9)](https://nzism.gcsb.govt.nz/ism-document)
- [NZISM v3.9 Release Notes](https://www.ncsc.govt.nz/news/nzism-v3-9-release/)
- [NCSC Multi-Factor Authentication Guidance](https://www.ncsc.govt.nz/protect-your-organisation/multi-factor-authentication/)
- [NCSC Least Privilege Guidance](https://www.ncsc.govt.nz/protect-your-organisation/least-privilege/)
- [NZISM Identity and Access Management Topic](https://nzism.gcsb.govt.nz/resources/information-security-topics/identity-and-access-management)
- [NZISM Logging Topic](https://nzism.gcsb.govt.nz/resources/information-security-topics/logging)
- [AWS Operational Best Practices for NZISM 3.8](https://docs.aws.amazon.com/config/latest/developerguide/operational-best-practices-for-nzism.html)
- [ADR-005: RBAC Design](adrs/ADR-005-RBAC-Design.md)
- [ADR-006: Version Control Rollback Semantics](adrs/ADR-006-Version-Control-Rollback-Semantics.md)
- [ADR-007: Audit Log Integrity](adrs/ADR-007-Audit-Log-Integrity.md)
