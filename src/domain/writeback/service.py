import base64
import re
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.models import (
    ChatMessage,
    Connection,
    KnowledgeSource,
    Provider,
    SourceType,
    WriteBackProposal,
)
from domain.oauth.github_app import GITHUB_API_BASE, get_installation_access_token
from domain.oauth.linear import get_linear_access_token
from domain.permissions import can_access
from domain.schemas.chat import ChatRole, ResponseKind
from domain.schemas.common import ActorContext, CouncilDecision
from domain.schemas.writeback import (
    WriteBackFeedbackEntry,
    WriteBackPlan,
    WriteBackProposalOut,
    WriteBackProposalStatus,
)
from domain.writeback.planner import classify_write_back_plan

LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_ACTOR_NAME = "domAIn"
NEW_DOC_BASE_PATH = "docs/business/council-decisions"


def _parse_council_decision(record: ChatMessage) -> CouncilDecision:
    if record.council_decision is None:
        raise HTTPException(status_code=400, detail="Council message has no council decision")
    return CouncilDecision.model_validate(record.council_decision)


def _feedback_strings(proposal: WriteBackProposal) -> list[str]:
    return [str(entry["feedback"]) for entry in proposal.feedback_history]


def _to_proposal_out(proposal: WriteBackProposal) -> WriteBackProposalOut:
    feedback_history = [
        WriteBackFeedbackEntry.model_validate(entry) for entry in proposal.feedback_history
    ]
    return WriteBackProposalOut(
        id=proposal.id,
        chat_message_id=proposal.chat_message_id,
        user_id=proposal.user_id,
        project_id=proposal.project_id,
        plan=WriteBackPlan.model_validate(proposal.plan),
        feedback_history=feedback_history,
        status=WriteBackProposalStatus(proposal.status),
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        executed_at=proposal.executed_at,
    )


async def _get_council_message(
    db: AsyncSession,
    message_id: UUID,
    actor: ActorContext,
) -> ChatMessage:
    message = await db.get(ChatMessage, message_id)
    if message is None or not can_access(
        actor.user_id, actor.project_id, message.user_id, message.project_id
    ):
        raise HTTPException(status_code=404, detail="Chat message not found")
    if message.response_kind != ResponseKind.COUNCIL_RESULT.value:
        raise HTTPException(status_code=400, detail="Message is not a council result")
    return message


async def _get_original_query(db: AsyncSession, council_message: ChatMessage) -> str:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == council_message.session_id,
            ChatMessage.role == ChatRole.USER.value,
            ChatMessage.created_at < council_message.created_at,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    user_message = result.scalar_one_or_none()
    if user_message is None:
        return council_message.content
    return user_message.content


async def _list_accessible_sources(
    db: AsyncSession,
    actor: ActorContext,
    source_type: SourceType,
) -> list[KnowledgeSource]:
    result = await db.execute(
        select(KnowledgeSource)
        .join(Connection, KnowledgeSource.connection_id == Connection.id)
        .where(KnowledgeSource.source_type == source_type)
    )
    return [
        source
        for source in result.scalars().all()
        if can_access(actor.user_id, actor.project_id, source.user_id, source.project_id)
    ]


async def _resolve_github_repo_source(
    db: AsyncSession,
    actor: ActorContext,
) -> tuple[KnowledgeSource, Connection]:
    sources = await _list_accessible_sources(db, actor, SourceType.GITHUB_REPO)
    if len(sources) == 0:
        raise HTTPException(
            status_code=400, detail="No GitHub repository knowledge source configured"
        )
    if len(sources) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple GitHub repository knowledge sources configured; v1 expects exactly one",
        )
    source = sources[0]
    connection = await db.get(Connection, source.connection_id)
    if connection is None or connection.provider != Provider.GITHUB:
        raise HTTPException(
            status_code=400, detail="GitHub connection not found for repository source"
        )
    if not connection.installation_id:
        raise HTTPException(status_code=400, detail="GitHub connection is missing installation_id")
    return source, connection


