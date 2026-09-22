from uuid import UUID


def can_access(
    actor_user_id: UUID,
    actor_project_id: UUID | None,
    resource_user_id: UUID | None,
    resource_project_id: UUID | None,
) -> bool:
    """Single shared authorization check for all resource reads."""
    if resource_user_id is None and resource_project_id is None:
        return True
    if resource_user_id is not None and resource_user_id != actor_user_id:
        return False
    if resource_project_id is not None and resource_project_id != actor_project_id:
        return False
    return True
