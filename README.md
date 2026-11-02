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

## Reproducing the paper results

Every table, figure and number in the paper is produced from this repository.

```bash
python -m pip install -e ".[dev,frontends]"   # frontends extra: LangGraph, LangChain, matplotlib
python -m experiments.revision.run_all        # rebuild corpora, run E1-E6, regenerate figures + LaTeX macros
```

| Path | Content |
| --- | --- |
| `agentlint/ir/findings.py` | resource-keyed, effect-local, authority-confirmed analysis (bitset propagation, cycles) |
| `agentlint/frontends/langgraph.py` | static LangGraph (`StateGraph` AST) and LangChain trace frontends |
| `agentlint/dynamic/simulator.py` | dynamic schedule checker (random and systematic), no shared analysis code |
| `agentlint/evaluation/baselines.py` | independently implemented baselines B1, B2, B3, B3A (+ B4 = AgentLint) |
| `agentlint/benchmark/bindbench.py` | declarative BindBench v2 specification and generator (40 families) |
| `agentlint/benchmark/tool_catalog.py` | 46 real tool APIs with hand-written contracts |
| `agentlint/benchmark/benign.py` | seeded benign / injected-risk workflow generator over the tool catalog |
| `agentlint/contracts/infer.py` | schema-only draft-contract inference (contract-effort study) |
| `examples/langgraph/` | executable LangGraph `StateGraph` pipelines and ReAct agents |
| `experiments/revision/` | E1-E6 and `make_paper_assets.py` (results in `results/revision/`) |
| `paper/procedia/` | generated figures and LaTeX macros (`figures/`, `generated/`) written by `run_all` |

`experiments/e1_detection` ... `experiments/e6_scalability` are the superseded pilot scaffolding
from an earlier pilot and are kept only for history; `experiments/revision/` is authoritative.

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
