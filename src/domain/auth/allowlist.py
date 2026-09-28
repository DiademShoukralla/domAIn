from domain.config import get_settings


def is_github_id_allowed(github_id: int) -> bool:
    return github_id in get_settings().allowed_github_ids
