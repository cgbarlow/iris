"""Idempotent seed: Scenia demo data for the roadmapping extension.

Creates a "Scenia Extract" set with:
- 7 Categories, 6 Strategies, 6 Programmes
- 40 Assets (16 banking + 24 GEANZ), 8 Applications, ~30 App Segments
- ~40 Initiatives, 9 Dependencies, 14 Milestones, 6 Resources
- 6 Application Statuses, Timeline Settings
- 10 interlinked diagrams

Idempotency: checks for existing seed marker before creating.
Called from extensions/router.py when Scenia is installed.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

# Deterministic UUIDs for seed data
_NAMESPACE = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")


def _gen_id(prefix: str, index: int) -> str:
    """Generate a deterministic UUID v5 for Scenia seed data."""
    return str(uuid.uuid5(_NAMESPACE, f"scenia-{prefix}-{index}"))


_SET_ID = _gen_id("set", 0)
_SEED_MARKER = "scenia_seed_v2"


# ── ID Mapping ──────────────────────────────────────────────────────────────

_ID_MAP: dict[str, str] = {}
_ID_COUNTERS: dict[str, int] = {}


def _map_id(scenia_id: str, prefix: str) -> str:
    """Map a Scenia short ID to a deterministic UUID, tracking the counter per prefix."""
    idx = _ID_COUNTERS.get(prefix, 0)
    _ID_COUNTERS[prefix] = idx + 1
    uid = _gen_id(prefix, idx)
    _ID_MAP[scenia_id] = uid
    return uid


def _ref(scenia_id: str) -> str:
    """Look up a previously mapped Scenia ID."""
    return _ID_MAP[scenia_id]


# ── Date helpers ────────────────────────────────────────────────────────────

def _rel_date(month_offset: int, day: int = 1) -> str:
    """Return an ISO date string relative to Jan 1 of the current year.

    month_offset=0, day=1  => Jan 1 current year
    month_offset=3, day=15 => Apr 15 current year
    month_offset=14, day=1 => Mar 1 next year
    """
    base_year = datetime.now(tz=UTC).year
    total_months = month_offset
    year = base_year + total_months // 12
    month = 1 + total_months % 12
    return f"{year}-{month:02d}-{day:02d}"


# ── Node / Edge helpers (same pattern as example_models.py) ─────────────────

def _node(
    nid: str,
    ntype: str,
    data: dict,
    x: int,
    y: int,
    w: int = 200,
    h: int = 80,
    **extra: object,
) -> dict:
    """Build a positioned node dict."""
    result: dict = {
        "id": nid,
        "type": ntype,
        "position": {"x": x, "y": y},
        "data": data,
        "measured": {"width": w, "height": h},
    }
    if "visual" not in data:
        data["visual"] = {"width": w, "height": h}
    else:
        data["visual"]["width"] = w
        data["visual"]["height"] = h
    result.update(extra)
    return result


def _edge(
    eid: str,
    source: str,
    target: str,
    etype: str,
    label: str,
    *,
    source_handle: str | None = None,
    target_handle: str | None = None,
    **extra_data: object,
) -> dict:
    """Build an edge dict."""
    data: dict = {"relationshipType": "uses", "label": label}
    data.update(extra_data)
    result: dict = {
        "id": eid, "source": source, "target": target, "type": "uses",
        "sourceHandle": "center", "targetHandle": "center",
        "data": data,
    }
    return result


def _boundary(nid: str, label: str, x: int, y: int, w: int, h: int) -> dict:
    """Build a boundary (group) node."""
    return {
        "id": nid,
        "type": "boundary",
        "position": {"x": x, "y": y},
        "data": {
            "label": label,
            "entityType": "boundary",
            "visual": {"width": w, "height": h},
        },
        "measured": {"width": w, "height": h},
        "zIndex": -1,
    }


# ── Seed data ───────────────────────────────────────────────────────────────

async def seed_scenia_data(db: DatabasePort) -> None:
    """Create Scenia demo data. Idempotent -- skips if seed marker exists."""
    # Reset counters for idempotency
    _ID_MAP.clear()
    _ID_COUNTERS.clear()

    # Check for existing seed marker (only active sets — uninstall soft-deletes)
    cursor = await db.execute(
        "SELECT id, is_deleted FROM sets WHERE id = ?",
        (_SET_ID,),
    )
    row = await cursor.fetchone()
    if row:
        if not row[1]:
            # Active set exists — already seeded
            return
        # Soft-deleted remnant — un-delete the set and re-seed its contents
        await db.execute(
            "UPDATE sets SET is_deleted = FALSE, updated_at = ? WHERE id = ?",
            (datetime.now(tz=UTC).strftime("%Y-%m-%d_%H:%M:%S"), _SET_ID),
        )
        # Clean up old elements/diagrams so we can re-create them.
        # Delete child rows first to respect FK constraints (works on both SQLite and PostgreSQL).
        await db.execute(
            "DELETE FROM relationship_versions WHERE relationship_id IN "
            "(SELECT id FROM relationships WHERE relationship_type = 'scenia_dependency')",
        )
        await db.execute("DELETE FROM relationships WHERE relationship_type = 'scenia_dependency'")
        await db.execute(
            "DELETE FROM element_versions WHERE element_id IN "
            "(SELECT id FROM elements WHERE set_id = ?)", (_SET_ID,),
        )
        await db.execute("DELETE FROM elements WHERE set_id = ?", (_SET_ID,))
        await db.execute(
            "DELETE FROM diagram_thumbnails WHERE diagram_id IN "
            "(SELECT id FROM diagrams WHERE set_id = ?)", (_SET_ID,),
        )
        await db.execute(
            "DELETE FROM diagram_versions WHERE diagram_id IN "
            "(SELECT id FROM diagrams WHERE set_id = ?)", (_SET_ID,),
        )
        await db.execute("DELETE FROM diagrams WHERE set_id = ?", (_SET_ID,))
        await db.execute("DELETE FROM scenia_asset_categories WHERE set_id = ?", (_SET_ID,))
        await db.execute("DELETE FROM scenia_application_statuses WHERE set_id = ?", (_SET_ID,))
        await db.execute("DELETE FROM scenia_timeline_settings WHERE set_id = ?", (_SET_ID,))
        await db.commit()

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H:%M:%S")

    # Ensure system user exists for FK constraints
    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (_SYSTEM_USER_ID, "system", "!no-login-seed-user", "viewer", False),
    )

    # ── Create the Scenia Extract set ───────────────────────────────────────
    await db.execute(
        "INSERT OR IGNORE INTO sets (id, name, description, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_SET_ID, "Scenia Extract", "Full demo roadmapping data for the Scenia extension", now, _SYSTEM_USER_ID, now),
    )

    # ── Categories (7) ──────────────────────────────────────────────────────
    categories = [
        ("cat-iam", "Identity & Access Management", "#3B82F6", 1),
        ("cat-data", "Data Platform", "#8B5CF6", 2),
        ("cat-channel", "Customer Channels", "#10B981", 3),
        ("cat-core", "Core Banking", "#EF4444", 4),
        ("cat-cloud", "Cloud Infrastructure", "#0EA5E9", 5),
        ("cat-int", "Integration & APIs", "#F59E0B", 6),
        ("cat-geanz", "GEANZ", "#6B7280", 7),
    ]
    for scenia_id, name, color, order in categories:
        cat_id = _map_id(scenia_id, "cat")
        await db.execute(
            "INSERT INTO scenia_asset_categories (id, set_id, name, color, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (cat_id, _SET_ID, name, color, order),
        )

    # ── Strategies (6) ─────────────────────────────────────────────────────
    strategies = [
        ("strat-cloud", "Cloud First", "Prioritise cloud-native solutions for all new workloads", {"color": "bg-sky-500"}),
        ("strat-cust", "Customer First", "Design every service around customer outcomes", {"color": "bg-indigo-500"}),
        ("strat-zero", "Zero Trust", "Implement zero-trust security across all layers", {"color": "bg-rose-500"}),
        ("strat-api", "API-Led Architecture", "Expose all capabilities as well-governed APIs", {"color": "bg-emerald-500"}),
        ("strat-data", "Data-Driven Decisions", "Enable real-time analytics for every business unit", {"color": "bg-amber-500"}),
        ("strat-reg", "Regulatory Compliance", "Maintain continuous compliance with banking regulations", {"color": "bg-orange-500"}),
    ]
    for scenia_id, name, desc, data in strategies:
        sid = _map_id(scenia_id, "strategy")
        await _create_element(db, sid, "scenia_strategy", name, desc, data, now)

    # ── Programmes (6) ──────────────────────────────────────────────────────
    programmes = [
        ("prog-dtp", "Digital Transformation", "Organisation-wide digital transformation programme", {"color": "bg-blue-500"}),
        ("prog-reg", "Regulatory Programme", "Regulatory compliance and reporting programme", {"color": "bg-amber-500"}),
        ("prog-cloud", "Cloud Migration", "Migration of on-premise systems to cloud infrastructure", {"color": "bg-sky-500"}),
        ("prog-cx", "Customer Experience", "Customer experience improvement programme", {"color": "bg-fuchsia-500"}),
        ("prog-mod", "Tech Modernisation", "Legacy technology modernisation programme", {"color": "bg-rose-500"}),
        ("prog-data", "Data & Analytics", "Enterprise data and analytics programme", {"color": "bg-emerald-500"}),
    ]
    for scenia_id, name, desc, data in programmes:
        pid = _map_id(scenia_id, "programme")
        await _create_element(db, pid, "scenia_programme", name, desc, data, now)

    # ── Resources (6) ───────────────────────────────────────────────────────
    resources = [
        ("res-1", "Sarah Chen", "Programme Manager", {"type": "personnel", "role": "Programme Manager"}),
        ("res-2", "James Okafor", "Enterprise Architect", {"type": "personnel", "role": "Enterprise Architect"}),
        ("res-3", "Business Analyst", "Business Analyst", {"type": "personnel", "role": "Business Analyst"}),
        ("res-4", "Maria Santos", "Security Architect", {"type": "personnel", "role": "Security Architect"}),
        ("res-5", "Cloud Engineer", "Cloud Engineer", {"type": "personnel", "role": "Cloud Engineer"}),
        ("res-6", "Tom Wright", "Tech Lead", {"type": "personnel", "role": "Tech Lead"}),
    ]
    for scenia_id, name, desc, data in resources:
        rid = _map_id(scenia_id, "resource")
        await _create_element(db, rid, "scenia_resource", name, desc, data, now)

    # ── Assets (16 banking) ─────────────────────────────────────────────────
    banking_assets = [
        ("a-ciam", "Customer IAM (CIAM)", "Customer identity and access management platform", {"categoryId": _ref("cat-iam"), "maturityRating": 5}),
        ("a-eiam", "Employee IAM", "Employee identity and access management", {"categoryId": _ref("cat-iam"), "maturityRating": 3}),
        ("a-pam", "Privileged Access Mgmt", "Privileged access management for admin accounts", {"categoryId": _ref("cat-iam"), "maturityRating": 1}),
        ("a-lake", "Enterprise Data Lake", "Centralised enterprise data lake", {"categoryId": _ref("cat-data"), "maturityRating": 3}),
        ("a-dwh", "Data Warehouse", "Enterprise data warehouse for reporting", {"categoryId": _ref("cat-data"), "maturityRating": 4}),
        ("a-mdm", "Master Data Mgmt", "Master data management platform", {"categoryId": _ref("cat-data")}),
        ("a-web", "Internet Banking", "Customer-facing internet banking portal", {"categoryId": _ref("cat-channel"), "maturityRating": 4}),
        ("a-mobile", "Mobile Banking App", "Native mobile banking application", {"categoryId": _ref("cat-channel"), "maturityRating": 3}),
        ("a-cc", "Contact Centre Platform", "Omnichannel contact centre solution", {"categoryId": _ref("cat-channel"), "maturityRating": 2}),
        ("a-core", "Core Ledger", "Core banking ledger system", {"categoryId": _ref("cat-core"), "maturityRating": 2}),
        ("a-pay", "Payments Engine", "Real-time payments processing engine", {"categoryId": _ref("cat-core"), "maturityRating": 3}),
        ("a-lend", "Lending Platform", "Lending origination and servicing platform", {"categoryId": _ref("cat-core"), "maturityRating": 2}),
        ("a-k8s", "Kubernetes Platform", "Container orchestration platform", {"categoryId": _ref("cat-cloud"), "maturityRating": 4}),
        ("a-obs", "Observability Stack", "Centralised observability and monitoring stack", {"categoryId": _ref("cat-cloud"), "maturityRating": 3}),
        ("a-apigw", "API Gateway", "Centralised API gateway and management", {"categoryId": _ref("cat-int"), "maturityRating": 4}),
        ("a-esb", "Enterprise Service Bus", "Legacy enterprise service bus", {"categoryId": _ref("cat-int"), "maturityRating": 1}),
    ]
    for scenia_id, name, desc, data in banking_assets:
        aid = _map_id(scenia_id, "asset")
        await _create_element(db, aid, "scenia_asset", name, desc, data, now)

    # ── GEANZ Assets (24) ───────────────────────────────────────────────────
    geanz_assets = [
        ("gz-fmis", "Financial Mgmt Info System", "Government financial management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.01.01"}),
        ("gz-hrm", "Human Resource Mgmt", "HR and payroll management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.01.02"}),
        ("gz-erp", "ERP System", "Government enterprise resource planning", {"categoryId": _ref("cat-geanz"), "alias": "TAP.01.03"}),
        ("gz-case", "Case Management", "Case and workflow management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.02.01"}),
        ("gz-crm", "CRM Platform", "Citizen relationship management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.02.02"}),
        ("gz-portal", "Citizen Portal", "Public-facing citizen service portal", {"categoryId": _ref("cat-geanz"), "alias": "TAP.02.03"}),
        ("gz-wcm", "Web Content Mgmt", "Web content management system", {"categoryId": _ref("cat-geanz"), "alias": "TAP.03.01"}),
        ("gz-datagov", "Data Governance", "Enterprise data governance platform", {"categoryId": _ref("cat-geanz"), "alias": "TAP.03.02"}),
        ("gz-records", "Records Management", "Electronic records management system", {"categoryId": _ref("cat-geanz"), "alias": "TAP.03.03"}),
        ("gz-apimgmt", "API Management", "Government API management platform", {"categoryId": _ref("cat-geanz"), "alias": "TAP.04.01"}),
        ("gz-gesb", "Govt Enterprise Service Bus", "Government enterprise service bus", {"categoryId": _ref("cat-geanz"), "alias": "TAP.04.02"}),
        ("gz-idgov", "Identity Governance", "Identity governance and administration", {"categoryId": _ref("cat-geanz"), "alias": "TAP.05.01"}),
        ("gz-authn", "Authentication Service", "Centralised authentication service", {"categoryId": _ref("cat-geanz"), "alias": "TAP.05.02"}),
        ("gz-netsec", "Network Security", "Network security and firewall management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.05.03"}),
        ("gz-siem", "SIEM Platform", "Security information and event management", {"categoryId": _ref("cat-geanz"), "alias": "TAP.05.04"}),
        ("gz-bpm", "Business Process Mgmt", "Business process management suite", {"categoryId": _ref("cat-geanz"), "alias": "TAP.06.01"}),
        ("gz-itsm", "IT Service Management", "ITSM and service desk platform", {"categoryId": _ref("cat-geanz"), "alias": "TAP.06.02"}),
        ("gz-cmdb", "Configuration Mgmt DB", "Configuration management database", {"categoryId": _ref("cat-geanz"), "alias": "TAP.06.03"}),
        ("gz-email", "Email & Collaboration", "Email and collaboration platform", {"categoryId": _ref("cat-geanz"), "alias": "TAP.07.01"}),
        ("gz-video", "Video Conferencing", "Enterprise video conferencing", {"categoryId": _ref("cat-geanz"), "alias": "TAP.07.02"}),
        ("gz-sysmon", "System Monitoring", "Infrastructure monitoring platform", {"categoryId": _ref("cat-geanz"), "alias": "TAP.08.01"}),
        ("gz-apm", "Application Perf Monitoring", "Application performance monitoring", {"categoryId": _ref("cat-geanz"), "alias": "TAP.08.02"}),
        ("gz-iaas", "IaaS Platform", "Infrastructure as a service", {"categoryId": _ref("cat-geanz"), "alias": "TAP.09.01"}),
        ("gz-paas", "PaaS Platform", "Platform as a service", {"categoryId": _ref("cat-geanz"), "alias": "TAP.09.02"}),
    ]
    for scenia_id, name, desc, data in geanz_assets:
        aid = _map_id(scenia_id, "asset")
        await _create_element(db, aid, "scenia_asset", name, desc, data, now)

    # ── Application Statuses (6) ────────────────────────────────────────────
    app_statuses = [
        ("appstatus-planned", "Planned", "bg-slate-400", 0),
        ("appstatus-funded", "Funded", "bg-blue-400", 1),
        ("appstatus-in-production", "In Production", "bg-emerald-500", 2),
        ("appstatus-sunset", "Sunset", "bg-amber-500", 3),
        ("appstatus-out-of-support", "Out of Support", "bg-orange-500", 4),
        ("appstatus-retired", "Retired", "bg-slate-300", 5),
    ]
    for scenia_id, name, color, order in app_statuses:
        status_id = _map_id(scenia_id, "status")
        await db.execute(
            "INSERT INTO scenia_application_statuses (id, set_id, name, color, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (status_id, _SET_ID, name, color, order),
        )

    # ── Applications (8) ────────────────────────────────────────────────────
    applications = [
        ("app-okta", "Okta", "Cloud-based identity provider", {"assetId": _ref("a-ciam"), "statusId": _ref("appstatus-in-production")}),
        ("app-azuread", "Azure AD", "Microsoft identity platform", {"assetId": _ref("a-ciam"), "statusId": _ref("appstatus-in-production")}),
        ("app-keycloak", "Keycloak", "Open-source IAM solution", {"assetId": _ref("a-ciam"), "statusId": _ref("appstatus-planned")}),
        ("app-angular", "Angular Web App", "Internet banking SPA built in Angular", {"assetId": _ref("a-web"), "statusId": _ref("appstatus-in-production")}),
        ("app-bff", "BFF Service", "Backend-for-frontend API layer", {"assetId": _ref("a-web"), "statusId": _ref("appstatus-in-production")}),
        ("app-ios", "iOS App", "Native iOS banking application", {"assetId": _ref("a-mobile"), "statusId": _ref("appstatus-in-production")}),
        ("app-android", "Android App", "Native Android banking application", {"assetId": _ref("a-mobile"), "statusId": _ref("appstatus-in-production")}),
        ("app-rn", "React Native Shell", "Cross-platform React Native wrapper", {"assetId": _ref("a-mobile"), "statusId": _ref("appstatus-funded")}),
    ]
    for scenia_id, name, desc, data in applications:
        app_id = _map_id(scenia_id, "application")
        await _create_element(db, app_id, "scenia_application", name, desc, data, now)

    # ── Application Segments (~30) ──────────────────────────────────────────
    segments = [
        # Okta segments
        ("seg-okta-1", "Okta - In Production", {"applicationId": _ref("app-okta"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(24)}),
        ("seg-okta-2", "Okta - Sunset", {"applicationId": _ref("app-okta"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(24), "endDate": _rel_date(30)}),
        # Azure AD segments
        ("seg-azuread-1", "Azure AD - In Production", {"applicationId": _ref("app-azuread"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(36)}),
        # Keycloak segments
        ("seg-keycloak-1", "Keycloak - Planned", {"applicationId": _ref("app-keycloak"), "statusId": _ref("appstatus-planned"), "startDate": _rel_date(0), "endDate": _rel_date(6)}),
        ("seg-keycloak-2", "Keycloak - Funded", {"applicationId": _ref("app-keycloak"), "statusId": _ref("appstatus-funded"), "startDate": _rel_date(6), "endDate": _rel_date(12)}),
        ("seg-keycloak-3", "Keycloak - In Production", {"applicationId": _ref("app-keycloak"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(12), "endDate": _rel_date(36)}),
        # Angular Web App segments
        ("seg-angular-1", "Angular Web - In Production", {"applicationId": _ref("app-angular"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(18)}),
        ("seg-angular-2", "Angular Web - Sunset", {"applicationId": _ref("app-angular"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(18), "endDate": _rel_date(24)}),
        ("seg-angular-3", "Angular Web - Out of Support", {"applicationId": _ref("app-angular"), "statusId": _ref("appstatus-out-of-support"), "startDate": _rel_date(24), "endDate": _rel_date(30)}),
        # BFF segments
        ("seg-bff-1", "BFF - In Production", {"applicationId": _ref("app-bff"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(36)}),
        # iOS segments
        ("seg-ios-1", "iOS - In Production", {"applicationId": _ref("app-ios"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(36)}),
        # Android segments
        ("seg-android-1", "Android - In Production", {"applicationId": _ref("app-android"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(0), "endDate": _rel_date(36)}),
        # React Native segments
        ("seg-rn-1", "RN Shell - Planned", {"applicationId": _ref("app-rn"), "statusId": _ref("appstatus-planned"), "startDate": _rel_date(0), "endDate": _rel_date(3)}),
        ("seg-rn-2", "RN Shell - Funded", {"applicationId": _ref("app-rn"), "statusId": _ref("appstatus-funded"), "startDate": _rel_date(3), "endDate": _rel_date(9)}),
        ("seg-rn-3", "RN Shell - In Production", {"applicationId": _ref("app-rn"), "statusId": _ref("appstatus-in-production"), "startDate": _rel_date(9), "endDate": _rel_date(36)}),
        # Additional lifecycle segments for variety
        ("seg-okta-3", "Okta - Retired", {"applicationId": _ref("app-okta"), "statusId": _ref("appstatus-retired"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-angular-4", "Angular Web - Retired", {"applicationId": _ref("app-angular"), "statusId": _ref("appstatus-retired"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        # Extra segments for deeper lifecycle coverage
        ("seg-ios-2", "iOS - Sunset", {"applicationId": _ref("app-ios"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-android-2", "Android - Sunset", {"applicationId": _ref("app-android"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-bff-2", "BFF - Sunset", {"applicationId": _ref("app-bff"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        # Additional app segments
        ("seg-azuread-2", "Azure AD - Funded", {"applicationId": _ref("app-azuread"), "statusId": _ref("appstatus-funded"), "startDate": _rel_date(-6), "endDate": _rel_date(0)}),
        ("seg-keycloak-4", "Keycloak - Sunset", {"applicationId": _ref("app-keycloak"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-rn-4", "RN Shell - Sunset", {"applicationId": _ref("app-rn"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-ios-3", "iOS - Out of Support", {"applicationId": _ref("app-ios"), "statusId": _ref("appstatus-out-of-support"), "startDate": _rel_date(33), "endDate": _rel_date(36)}),
        ("seg-android-3", "Android - Out of Support", {"applicationId": _ref("app-android"), "statusId": _ref("appstatus-out-of-support"), "startDate": _rel_date(33), "endDate": _rel_date(36)}),
        ("seg-angular-5", "Angular Web - Planned", {"applicationId": _ref("app-angular"), "statusId": _ref("appstatus-planned"), "startDate": _rel_date(-6), "endDate": _rel_date(0)}),
        ("seg-bff-3", "BFF - Planned", {"applicationId": _ref("app-bff"), "statusId": _ref("appstatus-planned"), "startDate": _rel_date(-6), "endDate": _rel_date(0)}),
        ("seg-okta-4", "Okta - Funded", {"applicationId": _ref("app-okta"), "statusId": _ref("appstatus-funded"), "startDate": _rel_date(-6), "endDate": _rel_date(0)}),
        ("seg-azuread-3", "Azure AD - Sunset", {"applicationId": _ref("app-azuread"), "statusId": _ref("appstatus-sunset"), "startDate": _rel_date(30), "endDate": _rel_date(36)}),
        ("seg-rn-5", "RN Shell - Out of Support", {"applicationId": _ref("app-rn"), "statusId": _ref("appstatus-out-of-support"), "startDate": _rel_date(33), "endDate": _rel_date(36)}),
    ]
    for scenia_id, name, data in segments:
        seg_id = _map_id(scenia_id, "segment")
        await _create_element(db, seg_id, "scenia_app_segment", name, "", data, now)

    # ── Initiatives (~40) ───────────────────────────────────────────────────
    initiatives = [
        # Digital Transformation Programme
        ("init-1", "CIAM Platform Refresh", "Replace legacy CIAM with modern cloud-native IAM",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-ciam"),
          "startDate": _rel_date(0), "endDate": _rel_date(8), "budget": 1200000,
          "status": "in_progress", "progress": 45, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-4"), _ref("res-6")]}),
        ("init-2", "Employee IAM Consolidation", "Consolidate employee identity across all business units",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-zero"), "assetId": _ref("a-eiam"),
          "startDate": _rel_date(3), "endDate": _rel_date(12), "budget": 800000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-4"), "resourceIds": [_ref("res-2")]}),
        ("init-3", "PAM Implementation", "Deploy privileged access management solution",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-zero"), "assetId": _ref("a-pam"),
          "startDate": _rel_date(6), "endDate": _rel_date(14), "budget": 600000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-4"), "resourceIds": [_ref("res-5")]}),
        ("init-4", "Internet Banking Redesign", "Complete UX overhaul of internet banking portal",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-cust"), "assetId": _ref("a-web"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 1500000,
          "status": "in_progress", "progress": 25, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-3"), _ref("res-6")]}),
        ("init-5", "Mobile App v3", "Next-generation mobile banking experience",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-cust"), "assetId": _ref("a-mobile"),
          "startDate": _rel_date(4), "endDate": _rel_date(14), "budget": 2000000,
          "status": "planned", "progress": 5, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-3")]}),

        # Regulatory Programme
        ("init-6", "Data Governance Framework", "Implement enterprise data governance for regulatory compliance",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-reg"), "assetId": _ref("a-mdm"),
          "startDate": _rel_date(1), "endDate": _rel_date(9), "budget": 700000,
          "status": "in_progress", "progress": 30, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-3")]}),
        ("init-7", "Regulatory Reporting Automation", "Automate regulatory reporting via data warehouse",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-data"), "assetId": _ref("a-dwh"),
          "startDate": _rel_date(3), "endDate": _rel_date(11), "budget": 900000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-3"), _ref("res-5")]}),
        ("init-8", "SIEM Enhancement", "Upgrade SIEM for real-time threat detection and compliance",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-zero"), "assetId": _ref("a-obs"),
          "startDate": _rel_date(2), "endDate": _rel_date(8), "budget": 500000,
          "status": "in_progress", "progress": 20, "ownerId": _ref("res-4"), "resourceIds": [_ref("res-5")]}),
        ("init-9", "Core Ledger Compliance Update", "Update core ledger for new regulatory requirements",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-reg"), "assetId": _ref("a-core"),
          "startDate": _rel_date(5), "endDate": _rel_date(13), "budget": 1100000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-2"), _ref("res-6")]}),

        # Cloud Migration Programme
        ("init-10", "Kubernetes Platform Build", "Build enterprise Kubernetes platform for workload hosting",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-k8s"),
          "startDate": _rel_date(0), "endDate": _rel_date(6), "budget": 1800000,
          "status": "in_progress", "progress": 60, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-6")]}),
        ("init-11", "Observability Platform", "Deploy comprehensive observability stack",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-obs"),
          "startDate": _rel_date(2), "endDate": _rel_date(8), "budget": 600000,
          "status": "in_progress", "progress": 35, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-6")]}),
        ("init-12", "Data Lake Cloud Migration", "Migrate on-premise data lake to cloud",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-lake"),
          "startDate": _rel_date(4), "endDate": _rel_date(12), "budget": 1400000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-2")]}),
        ("init-13", "ESB Decommission", "Decommission legacy ESB and migrate to API-led integration",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-api"), "assetId": _ref("a-esb"),
          "startDate": _rel_date(8), "endDate": _rel_date(18), "budget": 900000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-6")]}),
        ("init-14", "Contact Centre Cloud Move", "Migrate contact centre to cloud-based CCaaS",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-cc"),
          "startDate": _rel_date(6), "endDate": _rel_date(14), "budget": 750000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-3")]}),

        # Customer Experience Programme
        ("init-15", "Omnichannel Contact Centre", "Implement omnichannel customer engagement",
         {"programmeId": _ref("prog-cx"), "strategyId": _ref("strat-cust"), "assetId": _ref("a-cc"),
          "startDate": _rel_date(1), "endDate": _rel_date(9), "budget": 1100000,
          "status": "in_progress", "progress": 15, "ownerId": _ref("res-3"), "resourceIds": [_ref("res-1")]}),
        ("init-16", "Customer 360 View", "Build unified customer data view across all channels",
         {"programmeId": _ref("prog-cx"), "strategyId": _ref("strat-data"), "assetId": _ref("a-mdm"),
          "startDate": _rel_date(3), "endDate": _rel_date(11), "budget": 800000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-3")]}),
        ("init-17", "Real-time Payments", "Enable real-time payment processing",
         {"programmeId": _ref("prog-cx"), "strategyId": _ref("strat-cust"), "assetId": _ref("a-pay"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 1300000,
          "status": "in_progress", "progress": 20, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-5")]}),
        ("init-18", "Digital Lending Portal", "Launch self-service digital lending platform",
         {"programmeId": _ref("prog-cx"), "strategyId": _ref("strat-cust"), "assetId": _ref("a-lend"),
          "startDate": _rel_date(5), "endDate": _rel_date(15), "budget": 1600000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-3"), _ref("res-6")]}),

        # Tech Modernisation Programme
        ("init-19", "Core Ledger Modernisation", "Replace legacy core banking with modern platform",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-cloud"), "assetId": _ref("a-core"),
          "startDate": _rel_date(6), "endDate": _rel_date(24), "budget": 5000000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-2"), _ref("res-6")]}),
        ("init-20", "API Gateway Upgrade", "Upgrade API gateway to support GraphQL and gRPC",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-api"), "assetId": _ref("a-apigw"),
          "startDate": _rel_date(1), "endDate": _rel_date(7), "budget": 500000,
          "status": "in_progress", "progress": 40, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-5")]}),
        ("init-21", "ESB to API Migration", "Migrate ESB integrations to API-first pattern",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-api"), "assetId": _ref("a-esb"),
          "startDate": _rel_date(4), "endDate": _rel_date(16), "budget": 1200000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-6")]}),
        ("init-22", "Data Warehouse Modernisation", "Modernise data warehouse with cloud-native tech",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-data"), "assetId": _ref("a-dwh"),
          "startDate": _rel_date(3), "endDate": _rel_date(11), "budget": 1000000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-5")]}),

        # Data & Analytics Programme
        ("init-23", "Enterprise Data Lake Build", "Build cloud-native enterprise data lake",
         {"programmeId": _ref("prog-data"), "strategyId": _ref("strat-data"), "assetId": _ref("a-lake"),
          "startDate": _rel_date(0), "endDate": _rel_date(8), "budget": 1500000,
          "status": "in_progress", "progress": 50, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-5")]}),
        ("init-24", "MDM Platform Implementation", "Implement master data management platform",
         {"programmeId": _ref("prog-data"), "strategyId": _ref("strat-data"), "assetId": _ref("a-mdm"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 800000,
          "status": "in_progress", "progress": 15, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-3")]}),
        ("init-25", "Analytics Self-Service", "Enable self-service analytics for business users",
         {"programmeId": _ref("prog-data"), "strategyId": _ref("strat-data"), "assetId": _ref("a-dwh"),
          "startDate": _rel_date(6), "endDate": _rel_date(14), "budget": 600000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-3"), "resourceIds": [_ref("res-2")]}),
        ("init-26", "Real-time Data Streaming", "Implement real-time data streaming infrastructure",
         {"programmeId": _ref("prog-data"), "strategyId": _ref("strat-data"), "assetId": _ref("a-lake"),
          "startDate": _rel_date(4), "endDate": _rel_date(12), "budget": 700000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-6")]}),

        # GEANZ Initiatives
        ("init-27", "FMIS Cloud Migration", "Migrate financial management to cloud",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-fmis"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 900000,
          "status": "in_progress", "progress": 20, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-2")]}),
        ("init-28", "HRM Modernisation", "Modernise HR management system",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-hrm"),
          "startDate": _rel_date(4), "endDate": _rel_date(14), "budget": 700000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-1"), "resourceIds": [_ref("res-3")]}),
        ("init-29", "Case Mgmt Platform", "Implement new case management platform",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-cust"), "assetId": _ref("gz-case"),
          "startDate": _rel_date(1), "endDate": _rel_date(9), "budget": 800000,
          "status": "in_progress", "progress": 30, "ownerId": _ref("res-3"), "resourceIds": [_ref("res-6")]}),
        ("init-30", "Citizen Portal Rebuild", "Rebuild citizen portal with modern UX",
         {"programmeId": _ref("prog-cx"), "strategyId": _ref("strat-cust"), "assetId": _ref("gz-portal"),
          "startDate": _rel_date(3), "endDate": _rel_date(11), "budget": 1100000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-3")]}),
        ("init-31", "Identity Governance Rollout", "Deploy identity governance across all agencies",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-zero"), "assetId": _ref("gz-idgov"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 600000,
          "status": "in_progress", "progress": 25, "ownerId": _ref("res-4"), "resourceIds": [_ref("res-5")]}),
        ("init-32", "SIEM Platform Deployment", "Deploy centralised SIEM for threat monitoring",
         {"programmeId": _ref("prog-reg"), "strategyId": _ref("strat-zero"), "assetId": _ref("gz-siem"),
          "startDate": _rel_date(1), "endDate": _rel_date(7), "budget": 500000,
          "status": "in_progress", "progress": 40, "ownerId": _ref("res-4"), "resourceIds": [_ref("res-5")]}),
        ("init-33", "ITSM Consolidation", "Consolidate IT service management platforms",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-itsm"),
          "startDate": _rel_date(5), "endDate": _rel_date(13), "budget": 450000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-2")]}),
        ("init-34", "API Mgmt Platform", "Deploy centralised API management platform",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-api"), "assetId": _ref("gz-apimgmt"),
          "startDate": _rel_date(3), "endDate": _rel_date(9), "budget": 550000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-2")]}),
        ("init-35", "BPM Automation", "Implement business process management automation",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-api"), "assetId": _ref("gz-bpm"),
          "startDate": _rel_date(4), "endDate": _rel_date(12), "budget": 650000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-3"), "resourceIds": [_ref("res-6")]}),
        ("init-36", "Data Governance Platform", "Implement enterprise data governance",
         {"programmeId": _ref("prog-data"), "strategyId": _ref("strat-data"), "assetId": _ref("gz-datagov"),
          "startDate": _rel_date(2), "endDate": _rel_date(10), "budget": 700000,
          "status": "in_progress", "progress": 10, "ownerId": _ref("res-2"), "resourceIds": [_ref("res-3")]}),
        ("init-37", "Records Mgmt Digitisation", "Digitise records management processes",
         {"programmeId": _ref("prog-dtp"), "strategyId": _ref("strat-data"), "assetId": _ref("gz-records"),
          "startDate": _rel_date(6), "endDate": _rel_date(14), "budget": 400000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-3"), "resourceIds": [_ref("res-2")]}),
        ("init-38", "IaaS Platform Expansion", "Expand infrastructure-as-a-service capabilities",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-iaas"),
          "startDate": _rel_date(1), "endDate": _rel_date(7), "budget": 1200000,
          "status": "in_progress", "progress": 55, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-6")]}),
        ("init-39", "PaaS Enablement", "Enable platform-as-a-service for development teams",
         {"programmeId": _ref("prog-cloud"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-paas"),
          "startDate": _rel_date(3), "endDate": _rel_date(11), "budget": 800000,
          "status": "planned", "progress": 0, "ownerId": _ref("res-5"), "resourceIds": [_ref("res-6")]}),
        ("init-40", "Email & Collaboration Upgrade", "Upgrade email and collaboration platform",
         {"programmeId": _ref("prog-mod"), "strategyId": _ref("strat-cloud"), "assetId": _ref("gz-email"),
          "startDate": _rel_date(2), "endDate": _rel_date(6), "budget": 350000,
          "status": "in_progress", "progress": 50, "ownerId": _ref("res-6"), "resourceIds": [_ref("res-5")]}),
    ]
    for scenia_id, name, desc, data in initiatives:
        iid = _map_id(scenia_id, "initiative")
        await _create_element(db, iid, "scenia_initiative", name, desc, data, now)

    # ── Dependencies (9: dep-1 to dep-10, no dep-4) ─────────────────────────
    dependencies = [
        ("dep-1", "init-10", "init-11", "blocks"),    # K8s platform blocks observability
        ("dep-2", "init-10", "init-12", "blocks"),    # K8s platform blocks data lake migration
        ("dep-3", "init-1", "init-2", "requires"),    # CIAM refresh required by employee IAM
        ("dep-5", "init-20", "init-21", "blocks"),    # API gateway upgrade blocks ESB migration
        ("dep-6", "init-6", "init-7", "requires"),    # Data governance required by regulatory reporting
        ("dep-7", "init-23", "init-26", "blocks"),    # Data lake build blocks real-time streaming
        ("dep-8", "init-2", "init-3", "requires"),    # Employee IAM required by PAM
        ("dep-9", "init-19", "init-9", "blocks"),     # Core modernisation blocks compliance update
        ("dep-10", "init-24", "init-16", "requires"), # MDM required by Customer 360
    ]
    for scenia_id, src, tgt, dep_type in dependencies:
        dep_id = _map_id(scenia_id, "dep")
        await _create_dependency(db, dep_id, _ref(src), _ref(tgt), dep_type, now)

    # ── Milestones (14: 8 banking + 6 GEANZ) ────────────────────────────────
    milestones = [
        # Banking milestones
        ("ms-1", "K8s Platform GA", "Kubernetes platform generally available", {"date": _rel_date(6), "severity": "critical"}),
        ("ms-2", "CIAM Migration Complete", "All customers migrated to new CIAM", {"date": _rel_date(8), "severity": "critical"}),
        ("ms-3", "API Gateway v2 Live", "New API gateway in production", {"date": _rel_date(7), "severity": "major"}),
        ("ms-4", "Data Lake MVP", "Enterprise data lake minimum viable product", {"date": _rel_date(8), "severity": "major"}),
        ("ms-5", "Core Ledger RFP", "Core ledger replacement RFP issued", {"date": _rel_date(6), "severity": "major"}),
        ("ms-6", "Regulatory Report Auto", "Automated regulatory reporting live", {"date": _rel_date(11), "severity": "critical"}),
        ("ms-7", "Mobile v3 Beta", "Mobile banking v3 beta release", {"date": _rel_date(10), "severity": "major"}),
        ("ms-8", "ESB Sunset Date", "Enterprise service bus end-of-life", {"date": _rel_date(18), "severity": "critical"}),
        # GEANZ milestones
        ("ms-gz-1", "FMIS Cloud Go-Live", "Financial management system live in cloud", {"date": _rel_date(10), "severity": "critical"}),
        ("ms-gz-2", "Identity Gov Phase 1", "Identity governance rollout phase 1 complete", {"date": _rel_date(6), "severity": "major"}),
        ("ms-gz-3", "Citizen Portal Beta", "New citizen portal beta release", {"date": _rel_date(8), "severity": "major"}),
        ("ms-gz-4", "SIEM Operational", "SIEM platform fully operational", {"date": _rel_date(7), "severity": "critical"}),
        ("ms-gz-5", "IaaS Expansion Complete", "IaaS platform expansion complete", {"date": _rel_date(7), "severity": "major"}),
        ("ms-gz-6", "BPM Automation Live", "Business process automation in production", {"date": _rel_date(12), "severity": "major"}),
    ]
    for scenia_id, name, desc, data in milestones:
        mid = _map_id(scenia_id, "milestone")
        await _create_element(db, mid, "scenia_milestone", name, desc, data, now)

    # ── Timeline Settings ───────────────────────────────────────────────────
    await db.execute(
        "INSERT INTO scenia_timeline_settings (id, set_id, start_date, end_date, view_mode, zoom_level, data, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (_gen_id("timeline", 0), _SET_ID, _rel_date(0), _rel_date(36), "quarterly", 1.0,
         json.dumps({
             "monthsToShow": 36,
             "showMilestones": True,
             "showDependencies": True,
             "showProgress": True,
             "showBudget": True,
         }), now),
    )

    # ── Diagrams (10) ───────────────────────────────────────────────────────
    await _create_diagrams(db, now)

    await db.commit()


# ── Diagram builders ────────────────────────────────────────────────────────

# Programme ID to Scenia key mapping for initiative lookups
_PROGRAMME_KEYS = ["prog-dtp", "prog-reg", "prog-cloud", "prog-cx", "prog-mod", "prog-data"]

# All initiative Scenia keys
_ALL_INIT_KEYS = [f"init-{i}" for i in range(1, 41)]

# Initiatives by programme (Scenia key -> list of initiative Scenia keys)
_PROG_INITS: dict[str, list[str]] = {
    "prog-dtp": ["init-1", "init-2", "init-3", "init-4", "init-5", "init-29", "init-35", "init-37"],
    "prog-reg": ["init-6", "init-7", "init-8", "init-9", "init-31", "init-32"],
    "prog-cloud": ["init-10", "init-11", "init-12", "init-13", "init-14", "init-27", "init-38", "init-39"],
    "prog-cx": ["init-15", "init-16", "init-17", "init-18", "init-30"],
    "prog-mod": ["init-19", "init-20", "init-21", "init-22", "init-28", "init-33", "init-34", "init-40"],
    "prog-data": ["init-23", "init-24", "init-25", "init-26", "init-36"],
}

# Strategy -> Programme linkage (based on initiative assignments)
_STRAT_PROG_LINKS: list[tuple[str, str]] = [
    ("strat-cloud", "prog-dtp"), ("strat-cloud", "prog-cloud"), ("strat-cloud", "prog-mod"),
    ("strat-cust", "prog-dtp"), ("strat-cust", "prog-cx"),
    ("strat-zero", "prog-dtp"), ("strat-zero", "prog-reg"),
    ("strat-api", "prog-cloud"), ("strat-api", "prog-mod"),
    ("strat-data", "prog-reg"), ("strat-data", "prog-cx"), ("strat-data", "prog-mod"), ("strat-data", "prog-data"),
    ("strat-reg", "prog-reg"),
]

# Dependencies as (source_init, target_init) pairs
_DEP_PAIRS = [
    ("init-10", "init-11"), ("init-10", "init-12"), ("init-1", "init-2"),
    ("init-20", "init-21"), ("init-6", "init-7"), ("init-23", "init-26"),
    ("init-2", "init-3"), ("init-19", "init-9"), ("init-24", "init-16"),
]

# Category -> asset mapping
_CAT_ASSETS: dict[str, list[str]] = {
    "cat-iam": ["a-ciam", "a-eiam", "a-pam"],
    "cat-data": ["a-lake", "a-dwh", "a-mdm"],
    "cat-channel": ["a-web", "a-mobile", "a-cc"],
    "cat-core": ["a-core", "a-pay", "a-lend"],
    "cat-cloud": ["a-k8s", "a-obs"],
    "cat-int": ["a-apigw", "a-esb"],
    "cat-geanz": [
        "gz-fmis", "gz-hrm", "gz-erp", "gz-case", "gz-crm", "gz-portal",
        "gz-wcm", "gz-datagov", "gz-records", "gz-apimgmt", "gz-gesb",
        "gz-idgov", "gz-authn", "gz-netsec", "gz-siem", "gz-bpm",
        "gz-itsm", "gz-cmdb", "gz-email", "gz-video", "gz-sysmon",
        "gz-apm", "gz-iaas", "gz-paas",
    ],
}

# Resource -> initiative assignments (based on ownerId and resourceIds)
_RES_INITS: dict[str, list[str]] = {
    "res-1": ["init-1", "init-4", "init-9", "init-14", "init-18", "init-19", "init-28"],
    "res-2": ["init-6", "init-7", "init-13", "init-16", "init-21", "init-22", "init-23", "init-24", "init-36"],
    "res-3": ["init-15", "init-25", "init-29", "init-30", "init-35", "init-37"],
    "res-4": ["init-2", "init-3", "init-8", "init-31", "init-32"],
    "res-5": ["init-10", "init-11", "init-12", "init-38", "init-39", "init-40"],
    "res-6": ["init-5", "init-17", "init-20", "init-33", "init-34", "init-40"],
}


def _build_strategic_overview(diagram_ids: dict[int, str]) -> dict:
    """Diagram 1: Strategic Overview -- strategies (top) linked to programmes (bottom)."""
    strat_keys = ["strat-cloud", "strat-cust", "strat-zero", "strat-api", "strat-data", "strat-reg"]
    prog_keys = _PROGRAMME_KEYS

    nodes = []
    # Strategy nodes (top row)
    for i, sk in enumerate(strat_keys):
        nodes.append(_node(
            f"s-{sk}", "component",
            {"label": _get_strategy_name(sk), "entityType": "scenia_strategy",
             "entityId": _ref(sk)},
            i * 250, 0, 200, 80,
        ))

    # Programme nodes (bottom row) with linkedModelId to programme roadmap diagrams
    for i, pk in enumerate(prog_keys):
        nodes.append(_node(
            f"p-{pk}", "component",
            {"label": _get_programme_name(pk), "entityType": "scenia_programme",
             "entityId": _ref(pk),
             "linkedModelId": diagram_ids.get(1 + i, "")},
            i * 250, 200, 200, 80,
        ))

    # Edges from strategies to programmes
    edges = []
    for ei, (sk, pk) in enumerate(_STRAT_PROG_LINKS):
        edges.append(_edge(
            f"e-sp-{ei}", f"s-{sk}", f"p-{pk}", "association", "drives",
            source_handle="bottom", target_handle="top",
        ))

    return {"nodes": nodes, "edges": edges}


def _build_programme_roadmap(prog_key: str) -> dict:
    """Diagrams 2-7: Programme Roadmap for a specific programme."""
    init_keys = _PROG_INITS.get(prog_key, [])

    nodes = []
    # Programme node at top
    nodes.append(_node(
        f"prog-{prog_key}", "component",
        {"label": _get_programme_name(prog_key), "entityType": "scenia_programme",
         "entityId": _ref(prog_key)},
        300, 0, 220, 80,
    ))

    # Initiative nodes arranged in rows
    for i, ik in enumerate(init_keys):
        col = i % 3
        row = i // 3
        nodes.append(_node(
            f"init-{ik}", "component",
            {"label": _get_initiative_name(ik), "entityType": "scenia_initiative",
             "entityId": _ref(ik)},
            col * 280, 120 + row * 120, 240, 80,
        ))

    edges = []
    # Programme -> initiative edges
    for i, ik in enumerate(init_keys):
        edges.append(_edge(
            f"e-pi-{i}", f"prog-{prog_key}", f"init-{ik}", "association", "includes",
            source_handle="bottom", target_handle="top",
        ))

    # Dependency edges within this programme's initiatives
    ei = len(init_keys)
    for src, tgt in _DEP_PAIRS:
        if src in init_keys and tgt in init_keys:
            edges.append(_edge(
                f"e-dep-{ei}", f"init-{src}", f"init-{tgt}", "dependency", "depends on",
                source_handle="right", target_handle="left",
            ))
            ei += 1

    return {"nodes": nodes, "edges": edges}


def _build_asset_landscape() -> dict:
    """Diagram 8: Asset Landscape -- categories as boundaries with asset nodes inside."""
    nodes = []
    edges = []

    # Layout: categories in rows, max 3 columns
    cat_keys = ["cat-iam", "cat-data", "cat-channel", "cat-core", "cat-cloud", "cat-int", "cat-geanz"]
    cat_names = {
        "cat-iam": "Identity & Access Management", "cat-data": "Data Platform",
        "cat-channel": "Customer Channels", "cat-core": "Core Banking",
        "cat-cloud": "Cloud Infrastructure", "cat-int": "Integration & APIs",
        "cat-geanz": "GEANZ",
    }

    y_offset = 0
    for ci, ck in enumerate(cat_keys):
        assets = _CAT_ASSETS.get(ck, [])
        # Calculate boundary size based on number of assets
        cols = min(3, len(assets))
        rows = (len(assets) + 2) // 3
        bw = cols * 220 + 40
        bh = rows * 100 + 50

        # Boundary node
        nodes.append(_boundary(f"cat-{ck}", cat_names[ck], 0, y_offset, bw, bh))

        # Asset nodes within boundary
        for ai, ak in enumerate(assets):
            col = ai % 3
            row = ai // 3
            nodes.append(_node(
                f"asset-{ak}", "component",
                {"label": _get_asset_name(ak), "entityType": "scenia_asset",
                 "entityId": _ref(ak)},
                20 + col * 220, y_offset + 40 + row * 100, 200, 70,
            ))

        y_offset += bh + 30

    return {"nodes": nodes, "edges": edges}


def _build_dependency_map() -> dict:
    """Diagram 9: Dependency Map -- all initiatives with dependency edges."""
    nodes = []
    edges = []

    # Only include initiatives that participate in dependencies
    dep_inits = set()
    for src, tgt in _DEP_PAIRS:
        dep_inits.add(src)
        dep_inits.add(tgt)

    sorted_inits = sorted(dep_inits, key=lambda x: int(x.split("-")[1]))

    for i, ik in enumerate(sorted_inits):
        col = i % 4
        row = i // 4
        nodes.append(_node(
            f"dep-{ik}", "component",
            {"label": _get_initiative_name(ik), "entityType": "scenia_initiative",
             "entityId": _ref(ik)},
            col * 280, row * 140, 240, 80,
        ))

    for ei, (src, tgt) in enumerate(_DEP_PAIRS):
        edges.append(_edge(
            f"e-d-{ei}", f"dep-{src}", f"dep-{tgt}", "dependency", "depends on",
            source_handle="right", target_handle="left",
        ))

    return {"nodes": nodes, "edges": edges}


def _build_resource_allocation() -> dict:
    """Diagram 10: Resource Allocation -- resource nodes linked to initiative nodes."""
    nodes = []
    edges = []

    res_keys = ["res-1", "res-2", "res-3", "res-4", "res-5", "res-6"]
    res_names = {
        "res-1": "Sarah Chen", "res-2": "James Okafor", "res-3": "Business Analyst",
        "res-4": "Maria Santos", "res-5": "Cloud Engineer", "res-6": "Tom Wright",
    }

    # Resource nodes on the left
    for ri, rk in enumerate(res_keys):
        nodes.append(_node(
            f"res-{rk}", "component",
            {"label": res_names[rk], "entityType": "scenia_resource",
             "entityId": _ref(rk)},
            0, ri * 140, 180, 80,
        ))

    # Collect unique initiatives referenced by resources
    all_init_set: set[str] = set()
    for inits in _RES_INITS.values():
        all_init_set.update(inits)
    sorted_res_inits = sorted(all_init_set, key=lambda x: int(x.split("-")[1]))

    # Initiative nodes on the right
    for ii, ik in enumerate(sorted_res_inits):
        col = ii % 3
        row = ii // 3
        nodes.append(_node(
            f"ra-{ik}", "component",
            {"label": _get_initiative_name(ik), "entityType": "scenia_initiative",
             "entityId": _ref(ik)},
            300 + col * 260, row * 100, 220, 70,
        ))

    # Edges from resources to initiatives
    ei = 0
    for rk in res_keys:
        for ik in _RES_INITS.get(rk, []):
            edges.append(_edge(
                f"e-ra-{ei}", f"res-{rk}", f"ra-{ik}", "association", "assigned to",
                source_handle="right", target_handle="left",
            ))
            ei += 1

    return {"nodes": nodes, "edges": edges}


# ── Name lookup helpers ─────────────────────────────────────────────────────

_STRATEGY_NAMES = {
    "strat-cloud": "Cloud First", "strat-cust": "Customer First",
    "strat-zero": "Zero Trust", "strat-api": "API-Led Architecture",
    "strat-data": "Data-Driven Decisions", "strat-reg": "Regulatory Compliance",
}

_PROGRAMME_NAMES = {
    "prog-dtp": "Digital Transformation", "prog-reg": "Regulatory Programme",
    "prog-cloud": "Cloud Migration", "prog-cx": "Customer Experience",
    "prog-mod": "Tech Modernisation", "prog-data": "Data & Analytics",
}

_INITIATIVE_NAMES = {
    "init-1": "CIAM Platform Refresh", "init-2": "Employee IAM Consolidation",
    "init-3": "PAM Implementation", "init-4": "Internet Banking Redesign",
    "init-5": "Mobile App v3", "init-6": "Data Governance Framework",
    "init-7": "Regulatory Reporting Automation", "init-8": "SIEM Enhancement",
    "init-9": "Core Ledger Compliance Update", "init-10": "Kubernetes Platform Build",
    "init-11": "Observability Platform", "init-12": "Data Lake Cloud Migration",
    "init-13": "ESB Decommission", "init-14": "Contact Centre Cloud Move",
    "init-15": "Omnichannel Contact Centre", "init-16": "Customer 360 View",
    "init-17": "Real-time Payments", "init-18": "Digital Lending Portal",
    "init-19": "Core Ledger Modernisation", "init-20": "API Gateway Upgrade",
    "init-21": "ESB to API Migration", "init-22": "Data Warehouse Modernisation",
    "init-23": "Enterprise Data Lake Build", "init-24": "MDM Platform Implementation",
    "init-25": "Analytics Self-Service", "init-26": "Real-time Data Streaming",
    "init-27": "FMIS Cloud Migration", "init-28": "HRM Modernisation",
    "init-29": "Case Mgmt Platform", "init-30": "Citizen Portal Rebuild",
    "init-31": "Identity Governance Rollout", "init-32": "SIEM Platform Deployment",
    "init-33": "ITSM Consolidation", "init-34": "API Mgmt Platform",
    "init-35": "BPM Automation", "init-36": "Data Governance Platform",
    "init-37": "Records Mgmt Digitisation", "init-38": "IaaS Platform Expansion",
    "init-39": "PaaS Enablement", "init-40": "Email & Collaboration Upgrade",
}

_ASSET_NAMES = {
    "a-ciam": "Customer IAM (CIAM)", "a-eiam": "Employee IAM",
    "a-pam": "Privileged Access Mgmt", "a-lake": "Enterprise Data Lake",
    "a-dwh": "Data Warehouse", "a-mdm": "Master Data Mgmt",
    "a-web": "Internet Banking", "a-mobile": "Mobile Banking App",
    "a-cc": "Contact Centre Platform", "a-core": "Core Ledger",
    "a-pay": "Payments Engine", "a-lend": "Lending Platform",
    "a-k8s": "Kubernetes Platform", "a-obs": "Observability Stack",
    "a-apigw": "API Gateway", "a-esb": "Enterprise Service Bus",
    "gz-fmis": "Financial Mgmt Info System", "gz-hrm": "Human Resource Mgmt",
    "gz-erp": "ERP System", "gz-case": "Case Management",
    "gz-crm": "CRM Platform", "gz-portal": "Citizen Portal",
    "gz-wcm": "Web Content Mgmt", "gz-datagov": "Data Governance",
    "gz-records": "Records Management", "gz-apimgmt": "API Management",
    "gz-gesb": "Govt Enterprise Service Bus", "gz-idgov": "Identity Governance",
    "gz-authn": "Authentication Service", "gz-netsec": "Network Security",
    "gz-siem": "SIEM Platform", "gz-bpm": "Business Process Mgmt",
    "gz-itsm": "IT Service Management", "gz-cmdb": "Configuration Mgmt DB",
    "gz-email": "Email & Collaboration", "gz-video": "Video Conferencing",
    "gz-sysmon": "System Monitoring", "gz-apm": "Application Perf Monitoring",
    "gz-iaas": "IaaS Platform", "gz-paas": "PaaS Platform",
}


def _get_strategy_name(key: str) -> str:
    return _STRATEGY_NAMES.get(key, key)


def _get_programme_name(key: str) -> str:
    return _PROGRAMME_NAMES.get(key, key)


def _get_initiative_name(key: str) -> str:
    return _INITIATIVE_NAMES.get(key, key)


def _get_asset_name(key: str) -> str:
    return _ASSET_NAMES.get(key, key)


# ── Create diagrams ─────────────────────────────────────────────────────────

async def _create_diagrams(db: DatabasePort, now: str) -> None:
    """Create 10 interlinked diagrams in the Scenia Extract set."""
    # Pre-generate all diagram IDs (indices 0-9)
    diagram_ids: dict[int, str] = {}
    for i in range(10):
        diagram_ids[i] = _gen_id("diagram", i)

    diagram_defs = [
        # Index 0: Strategic Overview
        {
            "index": 0,
            "name": "Strategic Overview",
            "description": "High-level view of all strategies and programmes with linkages",
            "builder": lambda: _build_strategic_overview(diagram_ids),
        },
    ]

    # Indices 1-6: Programme Roadmaps
    for pi, pk in enumerate(_PROGRAMME_KEYS):
        diagram_defs.append({
            "index": 1 + pi,
            "name": f"{_get_programme_name(pk)} Roadmap",
            "description": f"Detailed initiative roadmap for the {_get_programme_name(pk)} programme",
            "builder": lambda _pk=pk: _build_programme_roadmap(_pk),
        })

    # Index 7: Asset Landscape
    diagram_defs.append({
        "index": 7,
        "name": "Asset Landscape",
        "description": "All assets organised by category with maturity and ownership data",
        "builder": _build_asset_landscape,
    })

    # Index 8: Dependency Map
    diagram_defs.append({
        "index": 8,
        "name": "Dependency Map",
        "description": "Initiative dependencies showing blocks and requires relationships",
        "builder": _build_dependency_map,
    })

    # Index 9: Resource Allocation
    diagram_defs.append({
        "index": 9,
        "name": "Resource Allocation",
        "description": "Resource assignments across initiatives",
        "builder": _build_resource_allocation,
    })

    for ddef in diagram_defs:
        diagram_id = diagram_ids[ddef["index"]]
        diagram_data = ddef["builder"]()
        diagram_data_json = json.dumps(diagram_data)

        await db.execute(
            "INSERT INTO diagrams (id, diagram_type, set_id, current_version, "
            "created_at, created_by, updated_at, notation) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
            (diagram_id, "simple-view", _SET_ID, now, _SYSTEM_USER_ID, now, "scenia"),
        )
        await db.execute(
            "INSERT INTO diagram_versions (diagram_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
            (diagram_id, ddef["name"], ddef["description"],
             diagram_data_json, now, _SYSTEM_USER_ID),
        )


# ── Element / dependency helpers ────────────────────────────────────────────

async def _create_element(
    db: DatabasePort,
    element_id: str,
    element_type: str,
    name: str,
    description: str,
    data: dict,
    now: str,
) -> None:
    """Insert an element and its initial version."""
    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, created_at, created_by, updated_at, set_id, notation) "
        "VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
        (element_id, element_type, now, _SYSTEM_USER_ID, now, _SET_ID, "scenia"),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (element_id, name, description, json.dumps(data), now, _SYSTEM_USER_ID),
    )


async def _create_dependency(
    db: DatabasePort,
    rel_id: str,
    source_id: str,
    target_id: str,
    dep_type: str,
    now: str,
) -> None:
    """Insert a Scenia dependency as an Iris relationship."""
    data = json.dumps({"dependency_type": dep_type, "set_id": _SET_ID})
    await db.execute(
        "INSERT INTO relationships (id, source_element_id, target_element_id, relationship_type, "
        "current_version, created_at, created_by, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (rel_id, source_id, target_id, "scenia_dependency", now, _SYSTEM_USER_ID, now),
    )
    await db.execute(
        "INSERT INTO relationship_versions (relationship_id, version, label, description, data, "
        "change_type, created_at, created_by) VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (rel_id, dep_type, None, data, now, _SYSTEM_USER_ID),
    )


# ── Cleanup ─────────────────────────────────────────────────────────────────

async def remove_scenia_seed_data(db: DatabasePort) -> None:
    """Remove Scenia seed data on uninstall. Soft-deletes elements and relationships."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H:%M:%S")

    # Soft-delete all elements in the Scenia set
    await db.execute(
        "UPDATE elements SET is_deleted = TRUE, updated_at = ? WHERE set_id = ? AND element_type LIKE 'scenia_%'",
        (now, _SET_ID),
    )
    # Soft-delete diagrams in the Scenia set
    await db.execute(
        "UPDATE diagrams SET is_deleted = TRUE, updated_at = ? WHERE set_id = ?",
        (now, _SET_ID),
    )
    # Clean up lookup tables
    await db.execute("DELETE FROM scenia_asset_categories WHERE set_id = ?", (_SET_ID,))
    await db.execute("DELETE FROM scenia_application_statuses WHERE set_id = ?", (_SET_ID,))
    await db.execute("DELETE FROM scenia_timeline_settings WHERE set_id = ?", (_SET_ID,))

    # Soft-delete the set (hard-delete would violate FK constraints from elements/diagrams)
    await db.execute(
        "UPDATE sets SET is_deleted = TRUE, updated_at = ? WHERE id = ?",
        (now, _SET_ID),
    )
    await db.commit()
