# M2.1 Design: Workflow IR Foundation

## Scope

M2.1 implements only the immutable workflow graph foundation for the frozen internal model. It does not implement parsing, dependency propagation, binding analysis, finding generation, validation, experiments, or repairs.

## Problem

Later milestones need a deterministic graph representation that can attach M1 tool contracts to workflow nodes and expose basic traversal operations without committing to any frontend or analysis algorithm.

## Solution

The IR is a directed graph of immutable `Node` and `Edge` objects inside an immutable `Workflow`. Nodes may carry `ToolContract` objects, `ResourceReference` values, `BindingReference` values, and provenance strings.

## Data Structures

- `Workflow`: workflow identifier, node tuple, edge tuple.
- `Node`: node identifier, kind, label, optional `ToolContract`, resources, bindings, provenance.
- `Edge`: edge identifier, source node ID, target node ID, kind, label.
- `ResourceReference`: normalized resource ID, source argument, type, optional stable identity.
- `BindingReference`: binding mechanism, contract ID, authority-enforcement flag.
- `FindingLocation`: workflow/node/edge/source provenance handle for later finding APIs.

## Interfaces

- `Workflow.node(node_id)`
- `Workflow.predecessors(node_id)`
- `Workflow.successors(node_id)`
- `Workflow.topological_order()`

## Validation

Construction rejects empty workflows, duplicate node IDs, duplicate edge IDs, invalid edge endpoints, and malformed identifiers. Cycles are representable because the frozen specification does not prohibit cyclic workflows; `topological_order()` raises `GraphCycleError` when a cycle prevents ordering.

## Determinism

Traversal preserves constructor order. Topological ordering uses deterministic node order for initially ready nodes and deterministic edge order for successor release.

## Complexity

Construction validates nodes and edges in `O(N + E)`. Predecessor and successor lookup are `O(E)` in this foundation implementation. Topological ordering is `O(N + E)`.

## Evaluation Hook

Unit tests cover construction, invalid graphs, traversal, cycle reporting, immutability, and M1 `ToolContract` integration.
