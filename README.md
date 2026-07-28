# AgentLint

AgentLint is a reproducible engineering framework for evaluating check–effect binding risks in supported LLM-agent tool workflows.

This repository contains the current prototype implementation: tool contracts, pilot benchmark schemas and annotations, workflow IR, dependency propagation, finding generation, and an evaluation runner over local JSON workflow fixtures.

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

## Evaluation

Run the local pilot evaluation from the repository root:

```bash
python -m scripts.run_evaluation
```

The command analyzes every workflow fixture in `examples/workflows/` using the existing IR, dependency propagation, and finding generator. It compares analyzer output against `benchmark/pilot/annotations/annotator_a.json`.

Expected outputs:

- `results/findings/*.json`: per-workflow structured findings.
- `results/metrics/summary.json`: TP, FP, FN, precision, recall, F1, workflow count, finding count, and runtime.
- `results/metrics/summary.csv`: metric summary in CSV form.
- `results/tables/summary.csv`: publication-ready workflow summary table.
- `results/figures/README.md`: placeholder for future generated figures.
- `results/logs/experiment.log`: deterministic evaluation log structure.

Reproduction steps:

```bash
python -m pip install -e ".[dev]"
python -m scripts.run_evaluation
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
