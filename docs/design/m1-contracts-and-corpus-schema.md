# M1 Design: Contracts and Corpus Schema

## Scope

M1 implements only the frozen contract and BindBench schema layer. It does not implement workflow parsing, static analysis, validation adapters, or experiment runners beyond the pilot annotation agreement check.

## Problem

AgentLint needs explicit tool semantics before any later analysis can decide whether a check and effect are bound by an authority-enforced mechanism. It also needs a stable corpus schema so benchmark families can be labeled consistently before analysis rules are tuned.

## Solution

M1 provides:

- typed Python APIs for tool-contract and BindBench-manifest validation;
- JSON Schema documents for contract and corpus artifacts;
- six pilot BindBench family manifests, one per frozen category;
- an annotation guide and paired pilot annotation files;
- a deterministic Cohen's-kappa verification script.

## Data Structures

- `ToolContract`: operation, resource argument, predicate, binding mechanisms, authority behavior, version argument, effect category, and oracle reference.
- `ScenarioFamily`: family metadata and exactly three `ScenarioVariant` entries.
- `AnnotationSet`: one annotator's records keyed by `(family_id, variant)`.

## Interfaces

- `agentlint.contracts.validate_contract(document)`
- `agentlint.contracts.load_contract(path)`
- `agentlint.benchmark.validate_manifest(document)`
- `agentlint.benchmark.load_manifest(path)`
- `agentlint.annotations.load_annotation_set(path)`
- `agentlint.annotations.cohen_kappa(left, right)`
- `python -m scripts.verify_pilot_annotations`

## Assumptions

Contract and manifest files are versioned with `schema_version = 1`. M1 stores pilot artifacts as JSON documents; the JSON Schema definitions are applicable to equivalent YAML documents in later corpus authoring.

## Complexity

Validation is linear in the number of fields and manifest variants. Cohen's kappa is linear in the number of paired annotation records.

## Evaluation Hook

The pilot agreement script checks that two completed pilot annotation files cover the same records and meet the frozen `kappa >= 0.70` threshold before full labeling.