async def _resolve_linear_team_source(
    db: AsyncSession,
    actor: ActorContext,
) -> tuple[KnowledgeSource, Connection]:
    sources = await _list_accessible_sources(db, actor, SourceType.LINEAR)
    if len(sources) == 0:
        raise HTTPException(status_code=400, detail="No Linear knowledge source configured")
    if len(sources) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple Linear knowledge sources configured; v1 expects exactly one",
        )
    source = sources[0]
    connection = await db.get(Connection, source.connection_id)
    if connection is None or connection.provider != Provider.LINEAR:
        raise HTTPException(status_code=400, detail="Linear connection not found for team source")
    return source, connection


def _format_date(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()


def _build_new_doc_content(
    *,
    slug: str,
    query: str,
    council_decision: CouncilDecision,
    executed_at: datetime,
) -> str:
    date_str = _format_date(executed_at)
    lines = [
        f"# Council decision: {slug}",
        "",
        f"Date: {date_str}",
        "",
        "## Original query",
        "",
        query,
        "",
        "## Overall verdict",
        "",
        council_decision.overall_verdict.value,
        "",
        "## Persona opinions",
        "",
    ]
    for opinion in council_decision.persona_opinions:
        lines.extend(
            [
                f"### {opinion.persona} ({opinion.verdict.value})",
                "",
                opinion.reasoning,
                "",
            ]
        )
    lines.extend(
        [
            "## Synthesis",
            "",
            council_decision.synthesis,
            "",
        ]
    )
    return "\n".join(lines)


def _build_existing_doc_append(
    existing_content: str,
    *,
    query: str,
    council_decision: CouncilDecision,
    executed_at: datetime,
) -> str:
    date_str = _format_date(executed_at)
    section_title = f"Council write-back ({date_str})"
    body_lines = [
        f"Original query: {query}",
        "",
        f"Overall verdict: {council_decision.overall_verdict.value}",
        "",
        "Synthesis:",
        "",
        council_decision.synthesis,
        "",
    ]
    for opinion in council_decision.persona_opinions:
        body_lines.extend(
            [
                f"- **{opinion.persona}** ({opinion.verdict.value}): {opinion.reasoning}",
            ]
        )
    body = "\n".join(body_lines)
    changelog_entry = (
        f'Council write-back for query "{query}" '
        f"(verdict: {council_decision.overall_verdict.value})"
    )

    new_section = f"## {section_title}\n\nDate: {date_str}\n\n{body}\n"
    changelog_marker = "## Changelog"
    if changelog_marker in existing_content:
        before, changelog_block = existing_content.rsplit(changelog_marker, 1)
        updated = (
            before.rstrip()
            + "\n\n"
            + new_section
            + "\n"
            + changelog_marker
            + changelog_block.rstrip()
        )
        if not updated.endswith("\n"):
            updated += "\n"
        return _append_changelog_row(updated, date_str, changelog_entry)

    updated = existing_content.rstrip() + "\n\n" + new_section
    updated += (
        f"\n{changelog_marker}\n\n"
        "| Date | Change |\n"
        "|------|--------|\n"
        f"| {date_str} | {changelog_entry} |\n"
    )
    return updated


def _append_changelog_row(content: str, date_str: str, changelog_entry: str) -> str:
    lines = content.splitlines()
    table_row = f"| {date_str} | {changelog_entry} |"
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].startswith("|") and "|" in lines[index][1:]:
            lines.insert(index + 1, table_row)
            return "\n".join(lines) + "\n"
    lines.append(table_row)
    return "\n".join(lines) + "\n"


def _new_doc_path(slug: str, executed_at: datetime) -> str:
    date_str = _format_date(executed_at)
    safe_slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return f"{NEW_DOC_BASE_PATH}/{date_str}-{safe_slug}.md"


def _linear_display_icon_url() -> str:
    settings = get_settings()
    return f"{settings.app_base_url.rstrip('/')}/static/icon.png"


