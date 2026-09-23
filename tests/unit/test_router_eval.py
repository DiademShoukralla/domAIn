import json
from pathlib import Path

import pytest

from domain.chat.eval import load_router_eval_dataset, score_router_dataset
from domain.schemas.chat import ChatIntent


def test_router_eval_dataset_has_required_size() -> None:
    examples = load_router_eval_dataset()
    assert 50 <= len(examples) <= 100


def test_router_eval_dataset_covers_all_intents() -> None:
    examples = load_router_eval_dataset()
    intents = {example.expected_intent for example in examples}
    assert intents == {
        ChatIntent.GREETING,
        ChatIntent.SIMPLE_RETRIEVAL,
        ChatIntent.STRATEGIC_SESSION,
        ChatIntent.LINEAR_READ,
        ChatIntent.LINEAR_WRITE,
    }


def test_router_eval_dataset_json_is_valid() -> None:
    dataset_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "domain"
        / "chat"
        / "data"
        / "router_eval_dataset.json"
    )
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    for item in payload:
        assert "message" in item
        assert "expected_intent" in item
        ChatIntent(item["expected_intent"])


@pytest.mark.asyncio
async def test_score_router_dataset_with_mock_classifier() -> None:
    mapping = {
        "hello": ChatIntent.GREETING,
        "what is rrf": ChatIntent.SIMPLE_RETRIEVAL,
        "review this proposal": ChatIntent.STRATEGIC_SESSION,
        "show linear issue 1": ChatIntent.LINEAR_READ,
        "update linear issue 1": ChatIntent.LINEAR_WRITE,
    }

    async def mock_classifier(message: str) -> ChatIntent:
        lowered = message.lower()
        for key, intent in mapping.items():
            if key in lowered:
                return intent
        return ChatIntent.GREETING

    examples = load_router_eval_dataset()[:10]

    async def mapped_classifier(message: str) -> ChatIntent:
        for example in examples:
            if example.message == message:
                return example.expected_intent
        return ChatIntent.GREETING

    result = await score_router_dataset(examples, classifier=mapped_classifier)
    assert result.total == 10
    assert result.correct == 10
    assert result.accuracy == 1.0
