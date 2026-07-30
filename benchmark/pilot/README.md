# BindBench Pilot

The pilot benchmark contains twelve scenario-family manifests:

- file/object identity
- versioned key-value state
- HTTP-like resources
- authorization
- value/availability
- workflow control
- database row version
- cloud object generation
- git commit hash validation
- kubernetes resourceVersion
- payment authorization revalidation
- message queue acknowledgement

Each family has exactly three variants: `vulnerable`, `repaired`, and `safe_near_miss`. Workflow fixtures live in `examples/workflows/` and use the existing AgentLint JSON workflow format.
