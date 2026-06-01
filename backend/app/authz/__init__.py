"""Authorization helpers (ADR-237): per-user collection write-scope.

A user with no rows in ``user_collection_scope`` is *unscoped* — their role's
write permissions apply everywhere (the pre-ADR-237 behaviour). A *scoped* user
may write only inside their whitelisted collections, may never create or delete
collections, and may not mutate global element templates. Admins always bypass.
Reads are unaffected (ADR-123).
"""

from app.authz.collection_resolver import (
    collection_of_diagram,
    collection_of_element,
    collection_of_entity,
    collection_of_package,
    collection_of_set,
    collection_of_template,
)
from app.authz.collection_scope import load_scope
from app.authz.enforce import assert_unscoped_or_admin, assert_write_allowed

__all__ = [
    "assert_unscoped_or_admin",
    "assert_write_allowed",
    "collection_of_diagram",
    "collection_of_element",
    "collection_of_entity",
    "collection_of_package",
    "collection_of_set",
    "collection_of_template",
    "load_scope",
]
