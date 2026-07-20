# Reproducibility Conventions

Every experiment must contain `config.yaml`, `README.md`, `runner.py`, generated `results.csv`, and `plots/`.

Experiment runners must record their seed, command, package/environment revision, input revision, timeout, and machine metadata in generated results or adjacent manifests. Generated figures and tables must derive from versioned raw results; they must not be edited by hand.

Validation adapters must run locally with deterministic mutation schedules. A failed bounded validation is reported as `not_triggered_within_budget` or `inconclusive`, never as proof of safety.
