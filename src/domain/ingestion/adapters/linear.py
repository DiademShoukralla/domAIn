import httpx

from domain.ingestion.adapters.types import FetchedDocument


async def fetch_linear_team_documents(access_token: str, team_id: str) -> list[FetchedDocument]:
    query = """
    query TeamIssues($teamId: String!, $after: String) {
      team(id: $teamId) {
        issues(first: 100, after: $after) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            identifier
            title
            description
            state { name }
            priority
            url
          }
        }
      }
    }
    """
    documents: list[FetchedDocument] = []
    after: str | None = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            response = await client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"query": query, "variables": {"teamId": team_id, "after": after}},
            )
            response.raise_for_status()
            payload = response.json()
            team = payload["data"]["team"]
            if team is None:
                break

            issues = team["issues"]["nodes"]
            for issue in issues:
                description = issue.get("description") or ""
                content = (
                    f"# {issue['identifier']}: {issue['title']}\n\n"
                    f"State: {issue['state']['name']}\n"
                    f"Priority: {issue.get('priority')}\n"
                    f"URL: {issue.get('url')}\n\n"
                    f"{description}"
                )
                documents.append(FetchedDocument(document_id=issue["id"], content=content))

            page_info = team["issues"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            after = page_info["endCursor"]

    return documents
