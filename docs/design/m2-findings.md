# M2.3 Design: Finding Generation

## Scope

M2.3 implements finding generation over the existing workflow IR and `DependencyGraph`. It does not implement parsing, vulnerability validation, severity scoring, contract inference, benchmark execution, repair generation, or new dependency algorithms.

## Problem

The static core needs a typed, deterministic way to report missing check-effect binding relationships after dependencies have already been propagated.

## Solution

`generate_findings(workflow, dependency_graph)` scans dependency relationships in deterministic propagation order. A relationship becomes a finding only when its origin node has a `CHECK` contract, its dependent node has an `EFFECT` contract, and no propagated `BindingReference` on that relationship is authority-enforced with a modeled non-`none` binding mechanism.

## Data Structures

- `Finding`: immutable report containing resource, check node, effect node, missing binding, location, and repair obligation identifier.
- `FindingKind`: currently `missing_check_effect_binding`.
- `MissingBinding`: currently `authority_enforced_check_effect_binding`.
- `RepairObligationId`: currently `bind_check_to_effect`.

## Interfaces

- `agentlint.ir.generate_findings(workflow, dependency_graph=None)`
- `agentlint.ir.Finding`
- `agentlint.ir.FindingKind`
- `agentlint.ir.MissingBinding`
- `agentlint.ir.RepairObligationId`

## Determinism

Finding order follows dependency relationship order from M2.2. Duplicate finding identifiers are removed while preserving first occurrence.

## Complexity

For `D` dependency relationships and `B` propagated bindings per relationship, generation is `O(D * B)`.

## Acceptance Coverage

Unit tests cover vulnerable workflows, correctly bound workflows, multiple findings, deterministic ordering, and non-check false-finding suppression.
