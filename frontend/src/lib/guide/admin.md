# Admin

Admin-only screens manage users, audit logs, locks, and system settings.

![Admin](/guide/admin.png)

## Who sees admin

The Admin section of the sidebar is only visible to users with the **admin** role. Role-based permissions also gate individual admin routes on the server side, so non-admin users who construct a direct URL are rejected with HTTP 403.

## Users

Create, update, and deactivate users. Assign roles from the seeded set (admin, architect, reviewer, viewer).

## Audit

Every write operation on Iris is recorded in the audit log with the responsible user, timestamp, operation, and a hash of the request body. The log is append-only.

## Locks

Admins can inspect and force-release editing locks on diagrams when a user has disconnected without closing the lock.

## Settings

System-wide admin defaults for the knowledge graph (SPEC-117-A), AI providers, extensions, and themes live under the Admin Settings page.