def _linear_issue_title(query: str) -> str:
    normalized = " ".join(query.split())
    if len(normalized) <= 80:
        return f"Council: {normalized}"
    return f"Council: {normalized[:77]}..."


def _linear_issue_description(
    query: str,
    council_decision: CouncilDecision,
    executed_at: datetime,
) -> str:
    date_str = _format_date(executed_at)
    lines = [
        f"**Date:** {date_str}",
        "",
        "## Original query",
        "",
        query,
        "",
        f"**Overall verdict:** {council_decision.overall_verdict.value}",
        "",
        "## Synthesis",
        "",
        council_decision.synthesis,
        "",
        "## Persona opinions",
        "",
    ]
    for opinion in council_decision.persona_opinions:
        lines.extend(
            [
                f"### {opinion.persona} ({opinion.verdict.value})",
                "",
                opinion.reasoning,
                "",
            ]
        )
    return "\n".join(lines)


async def _github_request(
    method: str,
    path: str,
    *,
    token: str,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.request(
            method,
            f"{GITHUB_API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json=json,
        )
        return response


async def _get_default_branch(token: str, repo_full_name: str) -> str:
    response = await _github_request("GET", f"/repos/{repo_full_name}", token=token)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to resolve GitHub repository default branch: {response.text}",
        )
    payload = response.json()
    return str(payload["default_branch"])


async def _get_file_content(token: str, repo_full_name: str, path: str) -> tuple[str, str | None]:
    response = await _github_request(
        "GET",
        f"/repos/{repo_full_name}/contents/{path}",
        token=token,
    )
    if response.status_code == 404:
        raise HTTPException(
            status_code=400, detail=f"Existing doc path not found in repository: {path}"
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch existing doc from GitHub: {response.text}",
        )
    payload = response.json()
    if payload.get("encoding") != "base64":
        raise HTTPException(status_code=502, detail="Unexpected GitHub file encoding")
    content = base64.b64decode(str(payload["content"])).decode("utf-8")
    return content, str(payload["sha"])


async def _create_branch(
    token: str,
    repo_full_name: str,
    branch_name: str,
    base_branch: str,
) -> None:
    base_ref = await _github_request(
        "GET",
        f"/repos/{repo_full_name}/git/ref/heads/{base_branch}",
        token=token,
    )
    if base_ref.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to resolve base branch ref: {base_ref.text}",
        )
    base_sha = base_ref.json()["object"]["sha"]
    create_ref = await _github_request(
        "POST",
        f"/repos/{repo_full_name}/git/refs",
        token=token,
        json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
    )
    if create_ref.status_code not in {201, 422}:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create GitHub branch: {create_ref.text}",
        )


async def _commit_file(
    token: str,
    repo_full_name: str,
    path: str,
    content: str,
    message: str,
    branch_name: str,
    file_sha: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch_name,
    }
    if file_sha is not None:
        payload["sha"] = file_sha
    response = await _github_request(
        "PUT",
        f"/repos/{repo_full_name}/contents/{path}",
        token=token,
        json=payload,
    )
    if response.status_code not in {200, 201}:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to commit file to GitHub: {response.text}",
        )


async def _open_pull_request(
    token: str,
    repo_full_name: str,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
) -> str:
    response = await _github_request(
        "POST",
        f"/repos/{repo_full_name}/pulls",
        token=token,
        json={
            "title": title,
            "head": branch_name,
            "base": base_branch,
            "body": body,
        },
    )
    if response.status_code != 201:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to open GitHub pull request: {response.text}",
        )
    return str(response.json()["html_url"])


