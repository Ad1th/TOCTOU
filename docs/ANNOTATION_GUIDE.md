# BindBench Annotation Guide

## Purpose

This guide standardizes M1 pilot labeling for check-effect binding risks. It is limited to the frozen AgentLint scope: local, deterministic workflow cases with explicit tool contracts.

## Labels

Each annotator records the following for every family variant:

- `family_id`: stable family identifier.
- `variant`: one of `vulnerable`, `repaired`, or `safe_near_miss`.
- `resource`: mutable resource whose state is checked and later acted on.
- `check`: contract identifier for the predicate-producing check.
- `effect`: contract identifier for the dependent effect.
- `mutation`: external state change attempted between check and effect.
- `existing_binding`: binding present in the workflow, or `none`.
- `expected_result`: one of `candidate_risk`, `protected`, or `safe_near_miss`.
- `repair_obligation`: property required to remove the risk.

## Decision Rules

- Label `candidate_risk` only when the variant has a dependent check-effect pair on the same resource and no modeled binding mechanism.
- Label `protected` when an atomic operation, version token, stable identity, revalidation, or synchronization mechanism is declared as authority-enforced.
- Label `safe_near_miss` when the workflow shape resembles a risk but the effect does not depend on stale checked state.
- Do not infer authority behavior from tool names. Use the explicit contract.
- If a contract is missing or unclear, mark the annotation for adjudication before adding it to the full corpus.

## Pilot Completion Criterion

M1 requires two completed pilot annotation files over the six pilot families. Agreement is measured with Cohen's kappa over `expected_result`; the acceptance threshold is `0.70`.
