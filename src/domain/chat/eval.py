import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from domain.chat.classifier import classify_intent
from domain.schemas.chat import ChatIntent

ClassifierFn = Callable[[str], Awaitable[ChatIntent]]

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "data" / "router_eval_dataset.json"


@dataclass(frozen=True)
class RouterEvalExample:
    message: str
    expected_intent: ChatIntent


@dataclass(frozen=True)
class RouterEvalResult:
    total: int
    correct: int
    accuracy: float
    mismatches: list[tuple[str, ChatIntent, ChatIntent]]


def load_router_eval_dataset(path: Path | None = None) -> list[RouterEvalExample]:
    dataset_path = path or DEFAULT_DATASET_PATH
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [
        RouterEvalExample(
            message=item["message"],
            expected_intent=ChatIntent(item["expected_intent"]),
        )
        for item in raw
    ]


async def score_router_dataset(
    examples: list[RouterEvalExample],
    classifier: ClassifierFn | None = None,
) -> RouterEvalResult:
    classify: ClassifierFn = classifier or classify_intent
    mismatches: list[tuple[str, ChatIntent, ChatIntent]] = []
    correct = 0

    for example in examples:
        predicted = await classify(example.message)
        if predicted == example.expected_intent:
            correct += 1
        else:
            mismatches.append((example.message, example.expected_intent, predicted))

    total = len(examples)
    accuracy = correct / total if total else 0.0
    return RouterEvalResult(
        total=total,
        correct=correct,
        accuracy=accuracy,
        mismatches=mismatches,
    )
