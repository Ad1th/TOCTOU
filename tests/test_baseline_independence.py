"""Baselines B1-B3A must not depend on the analysis under test."""

from __future__ import annotations

import ast
from pathlib import Path

from agentlint.evaluation import baselines

FORBIDDEN = ("agentlint.ir.findings", "agentlint.ir.dependencies", "agentlint.ir")


def test_baselines_module_does_not_import_the_analysis_at_module_level() -> None:
    tree = ast.parse(Path(baselines.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module not in FORBIDDEN[:2], node.module
            if node.module == "agentlint.ir":
                raise AssertionError("baselines must import IR data types from agentlint.ir.models")


def test_only_b4_reaches_generate_findings() -> None:
    source = Path(baselines.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        if "generate_findings" in names:
            assert fn.name == "run_baseline"
