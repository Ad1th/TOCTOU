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

## M2.1 Workflow IR

- `agentlint.ir.Workflow`: immutable directed workflow graph.
- `agentlint.ir.Node`: immutable workflow node with optional `ToolContract` attachment.
- `agentlint.ir.Edge`: immutable directed edge between node IDs.
- `agentlint.ir.ResourceReference`: normalized resource reference carried by a node.
- `agentlint.ir.BindingReference`: modeled binding mechanism carried by a node.
- `agentlint.ir.FindingLocation`: provenance handle for later finding APIs.
- `Workflow.node(node_id)`: deterministic node lookup.
- `Workflow.predecessors(node_id)`: direct predecessor lookup in edge order.
- `Workflow.successors(node_id)`: direct successor lookup in edge order.
- `Workflow.topological_order()`: deterministic topological ordering for acyclic workflows.

## M2.2 Dependency Propagation

- `agentlint.ir.propagate_dependencies(workflow)`: computes propagated resource and binding state over an acyclic workflow.
- `agentlint.ir.DependencyGraph`: immutable dependency-state API for a workflow.
- `DependencyGraph.state_for(node_id)`: propagated state lookup.
- `DependencyGraph.resources_at(node_id)`: propagated resources at a node.
- `DependencyGraph.bindings_at(node_id)`: propagated bindings at a node.
- `DependencyGraph.dependencies_of(node_id)`: resource dependency relationships for a node.
