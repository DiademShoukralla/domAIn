import httpx

from domain.ingestion.adapters.types import FetchedDocument
from domain.oauth.github_app import get_installation_access_token

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".css",
    ".html",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".sh",
    ".ini",
    ".cfg",
    ".env.example",
}


async def fetch_github_repo_documents(
    installation_id: str, repo_full_name: str
) -> list[FetchedDocument]:
    access_token = await get_installation_access_token(installation_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    documents: list[FetchedDocument] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        tree_url = f"https://api.github.com/repos/{repo_full_name}/git/trees/main?recursive=1"
        response = await client.get(tree_url, headers=headers)
        if response.status_code == 404:
            tree_url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
            response = await client.get(tree_url, headers=headers)
        response.raise_for_status()
        tree = response.json()

        for item in tree.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item["path"]
            if not any(path.endswith(ext) for ext in TEXT_EXTENSIONS):
                continue
            if path.startswith(".git/") or "/node_modules/" in path or "/.venv/" in path:
                continue

            blob_sha = item["sha"]
            blob_response = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/git/blobs/{blob_sha}",
                headers=headers,
            )
            if blob_response.status_code != 200:
                continue
            blob = blob_response.json()
            if blob.get("encoding") != "base64":
                continue
            import base64

            content = base64.b64decode(blob["content"]).decode("utf-8", errors="ignore")
            if not content.strip():
                continue
            documents.append(FetchedDocument(document_id=path, content=content))

    return documents
