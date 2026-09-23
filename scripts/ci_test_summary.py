#!/usr/bin/env python3
"""Render a markdown table summarizing pytest JUnit XML results."""

from __future__ import annotations

import argparse
import subprocess
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


def _collect_test_ids(root: Path | None = None) -> set[str]:
    result = subprocess.run(
        ["pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    return {line.strip() for line in result.stdout.splitlines() if "::" in line}


def _test_diff_stats(main_worktree: Path) -> tuple[int, int]:
    pr_ids = _collect_test_ids()
    main_ids = _collect_test_ids(main_worktree)
    added = len(pr_ids - main_ids)
    deleted = len(main_ids - pr_ids)
    return added, deleted


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("junit_xml", nargs="+", type=Path, help="JUnit XML result files")
    parser.add_argument(
        "--main-worktree",
        type=Path,
        default=None,
        help="Path to a git worktree checkout of origin/main for test inventory diff",
    )
    args = parser.parse_args(argv[1:])

    rows = [_suite_stats(path) for path in args.junit_xml]
    print("## CI test summary")
    print()
    print("| Suite | Tests run | Passed | Failed | Skipped |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for name, tests, passed, failed, skipped in rows:
        print(f"| {name} | {tests} | {passed} | {failed} | {skipped} |")

    if args.main_worktree is not None:
        added, deleted = _test_diff_stats(args.main_worktree.resolve())
        print()
        print(f"{added} tests added, {deleted} tests deleted")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