async def _execute_github_doc_write(
    *,
    installation_id: str,
    repo_full_name: str,
    plan: WriteBackPlan,
    query: str,
    council_decision: CouncilDecision,
    executed_at: datetime,
    proposal_id: UUID,
) -> str:
    token = await get_installation_access_token(installation_id)
    base_branch = await _get_default_branch(token, repo_full_name)
    date_str = _format_date(executed_at)
    branch_name = f"domain/write-back-{str(proposal_id)[:8]}-{date_str}"

    if plan.doc_target == "existing":
        if not plan.existing_doc_path:
            raise HTTPException(status_code=400, detail="Plan is missing existing_doc_path")
        existing_content, file_sha = await _get_file_content(
            token, repo_full_name, plan.existing_doc_path
        )
        updated_content = _build_existing_doc_append(
            existing_content,
            query=query,
            council_decision=council_decision,
            executed_at=executed_at,
        )
        path = plan.existing_doc_path
        commit_message = f"docs: council write-back to {path}"
        pr_title = f"Council write-back: update {path}"
    elif plan.doc_target == "new":
        if not plan.new_doc_slug:
            raise HTTPException(status_code=400, detail="Plan is missing new_doc_slug")
        path = _new_doc_path(plan.new_doc_slug, executed_at)
        updated_content = _build_new_doc_content(
            slug=plan.new_doc_slug,
            query=query,
            council_decision=council_decision,
            executed_at=executed_at,
        )
        file_sha = None
        commit_message = f"docs: add council decision {path}"
        pr_title = f"Council write-back: add {path}"
    else:
        raise HTTPException(
            status_code=400, detail="Plan has invalid doc_target for GitHub write-back"
        )

    await _create_branch(token, repo_full_name, branch_name, base_branch)
    await _commit_file(
        token,
        repo_full_name,
        path,
        updated_content,
        commit_message,
        branch_name,
        file_sha=file_sha,
    )
    return await _open_pull_request(
        token,
        repo_full_name,
        branch_name,
        base_branch,
        pr_title,
        f"Automated council write-back for proposal `{proposal_id}`.\n\nOriginal query: {query}",
    )


async def _linear_graphql(
    access_token: str,
    query: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            LINEAR_API_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"query": query, "variables": variables},
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Linear API request failed: {response.text}",
        )
    payload = response.json()
    if payload.get("errors"):
        raise HTTPException(
            status_code=502,
            detail=f"Linear GraphQL error: {payload['errors']}",
        )
    return cast(dict[str, Any], payload["data"])


async def _find_linear_issue_by_title(
    access_token: str,
    team_id: str,
    title: str,
) -> str | None:
    query = """
    query FindIssue($teamId: String!, $title: String!) {
      team(id: $teamId) {
        issues(filter: { title: { eq: $title } }, first: 1) {
          nodes { id }
        }
      }
    }
    """
    data = await _linear_graphql(access_token, query, {"teamId": team_id, "title": title})
    team = data.get("team")
    if team is None:
        return None
    nodes = team["issues"]["nodes"]
    if not nodes:
        return None
    return str(nodes[0]["id"])


