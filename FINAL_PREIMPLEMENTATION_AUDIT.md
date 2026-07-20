# Final Pre-Implementation Prior-Art and Claims Audit

**Audit date:** 2026-07-20  
**Role assumed:** USENIX Security / ACM CCS Area Chair with three senior reviewers  
**Decision:** **C — Major redesign required. Do not implement.**

## 0. Executive Finding

The revised specification improved the problem statement but still proposes headline contributions that current work substantially overlaps or already contains:

- *Mind the Gap* already studies generic tool-using agent TOCTOU, creates a 66-task benchmark, uses runtime monitoring over tool sequences, and evaluates tool fusion ([paper](https://arxiv.org/abs/2508.17155)).
- *Atomicity for Agents* already formalizes planning-time versus execution-time target binding, defines a TOCTOU condition with `Bind(a,s)`, creates deterministic mutation schedules with task-specific oracles, and evaluates a benchmark plus mitigation ([paper](https://arxiv.org/abs/2603.00476)).
- *AgentFlow* already constructs a framework-agnostic agent IR with component, control-flow, and data-flow dependencies, supports static security analysis, supports five frameworks, and evaluates 5,399 real agent programs ([paper](https://arxiv.org/abs/2607.01640)).
- Classical work already frames TOCTOU as an atomicity/binding problem and static analyzers such as KERAT mine and check check–use atomicity rules ([KERAT](https://www.usenix.org/conference/usenixsecurity26/presentation/han)).

Therefore the current project is **not defensibly “the first workflow-semantic analysis framework”** and should not be implemented as specified. The sole plausible research nucleus is narrower:

> **A contract-verified analysis of whether agent workflow effects carry authority-enforceable validity preconditions for previously checked external state.**

This nucleus is only a *candidate* contribution until an additional systematic search shows that no prior agent-security system already models authority-side version/capability/conditional-operation contracts. The research program must be redesigned around that question, not around a new IR, generic static analysis, or a generic witness engine.

## 1. Source Review and Confidence

### Directly inspected full text

- Lilienthal and Hong, [*Mind the Gap*](https://arxiv.org/abs/2508.17155), 9 pages.
- Jiang et al., [*Atomicity for Agents*](https://arxiv.org/abs/2603.00476), 18 pages.
- Wang et al., [*AgentFlow*](https://arxiv.org/abs/2607.01640), paper HTML/full sections.

### Inspected primary records or official documentation

- [KERAT: Static Detection of TOCTOU Bugs Caused by Kernel Races](https://www.usenix.org/conference/usenixsecurity26/presentation/han).
- [AgentDojo](https://arxiv.org/abs/2406.13352).
- [Agent-BOM](https://arxiv.org/abs/2605.06812).
- [Agent Audit](https://arxiv.org/abs/2603.22853).
- [AIR Agent Intermediate Representation](https://agentir.org/).
- [Joern Code Property Graph](https://cpg.joern.io/), [FlowDroid](https://doi.org/10.1145/2594291.2594299), and classical file-system TOCTOU sources cited in `RESEARCH_VALIDATION.md`.

The findings below distinguish direct overlap from unverified negative claims. An absence of a discovered paper is never evidence that an idea is first.

## 2. Definitive C1–C5 Claim Matrix

Legend: **Invalid** = cannot be a paper contribution; **Partial** = potentially incremental only with a sharp new property; **Unverified** = no firstness claim allowed until further review; **Freeze** = may remain only in the limited form stated.

| Claim | Direct prior art | Determination | What may remain | What must be removed |
| --- | --- | --- | --- | --- |
| **C1: agent workflow binding calculus** | *Atomicity* defines check/use states and target binding `Bind(a,s)`, declaring vulnerability where `Bind(a,s_c) ≠ Bind(a,s_u)`; classical TOCTOU models stable object references and atomic check/use. | **Invalid as a general binding formalization.** | A calculus for **authority-enforceable tool preconditions**—e.g., version, ETag, conditional token, capability, transactional predicate—across multi-tool workflows is **Unverified**. | “First workflow binding calculus,” “first formalization of agentic binding,” and any claim based merely on naming checks/assertions/effects. |
| **C2: AWIR-B workflow IR** | *AgentFlow* ADG is a framework-agnostic agent IR with component/control/data-flow edges across five frameworks and 5,399 programs. Agent-BOM unifies static capabilities and dynamic states. AIR is an existing analysis IR for workflow/prompt/tool/protocol facts. Joern established generic multi-view code graphs. | **Invalid as an IR contribution.** | A small *analysis schema* containing authority-precondition contracts may be an implementation vehicle, not a standalone contribution. | “Framework-neutral agent workflow IR,” “first cross-framework semantics,” and an IR paper framing. |
| **C3: binding-aware static analysis** | *Mind the Gap* SIM monitors tool sequences using pair labels/FSA; *AgentFlow* does static prompt-to-tool dependency/taint analysis; KERAT statically mines and checks atomicity rules for check-use shared variables; classical TOCTOU static analysis exists. | **Partial.** | A static pass that proves/reports *missing propagation or authority enforcement of explicit resource preconditions* may be new in agent workflows, but must beat all three relevant abstractions. | Claims that CFG/DFG/taint/alias/abstract interpretation or generic check-use matching are novel. |
| **C4: deterministic witness protocol** | *Atomicity* DYNWEB contains deterministic update schedules and task-specific oracles; AgentDojo is a dynamic agent environment; classical dynamic TOCTOU work detects/prevents runtime races. | **Invalid as a generic witness protocol.** | Reproducible validation artifacts can support evaluation, but are not a headline contribution unless they validate precondition semantics beyond existing suites. | “First deterministic exploit witnesses,” generic adapters, or validation engine as a standalone novelty claim. |
| **C5: binding-focused corpus** | TOCTOU-Bench has 66 agent tasks; DYNWEB has deterministic synthesized and real-web scenarios with oracles; AgentDojo provides dynamic agent environments. | **Partial.** | A compact, independently labeled *precondition-contract compliance* corpus with hard negative controls can be evaluation infrastructure if existing corpora cannot encode the property. | “First agentic TOCTOU benchmark,” a benchmark positioned mainly by task count, or a smaller reimplementation of existing tests. |

## 3. Non-Overlap Matrix: What the Redesigned Work Could Test

This is a comparison matrix, not a novelty declaration. A `?` means further full-text review and code inspection is required before a submission claim.

| Capability | Mind the Gap | Atomicity for Agents | AgentFlow | KERAT | Proposed narrowed direction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Agent-specific TOCTOU/tool workflow | ✓ | browser-only | generic risk analysis | — | ✓ |
| Generic workflow/agent IR | — | — | ✓ | — | implementation detail only |
| Source static CFG/DFG analysis | — | — | ✓ | ✓ | ✓ |
| Check→effect dependency reasoning | pair/FSA | single observe→action | generic dependency | ✓ | ✓ |
| Explicit target/state binding | implicit pair relation | `Bind(a,s)` | generic components/dependencies | lock/atomicity rules | **authority-precondition propagation** |
| Version/ETag/CAS/capability contract modeling | — | browser DOM/target validation | ? | locks/shared variables | target property |
| Authority enforces precondition at effect | — | browser validation before action, residual window remains | ? | lock rule | target property |
| Deterministic mutation schedules + oracles | — | ✓ | — | state validation | evaluation support |
| Cross-framework source extraction | LangGraph evaluation | browser agents | 5 frameworks | — | not a headline claim |
| Large OSS corpus | — | 10 agents/websites | 5,399 programs | Linux/FreeBSD | optional, post-core |

The only potentially differentiating cell is bold. It has not been proven novel. The paper should use language such as “we investigate” until the competitor audit in Milestone R0 is complete.

## 4. Hidden and Under-Cited Prior Work

### 4.1 Directly threatening work

1. **AgentFlow (2026).** This is the most damaging omission. It makes the IR/cross-framework/static-agent-analysis framing obsolete, supporting five frameworks and a large real-world corpus. A future paper must cite it prominently and either reuse/extend its graph or explain why its graph cannot represent authority-side preconditions.
2. **Atomicity for Agents (2026).** This is more than a browser benchmark: it formally defines an action’s target binding and uses deterministic schedules/oracles. It invalidates C1/C4’s broad form.
3. **KERAT (USENIX Security 2026).** It treats check-use violations as atomicity-rule violations, mines protection rules, uses state-based validation, and finds confirmed real bugs. It sets the program-analysis bar far above a generic path matcher.
4. **Agent-BOM (2026).** It combines static capability facts with dynamic runtime semantic states for agent-security audit paths. Trace plus graph fusion cannot be advertised as new without a direct contrast.
5. **AIR (public system).** Even if not peer-reviewed, it is a public analysis IR that lowers agent code, prompts, tools, and protocols. It prevents any unqualified “first IR” statement.

### 4.2 Relevant adjacent work

- **Agent Audit (2026):** agent-aware Python/config static analysis with dataflow and MCP privilege checks; it narrows engineering novelty for a security linter.
- **AgentDojo and MCPTox:** dynamic evaluation of agent security/tool poisoning; they prevent broad dynamic-benchmark novelty claims.
- **CaMeL / capability and information-flow defenses:** formal/policy systems mediate agent tool use. They may have an authority contract analogue and must be searched for conditional-effect semantics before implementation.
- **Classical TOCTOU static/dynamic defenses:** MOPS, RaceGuard, Tsyrklevich–Yee, STEM/EDGI, and KERAT provide established check/use, atomicity, state-machine, and validation techniques. Repackaging them in Python is not enough.

### 4.3 Required follow-up search before resuming

Search full text, code, and appendices for: `ETag`, `If-Match`, `version`, `compare-and-swap`, `conditional write`, `capability`, `lease`, `precondition`, `idempotency key`, `transaction`, `tool contract`, and `authority enforcement` across AgentFlow, Agent-BOM, AIR, Agent Audit, CaMeL/FIDES/Progent/RTBAS/FORGE, and MCP security work. If any supplies a static check for predicate-to-effect conditional-operation propagation, the remaining nucleus may also be preempted.

## 5. Strongest Honest Positioning

The work is **not fundamentally an AI-agent-security contribution in its current form**. It is a generic workflow/program-analysis proposal illustrated with agents. The agent setting supplies motivating examples but does not yet require new theory: standard service/workflow transaction analysis could model the same check–use paths.

The strongest possible positioning is:

> **Agent tool APIs are partially ordered, externally authoritative effects whose security-relevant validity predicates must be transferred as machine-checkable preconditions across LLM-selected, framework-induced workflow paths.**

This is agent-specific only if experiments demonstrate all of the following:

1. framework-induced paths (tool selection, retries, handoffs, state injection) create precondition-loss paths absent from ordinary call graphs;
2. source-level workflow extraction alone is insufficient in a measured way, and selected trace/manifest evidence improves the relevant property;
3. real agent tool APIs expose or fail to expose usable conditional operations in a way that makes the analysis actionable; and
4. a conventional workflow checker or AgentFlow-like dependency graph cannot capture the authority-precondition property without the new effect-contract semantics.

If these tests fail, position the work as **workflow security analysis for distributed tool APIs**, not AI-agent security. That may still be useful but is a weaker top-security venue fit.

## 6. Simulated Reviews: Rejection Reasons and Minimum Fixes

| Rejection reason | Why a reviewer rejects | Minimum evidence or redesign to overcome |
| --- | --- | --- |
| “Novelty is preempted.” | Mind the Gap, Atomicity, AgentFlow, and KERAT overlap each headline component. | Retire C1/C2/C4; show an exact feature-by-feature non-overlap with full-text/code citations; demonstrate a property none represents. |
| “This is generic TOCTOU with agent branding.” | The formal model is standard check/use/mutation/atomicity language. | Define an agent-only semantic feature with concrete failures and ablation; otherwise change venue/positioning. |
| “The IR is redundant.” | AgentFlow, Agent-BOM, AIR, CPG already normalize agent/workflow facts. | Reuse/adapt an existing representation or make contract semantics an overlay; do not evaluate IR as a contribution. |
| “Static analysis is shallow.” | Pair matching, taint, CFG/DFG, and alias rules are established; effects are opaque. | Formal contract language, relative-soundness theorem for a core, contract inference/validation methodology, and an ablation over a nontrivial baseline. |
| “Dynamic witnesses are a benchmark harness.” | DYNWEB already has deterministic schedules and oracles. | Treat witnesses as evaluation infrastructure, or prove a new reusable precondition-preservation property across heterogeneous authorities. |
| “Benchmark is detector-shaped.” | New synthetic cases can encode author assumptions; Mind the Gap already has 66 tasks. | Port existing cases, add independent labels/negative controls, preregister split, report inter-rater agreement, and external validation. |
| “MCP support is misleading.” | Server schemas do not encode client orchestration or state semantics. | Require client workflow manifests/traces; explicitly exclude schema-only detection and quantify coverage. |
| “No real impact.” | Synthetic results may not produce findings or usable fixes. | A scoped, ethically reviewed study of real agent repositories/tool APIs with manual validation, or a deployment-quality corpus of actual API contracts. |
| “Severity is arbitrary.” | Hand-weighted score has no ground truth. | Remove from paper; do not spend implementation effort on it. |
| “Cross-framework claims are superficial.” | Two frontends do not establish semantic generality, while AgentFlow has five. | Do not claim breadth; measure one narrowly defined property across two inputs or extend an existing multi-framework frontend. |
| “Evaluation is statistically weak.” | Paired variants inflate `n`; witness failures are misclassified as safe; baselines are not comparable. | Family-level splits, raw counts, bootstrap intervals, explicit `inconclusive`, preregistered baseline mappings, and independent test corpus. |

## 7. Frozen Research Plan

### 7.1 Frozen candidate contributions

Only the following are allowed to proceed to the next research gate; none may be called novel or first until R0 passes.

1. **P1 — Authority-precondition contract model.** Define whether a tool effect accepts and authority-enforces a validity precondition from a prior check (version, capability, conditional request, transaction predicate, or stable identity).
2. **P2 — Precondition-flow analysis.** Given explicit contracts, detect paths where a required validity precondition is dropped, weakened, or replaced before an effect. This is not generic “TOCTOU detection.”
3. **P3 — Contract-compliance corpus.** A minimal, independently annotated corpus of positive, repaired, and negative precondition-propagation cases, with existing TOCTOU suites used as external context/ports where legal.
4. **P4 — Validation artifacts.** Reproducible, deterministic cases only to verify P2’s report semantics; not a separate contribution.

### 7.2 Frozen hypotheses

| ID | Hypothesis | Decision rule |
| --- | --- | --- |
| H1 | Contract-aware precondition-flow analysis improves family-level F1 over path/taint/pair baselines on a held-out contract-compliance corpus. | Continue only if both precision and recall improve with non-overlapping 95% bootstrap CIs or a preregistered practical-effect threshold. |
| H2 | The authority-enforcement dimension reduces false positives relative to “state changed between calls” heuristics. | Continue only if hard negative controls demonstrate a meaningful FP reduction. |
| H3 | At least two agent-framework constructs produce precondition-loss paths missed by an ordinary host-language CFG/DFG baseline. | Continue only if manually adjudicated examples and controlled ablation support this. |
| H4 | Contract-derived repair obligations preserve task success and block the specified invariant violation. | Continue only if paired repaired cases meet both task and safety criteria. |

There is no frozen hypothesis for severity scoring, generic dynamic confirmation, universal IR fidelity, open-source vulnerability counts, LLM-plan semantics, or broad cross-framework generalization.

### 7.3 Frozen baselines

1. **API pair/state-change heuristic:** mirrors Mind the Gap’s broad read→write sequence approach as closely as the published method permits.
2. **Reachable check/effect path:** CFG plus resource name matching; no dataflow/precondition modeling.
3. **Dependency/taint path:** control/data dependencies plus aliases; no authority-precondition state.
4. **AgentFlow extension or equivalent ADG query:** mandatory if source/code permits; otherwise a documented ADG-compatible reimplementation of its relevant dependency relation.
5. **Full P2 analysis.**

Do not use AgentDojo, MCPTox, or a prompted LLM as primary accuracy baselines; their tasks/threat models differ. They can appear in related work or qualitative ecological checks.

### 7.4 Frozen evaluation protocol

- Unit of sampling: **scenario family**, never individual paired variants.
- Corpus split: hold out entire families before analysis-rule/contract-library tuning.
- Labels: two independent annotators; publish agreement, adjudication, contracts, mutation model, and invariant.
- Positive requires a deterministic local violation trace; negative includes a reason the authority binding makes mutation irrelevant/rejected.
- Results: precision, recall, F1, FP/FN counts, per-category results, 95% stratified bootstrap CIs, contract-coverage rate, and repair utility.
- Dynamic outcome: positive witness, not-triggered-within-budget, or inconclusive; never treat lack of witness as safe.
- Reproducibility: pinned contract revision, schedule, seed, environment digest, raw data, and automatic plots/tables.

### 7.5 Explicitly out of scope

- New framework-independent agent IR.
- Generic TOCTOU scanner or generic dynamic exploit-witness engine.
- Browser-use agents and DOM/layout binding (Atomicity’s domain).
- Schema-only MCP analysis.
- Arbitrary Python/opaque remote-tool soundness.
- LLM reasoning/model-plan correctness, prompt injection, memory poisoning, and tool poisoning.
- Severity scoring, automatic patch generation, and required discovery/disclosure of zero-days.
- Claiming support for more than two narrowly specified frontend forms.

## 8. Prioritized Roadmap and Acceptance Gates

| Milestone | Deliverable | Gate: stop unless all criteria pass |
| --- | --- | --- |
| **R0 — Prior-art closure** | 10–15 page competitor dossier, full-text/code search results, claim-to-citation map | A unique authority-precondition property survives AgentFlow/Atomicity/contract-defense comparison; otherwise terminate/reframe. |
| **R1 — Problem validation** | 20–30 real tool API contract survey; independently annotated candidate cases | At least 25% of sampled effect APIs expose/need a meaningful authority precondition and at least 10 nontrivial precondition-loss workflows exist. Thresholds may be revised only before sampling. |
| **R2 — Formal core** | calculus, contract grammar, transfer functions, relative-soundness proof sketch reviewed by a PL/security expert | Proof is non-vacuous and distinguishes P2 from a check/use path query. |
| **R3 — Evaluation preregistration** | corpus protocol, family split, labels, baselines, metrics, analysis plan | Independent annotator can apply the guide; at least 0.7 kappa on pilot labeling; baselines are executable/defined. |
| **M0 — Minimal artifact foundation** | repository scaffold, schemas, CI, reproducibility manifest; no analyzer | Reproduction/validation CI passes and no scientific claim changes. |
| **M1 — Contract representation** | parser-independent contract data model and validators | Contracts express all R1 cases and reject invalid/missing authority semantics. |
| **M2 — Core analysis** | precondition-flow analyzer for a declarative core plus proof artifact | Finds frozen positives; rejects frozen hard negatives; no frontend claims. |
| **M3 — Frontend evidence** | one LangGraph subset + one client manifest/trace importer | Measured property fidelity meets preregistered threshold; unknown coverage reported. |
| **M4 — Corpus/repair evaluation** | held-out results, repair obligations, deterministic validation artifacts | H1–H4 pass; otherwise revise claims or stop. |
| **M5 — Ecological validation** | optional OSS/API study, ethics/disclosure record | Add only if it produces manually defensible evidence; it must not rescue weak core results. |
| **Paper gate** | manuscript, artifact, all generated figures/tables, limitations audit | Every sentence marked as contribution maps to a passing H1–H4 result and a checked citation. |

## 9. Area-Chair Recommendation

**Decision: C — Major redesign required.**

The proposal must not proceed to M0. The original reframing removed several weak claims, but direct review of *Atomicity for Agents* and discovery of *AgentFlow* preempt the remaining “first workflow-semantic framework,” IR, binding formalization, and deterministic-witness narratives.

Proceed only through **R0** and **R1**. If authority-side precondition propagation/enforcement is not demonstrably distinct, terminate this line as a top-tier-security submission rather than investing in an incremental scanner. If it survives, write a new specification limited to P1–P4 and submit it for another hostile audit before any code is written.
