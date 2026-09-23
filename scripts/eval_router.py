#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from domain.chat.eval import load_router_eval_dataset, score_router_dataset


async def main() -> int:
    examples = load_router_eval_dataset()
    result = await score_router_dataset(examples)
    print(f"Router eval: {result.correct}/{result.total} correct ({result.accuracy:.1%})")
    if result.mismatches:
        print("Mismatches:")
        for message, expected, predicted in result.mismatches[:20]:
            print(f"- expected={expected.value} predicted={predicted.value}: {message}")
    return 0 if result.accuracy >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