async def _execute_linear_roadmap_write(
    *,
    db: AsyncSession,
    connection: Connection,
    team_id: str,
    query: str,
    council_decision: CouncilDecision,
    executed_at: datetime,
) -> str:
    access_token = await get_linear_access_token(db, connection)
    title = _linear_issue_title(query)
    description = _linear_issue_description(query, council_decision, executed_at)
    actor_input = {
        "createAsUser": LINEAR_ACTOR_NAME,
        "displayIconUrl": _linear_display_icon_url(),
    }

    issue_input: dict[str, Any] = {
        "title": title,
        "description": description,
        **actor_input,
    }
    existing_issue_id = await _find_linear_issue_by_title(access_token, team_id, title)
    if existing_issue_id is None:
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { url }
          }
        }
        """
        variables: dict[str, Any] = {
            "input": {
                "teamId": team_id,
                **issue_input,
            }
        }
        data = await _linear_graphql(access_token, mutation, variables)
        result = data["issueCreate"]
    else:
        mutation = """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue { url }
          }
        }
        """
        variables = {
            "id": existing_issue_id,
            "input": issue_input,
        }
        data = await _linear_graphql(access_token, mutation, variables)
        result = data["issueUpdate"]

    if not result.get("success"):
        raise HTTPException(status_code=502, detail="Linear issue write-back failed")
    return str(result["issue"]["url"])


async def create_write_back_proposal(
    db: AsyncSession,
    message_id: UUID,
    actor: ActorContext,
) -> WriteBackProposalOut:
    message = await _get_council_message(db, message_id, actor)
    council_decision = _parse_council_decision(message)

    existing = await db.execute(
        select(WriteBackProposal).where(WriteBackProposal.chat_message_id == message_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Write-back proposal already exists")

    plan = await classify_write_back_plan(council_decision)
    proposal = WriteBackProposal(
        chat_message_id=message_id,
        user_id=actor.user_id,
        project_id=message.project_id,
        plan=plan.model_dump(mode="json"),
        feedback_history=[],
        status=WriteBackProposalStatus.PROPOSED.value,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return _to_proposal_out(proposal)


async def refine_write_back_proposal(
    db: AsyncSession,
    proposal_id: UUID,
    feedback: str,
    actor: ActorContext,
) -> WriteBackProposalOut:
    proposal = await db.get(WriteBackProposal, proposal_id)
    if proposal is None or not can_access(
        actor.user_id, actor.project_id, proposal.user_id, proposal.project_id
    ):
        raise HTTPException(status_code=404, detail="Write-back proposal not found")
    if proposal.status != WriteBackProposalStatus.PROPOSED.value:
        raise HTTPException(status_code=400, detail="Proposal is not open for refinement")

    message = await db.get(ChatMessage, proposal.chat_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Chat message not found")
    council_decision = _parse_council_decision(message)

    feedback_history = _feedback_strings(proposal)
    feedback_history.append(feedback)
    plan = await classify_write_back_plan(council_decision, feedback_history=feedback_history)

    history_entry = WriteBackFeedbackEntry(
        feedback=feedback,
        created_at=datetime.now(UTC),
    )
    updated_history = [*proposal.feedback_history, history_entry.model_dump(mode="json")]
    proposal.plan = plan.model_dump(mode="json")
    proposal.feedback_history = updated_history
    await db.commit()
    await db.refresh(proposal)
    return _to_proposal_out(proposal)


async def confirm_write_back_proposal(
    db: AsyncSession,
    proposal_id: UUID,
    actor: ActorContext,
) -> WriteBackProposalOut:
    proposal = await db.get(WriteBackProposal, proposal_id)
    if proposal is None or not can_access(
        actor.user_id, actor.project_id, proposal.user_id, proposal.project_id
    ):
        raise HTTPException(status_code=404, detail="Write-back proposal not found")
    if proposal.status != WriteBackProposalStatus.PROPOSED.value:
        raise HTTPException(status_code=400, detail="Proposal is not open for confirmation")

    plan = WriteBackPlan.model_validate(proposal.plan)
    message = await db.get(ChatMessage, proposal.chat_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Chat message not found")
    council_decision = _parse_council_decision(message)
    query = await _get_original_query(db, message)
    executed_at = datetime.now(UTC)

    if plan.needs_doc_update:
        github_source, github_connection = await _resolve_github_repo_source(db, actor)
        await _execute_github_doc_write(
            installation_id=github_connection.installation_id or "",
            repo_full_name=github_source.external_ref,
            plan=plan,
            query=query,
            council_decision=council_decision,
            executed_at=executed_at,
            proposal_id=proposal.id,
        )

    if plan.needs_roadmap_item:
        linear_source, linear_connection = await _resolve_linear_team_source(db, actor)
        await _execute_linear_roadmap_write(
            db=db,
            connection=linear_connection,
            team_id=linear_source.external_ref,
            query=query,
            council_decision=council_decision,
            executed_at=executed_at,
        )

    proposal.status = WriteBackProposalStatus.EXECUTED.value
    proposal.executed_at = executed_at
    await db.commit()
    await db.refresh(proposal)
    return _to_proposal_out(proposal)
