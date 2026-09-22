# 4. Permissions model

Date: 2026-09-22

## Status

Accepted

## Context

domAIn v1 is single-user / single-project, but the data model must not paint us into a corner. Knowledge sources and API keys need scoping (whose data is this? which project does it belong to?), and every read path must enforce access consistently. We evaluated a dedicated Permissions entity and simpler alternatives.

## Decision

### Nullable `user_id` and `project_id` on core entities

Both `APIKey` and `KnowledgeSource` carry nullable `user_id` and `project_id` columns directly — no separate Permissions table for v1.

```python
class APIKey(Base):
    id: UUID
    key_hash: str
    user_id: Optional[UUID]       # owner; null = system/service key
    project_id: Optional[UUID]     # scope; null = all projects for this user
    ...

class KnowledgeSource(Base):
    id: UUID
    name: str
    source_type: str              # e.g. "git_repo", "upload", "linear"
    user_id: Optional[UUID]       # owner; null = global/shared source
    project_id: Optional[UUID]     # scope; null = user-global (not tied to a project)
    ...
```

### Scoping semantics

| `user_id` | `project_id` | Meaning |
|-----------|-------------|---------|
| set | set | Owned by user, scoped to project |
| set | null | Owned by user, not tied to any project (user-global) |
| null | set | Shared/system source scoped to a project |
| null | null | Global/system source (e.g. built-in docs) |

This matrix already covers a future **user-owned, no-project** knowledge source (row 2) without schema changes. A user can attach personal reference material that follows them across projects.

### One shared `can_access()` function

All authorization checks go through a single function:

```python
def can_access(
    actor_user_id: UUID,
    actor_project_id: Optional[UUID],
    resource_user_id: Optional[UUID],
    resource_project_id: Optional[UUID],
) -> bool:
    # Global resources (null/null) are accessible to all authenticated users
    if resource_user_id is None and resource_project_id is None:
        return True
    # User must match when resource has an owner
    if resource_user_id is not None and resource_user_id != actor_user_id:
        return False
    # Project must match when resource is project-scoped
    if resource_project_id is not None and resource_project_id != actor_project_id:
        return False
    return True
```

Used by:

- Knowledge source list/get/delete endpoints
- Retrieval pipeline (filters chunks by accessible sources)
- API key validation (key's `user_id` / `project_id` become the actor context)

**Rationale:** Duplicated access logic across endpoints and the retrieval layer is the most common source of authorization bugs. One function, tested once, called everywhere.

### Why a dedicated Permissions entity was rejected

A `Permissions` table (resource × principal × action rows) is the standard RBAC/ABAC pattern. We rejected it for v1 because:

1. **Scale:** v1 is single-user / single-project. There is one user and one project. A permissions table with join queries is overhead with no benefit.
2. **Complexity:** RBAC introduces role definitions, role assignment, permission inheritance, and cache invalidation — all unneeded when the access rule is "does the `user_id` match and does the `project_id` match?"
3. **The nullable-column model already extends:** Adding a `user_id=null, project_id=null` global source, or a `user_id=set, project_id=null` user-global source, requires zero migration. The `can_access()` function handles new combinations by reading the same two columns.
4. **Migration path is clear:** If multi-tenant RBAC is needed later (teams, roles, shared projects), a Permissions table can be introduced and `can_access()` rewritten to query it. The nullable columns on `KnowledgeSource` and `APIKey` remain useful as ownership metadata even after RBAC lands.

## Consequences

- Authorization is enforced in one place; new endpoints cannot accidentally skip a check if they call `can_access()`.
- No permissions table means no migration, no join, no cache invalidation for v1.
- Nullable columns on two tables are easy to reason about and query.
- Future RBAC is a refactor of `can_access()`, not a schema rewrite — `user_id` / `project_id` on entities remain as ownership metadata.
- v1 does not support multi-user projects or role-based access; that is an explicit non-goal documented here.
