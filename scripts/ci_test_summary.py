#!/usr/bin/env python3
"""Render a markdown table summarizing pytest JUnit XML results."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _suite_stats(path: Path) -> tuple[str, int, int, int, int]:
    if not path.exists():
        return (path.stem, 0, 0, 0, 0)

    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    tests = failures = errors = skipped = 0
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0))
        errors += int(suite.attrib.get("errors", 0))
        skipped += int(suite.attrib.get("skipped", 0))

    passed = tests - failures - errors - skipped
    return (path.stem, tests, passed, failures + errors, skipped)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: ci_test_summary.py <junit.xml> [...]", file=sys.stderr)
        return 1

    rows = [_suite_stats(Path(arg)) for arg in argv[1:]]
    print("## CI test summary")
    print()
    print("| Suite | Tests run | Passed | Failed | Skipped |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for name, tests, passed, failed, skipped in rows:
        print(f"| {name} | {tests} | {passed} | {failed} | {skipped} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
