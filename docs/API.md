# AgentLint API Surface

## M1 Contracts

- `agentlint.contracts.validate_contract(document)`: validates a contract mapping and returns `ToolContract`.
- `agentlint.contracts.load_contract(path)`: loads a JSON contract file and returns `ToolContract`.

## M1 BindBench Manifests

- `agentlint.benchmark.validate_manifest(document)`: validates a family manifest mapping and returns `ScenarioFamily`.
- `agentlint.benchmark.load_manifest(path)`: loads a JSON manifest file and returns `ScenarioFamily`.

## M1 Annotation Agreement

- `agentlint.annotations.load_annotation_set(path)`: loads a pilot annotation JSON file.
- `agentlint.annotations.cohen_kappa(left, right)`: computes Cohen's kappa over paired annotation labels.
