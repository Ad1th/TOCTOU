# AgentLint

AgentLint is a reproducible engineering framework for evaluating check–effect binding risks in supported LLM-agent tool workflows.

This repository currently contains **M0 — Foundation** only. It provides project conventions, quality tooling, CI, a structured logging utility, and a deterministic experiment template. It does not yet implement contracts, workflow parsing, analysis, validation, or benchmark cases.

## Requirements

- Python 3.12 or newer

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
black --check .
mypy .
pytest
```

## Experiment Template

Run the template from the repository root:

```bash
python -m experiments.template.runner
```

The command deterministically regenerates `experiments/template/results.csv` with only its declared CSV header. See `experiments/template/README.md` and `docs/REPRODUCIBILITY.md`.

## Documentation

- `FINAL_PROJECT_SPEC.md` is the frozen project contract.
- `docs/README.md` indexes engineering documentation.
- `docs/design/m0-foundation.md` records the M0 design and acceptance criteria.
