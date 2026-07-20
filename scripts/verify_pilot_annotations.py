"""Verify M1 pilot annotation agreement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentlint.annotations import cohen_kappa, load_annotation_set


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=Path("benchmark/pilot/annotations"),
        help="Directory containing annotator_a.json and annotator_b.json.",
    )
    parser.add_argument("--minimum-kappa", type=float, default=0.70)
    return parser


def main() -> int:
    """Run the pilot agreement check."""

    args = build_parser().parse_args()
    left = load_annotation_set(args.annotations_dir / "annotator_a.json")
    right = load_annotation_set(args.annotations_dir / "annotator_b.json")
    kappa = cohen_kappa(left, right)
    result = {
        "annotators": [left.annotator_id, right.annotator_id],
        "records_per_annotator": len(left.records),
        "cohen_kappa": round(kappa, 6),
        "minimum_kappa": args.minimum_kappa,
        "passed": kappa >= args.minimum_kappa,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
