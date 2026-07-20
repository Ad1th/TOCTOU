# Experiment Template

This template is the required starting point for every AgentLint experiment.

## Files

- `config.yaml`: human-readable experiment configuration.
- `runner.py`: deterministic result-artifact generator.
- `results.csv`: generated raw-results placeholder.
- `plots/`: generated plots for this experiment.

## Run

From the repository root, run:

```bash
python -m experiments.template.runner
```

The runner overwrites `results.csv` with the stable header:

```text
experiment_id,status,seed,notes
```

Future experiments must preserve this layout and document their inputs, seeds, commands, expected runtime, and generated outputs.
