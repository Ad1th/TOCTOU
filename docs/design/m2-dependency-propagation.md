# M2.2 Design: Dependency Propagation

## Scope

M2.2 implements typed dependency propagation over the existing workflow IR only. It does not implement parsing, vulnerability detection, contract evaluation, findings, validation, experiments, or repair suggestions.

## Problem

Later static analysis needs a deterministic record of which resource references and binding metadata can reach each workflow node. This must be computed independently of any security decision.

## Solution

`propagate_dependencies(workflow)` walks the workflow in deterministic topological order. At each node it unions predecessor dependency state, appends resources and bindings declared directly on the node, deduplicates by immutable value equality, and records resource dependency relationships from origin nodes to dependent nodes.

## Data Structures

- `PropagatedResource`: resource plus origin node ID.
- `PropagatedBinding`: binding plus origin node ID.
- `NodeDependencyState`: propagated resources and bindings available at one node.
- `DependencyRelationship`: resource-origin to dependent-node relationship.
- `DependencyGraph`: immutable API for node states and dependency relationships.

## Interfaces

- `agentlint.ir.propagate_dependencies(workflow)`
- `DependencyGraph.state_for(node_id)`
- `DependencyGraph.resources_at(node_id)`
- `DependencyGraph.bindings_at(node_id)`
- `DependencyGraph.dependencies_of(node_id)`

## Determinism

Propagation uses `Workflow.topological_order()`, constructor node order, and constructor edge order. Merge points deduplicate stable values without sorting or hashing-dependent output order.

## Complexity

For `N` nodes, `E` edges, and `D` propagated dependency values, propagation is `O(N + E + D)` for acyclic workflows under the current tuple-based foundation.

## Acceptance Coverage

Unit tests cover branching workflows, merge-point deduplication, multiple resources, binding metadata preservation, deterministic output, and cycle rejection.
