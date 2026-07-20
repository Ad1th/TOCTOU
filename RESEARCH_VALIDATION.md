# AgentLint M-1: Research Validation

**Status:** no implementation approved. This is an adversarial review of `DESIGN.md`, written before scaffolding or code.

## Executive Decision

**Decision: C — major redesign required before implementation.**

The problem is important, but the current proposal overstates novelty. In particular, *Mind the Gap* already introduces TOCTOU-Bench with 66 realistic tasks, reports automated detection and mitigation results, and frames agentic TOCTOU as a research direction. *Atomicity for Agents* further occupies the browser-use specialization. A 36-case replacement benchmark, a generic taxonomy, and an AST/data-flow linter would look incremental unless AgentLint establishes a stronger and measurably distinct semantic capability.

The viable paper is **not** “a benchmark and scanner for agentic TOCTOU.” It is:

> **A soundness-scoped, workflow-semantic detector that identifies check–use binding failures across *declared workflows and execution traces*, then produces deterministic exploit witnesses under an explicit resource-transition model.**

This demands three evidence-backed claims: (i) a new class of *workflow-semantic* cases missed by trajectory/prompt-level methods; (ii) a formal property and a conservative detector with stated coverage; and (iii) a validation protocol that distinguishes an executable witness from a static possibility. Do not claim firstness for agentic TOCTOU, a benchmark, automated detection, or generic mitigation.

## 1. Literature Review

### 1.1 Classical TOCTOU

TOCTOU began as a security problem in privileged operating-system programs: a predicate is checked on mutable state, then a later action assumes that predicate still holds. Early systems accounts trace the issue to McPhee (1974) and Abbott et al. (1976); Bishop and Dilger’s analysis remains a standard formal framing. The canonical Unix form is `access()` followed by `open()`, where pathname resolution or metadata can be swapped. The file-system model STEM enumerates exploitable check/use pairs and explains why path-to-object remapping—not elapsed wall time alone—is the critical condition [STEM/EDGI](https://doi.org/10.1016/j.cose.2010.09.004). POSIX advice and platform guidance consequently prefer descriptor-based operations, `openat`, no-follow flags, exclusive creation, and privilege separation over pre-checks; the API-level risk is also documented by [Apple’s secure-coding guidance](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html).

Mitigations evolved from “make the window small” to atomicity and binding: use atomic check-and-act operations, retain a stable object handle, lock, version, or transaction, or revalidate immediately before an irreversible effect. Portable file-system work shows why probabilistic hardening is not a substitute for a guarantee ([Tsafrir et al.](https://www.usenix.org/legacy/events/fast08/tech/full_papers/tsafrir/tsafrir_html/index.html)); attack work shows timing-based defenses can fail ([Borisov et al.](https://www.usenix.org/legacy/publications/library/proceedings/sec05/tech/full_papers/borisov/borisov_html/races.html)).

**Databases and distributed systems.** Here the same shape appears as stale reads, read–write conflicts, write skew, and check-then-act business logic. Serializable transactions, strict two-phase locking, compare-and-swap, optimistic concurrency with versions, idempotency tokens, and conditional writes provide binding. Snapshot isolation improves concurrency but does not universally eliminate anomalies; transaction systems make atomic execution the DBMS’s responsibility, not application code’s ([discussion of isolation limits](https://arxiv.org/abs/2405.18393)). Distributed services complicate a global atomic guarantee due to independent authorities, failures, and latency. Practical defenses are resource-specific preconditions (ETag/version/lease), server-side conditional actions, and compensating actions—not a distributed “lock everything.”

**Implication for AgentLint.** The right abstraction is a **validity binding**, not a temporal delay. An agent is vulnerable only when it uses a stale, unbound assertion about an external resource. `Wait` and retries increase opportunity but are neither necessary nor sufficient. This corrects a central weakness in `DESIGN.md`, which makes the gap too syntactic.

### 1.2 Static analysis and graph representations

| System / line | Relevant technique | What AgentLint may adapt | What it cannot claim |
| --- | --- | --- | --- |
| CodeQL | language databases; global/local data flow; path queries and library models | source/sink/barrier modeling, path explanations, query regression suites | first use of CFG/DFG/taint for security |
| Joern / CPG | language-agnostic attributed multigraph merging syntax, CFG, and DFG | provenance graph, multi-view graph schema, declarative rule layer | first framework-independent IR; CPG already does this broadly ([specification](https://cpg.joern.io/)) |
| Clang Static Analyzer | interprocedural path-sensitive symbolic execution | path feasibility and constraint-aware witnesses | practical whole-program path sensitivity for dynamic Python ([documentation](https://clang.llvm.org/docs/ClangStaticAnalyzer.html)) |
| Infer | compositional abstract interpretation and bi-abduction | summaries/effect contracts for tools and subgraphs | a novel abstract-interpretation architecture |
| FlowDroid | lifecycle models plus context/flow/field/object-sensitive taint; benchmark discipline | framework semantic models and precision/recall evaluation ([paper](https://doi.org/10.1145/2594291.2594299)) | first high-precision taint analysis or paired benchmark |
| Semgrep | developer-facing syntactic and taint rules | transparent lexical baseline and rule authoring UX | interprocedural coverage without precise evidence ([taint docs](https://semgrep.dev/docs/writing-rules/glossary)) |

The proven lesson is that precision requires domain models. In AgentLint, a tool declaration must supply an **effect contract**: resources read/written, validation predicate established, argument-to-resource mapping, version/precondition support, irreversible effect, and concurrency semantics. Without these, taint is at best a ranking heuristic. An “IR plus taint analysis” is not a contribution; **an agent workflow effect-and-binding model** may be.

### 1.3 LLM-agent and tool security

*Mind the Gap* is mandatory baseline work. It is the first study focused on agentic TOCTOU; it introduces TOCTOU-Bench (66 user tasks), adapts prompt rewriting, integrity monitoring, and tool fusion, and reports limited automated detection accuracy and reduced attack windows ([paper](https://arxiv.org/abs/2508.17155)). AgentLint must replicate relevant settings where permitted, explain the baseline’s scope accurately, and show which semantically defined cases it adds or detects.

*Atomicity for Agents* narrows the problem to browser-use agents, exposing and mitigating TOCTOU around browser state ([paper record](https://papers.cool/arxiv/2603.00476)). It weakens broad claims but creates a clean contrast: browser observation/action differs from tool-chain state binding. If that paper already provides formal/static claims, read the full text before submission and revise the matrix accordingly.

Agent security literature is dominated by indirect prompt injection, tool poisoning, excessive agency, capability control, and action mediation—not TOCTOU. AgentDojo provides a dynamic environment for prompt-injection attack/defense evaluation ([paper](https://arxiv.org/abs/2406.13352)); MCPTox targets tool-description poisoning on real MCP servers ([paper](https://arxiv.org/abs/2508.14925)). These are important ecological comparisons but inappropriate detection baselines because their threat and oracle are different. Recent work also warns that agent-security benchmarks can overestimate defenses because of benchmark design choices; this reinforces a held-out, independently executable validation protocol ([benchmark critique](https://firewall-defenses.github.io/)).

MCP is a protocol, not an orchestration language. Official guidance already notes TOCTOU in DNS validation and recommends pinning resolution between validation and request ([MCP security guidance](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)). Its tool schemas do not encode the client’s check-to-use workflow. Therefore **“MCP frontend” must mean trace/manifest/client-workflow frontend**, never server-schema-only static detection. LangGraph is a relevant graph runtime: it explicitly has conditional edges, tool nodes, state, interruption, persistence, and parallel tool execution ([LangGraph workflow docs](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/?h=tool)). These are the semantic features AgentLint should model and measure.

**Missing tooling.** There is no identified published tool that simultaneously (1) represents workflow-level resource predicates and their bindings, (2) analyzes source-declared graphs plus trace-derived executions, and (3) returns deterministic resource-transition witnesses. This is a hypothesis to verify through a systematic search before paper submission—not a fact to assert yet.

## 2. Novelty Matrix

Legend: ✓ documented contribution; ~ partial/adjacent; — not a stated contribution; ? requires full-text verification. “IR” means a workflow-semantic IR, not a generic code graph.

| Work | Agent-specific | Static analysis | Dynamic validation | Framework-independent | Workflow IR | TOCTOU benchmark | Severity | Repair advice | OSS evaluation | Public corpus | Cross-framework |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| STEM/EDGI (2010) | — | ✓ | ~ | — | — | — | — | ✓ | ✓ | — | — |
| CodeQL | — | ✓ | — | ✓ | generic DB | — | — | ✓ | ✓ | queries | ✓ |
| Joern / CPG | — | ✓ | — | ✓ | generic CPG | — | — | ~ | ✓ | tooling | ✓ |
| FlowDroid / DroidBench | — | ✓ | — | — | Android model | ✓ | — | — | ✓ | ✓ | — |
| AgentDojo | ✓ | — | ✓ | ~ | environment | — | — | defenses | — | ✓ | ~ |
| MCPTox | ✓ | — | ✓ | MCP-focused | — | — | — | — | real servers | ✓ | — |
| Mind the Gap | ✓ | ~ automated detection | ✓ trajectories | ~ | — | ✓ (66 tasks) | — | ✓ | — | ✓ | ~ |
| Atomicity for Agents | ✓ browser agents | ? | ✓ | browser scope | ? | ? | ? | ✓ | ? | ? | — |
| **AgentLint, proposed** | ✓ | ✓ | ✓ deterministic witness | ✓ but bounded | ✓ binding semantics | **extension, not first** | ~ auxiliary | ✓ repair classes | target | target | ✓ two inputs |

### Genuine novelty—conditional on evidence

1. **Predicate-to-effect binding semantics**: distinguish a stale observation from a security-relevant checked predicate that is later consumed without a binding such as version, handle, transaction, or atomic operation.
2. **Dual evidence detector**: combine source/manifest workflow extraction with trace-derived AWIR and report agreement/disagreement; this directly addresses dynamic agent graphs rather than pretending static extraction is complete.
3. **Deterministic exploit witness protocol**: make mutation placement a first-class, replayable transition schedule with an explicit safety oracle; report confirmed/inconclusive outcomes.
4. **Cross-framework semantic fidelity evaluation**: evaluate whether two very different workflow inputs preserve a predefined set of semantics, not merely whether parsers “work.”

### Not novel as currently framed

- Agentic TOCTOU as a problem, automated detection, a public agentic TOCTOU benchmark, and system-inspired mitigations.
- Generic CFG/DFG, SSA, aliasing, taint tracking, IRs, ranking, and static-plus-dynamic workflows.
- A severity score unless validated against independently adjudicated exploitability and impact outcomes; otherwise it is product packaging, not research.

## 3. Formal Model (minimal but sufficient)

Let a workflow be a labeled transition system `W = (Q, q0, E, →)` where each event `e ∈ E` has an actor, input/output values, source provenance, and effect contract. The runtime state is `σ = (ρ, κ, η)`: resource store `ρ`, agent/workflow state `κ`, and schedule/causal history `η`. A resource is `r = (id, ver, value, authority)`; `ver` is optional but must be modeled as absent, immutable, or mutable.

An effect contract contains `Read(r)`, `Check(r, φ, t)`, `Use(r, a, ψ)`, `Write(r)`, `Bind(r, b)`, `Atomic(r, φ, a)`, and `Sync(h)`. A check produces an assertion `α = (r, φ, ver_c, t_c, b)` where `b` is an optional stable binding (object handle, version/ETag, conditional token, lock/lease, transaction). A use consumes `α` if it is data- or control-dependent on the check; dependency is `c ⇝ u` in the union of DFG and control-dependence relation.

An attacker mutation is a permitted state transition `μ ∈ M_A` with `σ ─μ→ σ'` such that it changes the truth of `φ(r)` or redirects the resource referred to by `r`. A happens-before relation `≺` derives from workflow edges, joins, callbacks, and trace order. A **feasible gap** exists if `c ≺ μ ≺ u` and no synchronization excludes `μ`.

An Agent TOCTOU vulnerability exists iff there are `c,u,r,φ,μ` such that:

1. `c = Check(r, φ, t_c)` and `u = Use(r, a, ψ)`;
2. `c ⇝ u` and `c ≺ u` on a feasible workflow path;
3. `μ ∈ M_A` occurs in the gap and makes `φ(r)` false or changes the denotation of `r`;
4. no valid binding, recheck, or atomic operation guarantees that `u` observes the checked state; and
5. executing `u` after `μ` violates a case-specific security invariant `I`.

Condition 5 separates syntactic stale-read patterns from vulnerabilities. A static report is a **candidate** if it proves/over-approximates 1–4. A **confirmed finding** includes a witness trace `τ = c · μ · u` satisfying 5 in an isolated adapter. No finite dynamic campaign proves absence; lack of a witness is `inconclusive`.

### Detection algorithm and complexity

Construct an attributed workflow graph with control, data/control-dependence, resource-alias, and happens-before edges. For each modeled `Check`, forward-propagate its assertion through a finite abstract domain `(resource alias set, predicate class, binding state, trust, path condition)`. At a `Use`, emit a candidate if resource aliases intersect, the assertion reaches the use, the mutation model allows invalidation, and no kill/barrier transfer function proves a valid binding.

For `N` nodes, `E` edges, `R` resource aliases, `P` predicate classes, and bounded context `k`, a worklist bound is `O(kE RP)` lattice updates, plus bounded feasibility checks. State precisely that this is a bound for the supported AWIR subset—not a proof for arbitrary Python or LLM behavior. The desired theorem is **relative soundness**: for closed workflows whose contracts, aliases, and scheduler semantics are exact, every concrete violation maps to a static candidate. Prove this for a small core language; do not claim soundness for extracted production Python.

## 4. Hypotheses and Required Experiments

| Hypothesis | Test | Success criterion | Critical caveat |
| --- | --- | --- | --- |
| H1: binding-aware analysis outperforms lexical/CFG baselines | frozen held-out cases and external corpus | materially higher F1 with bootstrap CI | benchmark must contain nontrivial binding cases |
| H2: effect contracts and alias analysis each improve precision/recall | factorial ablation | paired F1 deltas and error taxonomy | ablate only independently meaningful components |
| H3: dynamic witnesses improve alert usefulness | static candidates with predeclared mutation adapters | higher confirmed-alert precision; report inconclusive rate | validation is not an oracle for absence |
| H4: AWIR retains required semantics across frontends | source/trace gold graphs with annotator agreement | node/edge/effect/binding fidelity, not only parse rate | trace is one execution, not full workflow coverage |
| H5: binding status predicts exploitability better than gap duration alone | matched cases varying binding and delays | binding feature adds predictive value | do not claim causal generality beyond adapters |
| H6: repairs preserve utility while blocking violation | vulnerable/patched pair tests | zero safety-oracle violations and unchanged task oracle | tests must make benign semantics explicit |

Drop the severity hypothesis unless there is an external human-expert labeling study or real disclosure outcomes. Ranking a synthetic set using its own hand-coded labels is circular.

## 5. Baselines

**Required internal baselines.**

1. **Lexical check→use matcher:** API-name/configurable pattern pairing within function/file. It establishes the minimum value beyond grep-like detection.
2. **CFG reachability:** check/use matching plus reachability, without data/control dependency or resource aliasing.
3. **Dependency-aware, binding-agnostic:** measures whether the central binding semantics adds value.
4. **AgentLint static:** full candidate detector.
5. **AgentLint static + witness validation:** measures operational precision and evidence cost, not recall against “confirmed only.”

**External baselines, only if input-compatible.**

- Reimplement the published automated detector from *Mind the Gap* if its code/specification permits exact reproduction; otherwise reproduce its documented heuristic and label it “adapted,” not “original.”
- Evaluate Semgrep/CodeQL-style rules only on the source subset they actually support. They are baselines for pattern matching, not agentic workflow semantics.
- Use AgentDojo/MCPTox only as **ecological environment comparisons**, not accuracy competitors. Their attack class is different.

It is invalid to compare against an LLM prompt (“find TOCTOU bugs”) as a primary baseline because model/version/prompt variance and unverifiable reasoning confound the contribution. It may appear only as an exploratory qualitative comparison with fixed models, prompts, and cost.

## 6. Architecture Review and Redesign

| Module | Why it exists | Current weakness | Required redesign | Publication value |
| --- | --- | --- | --- | --- |
| AWIR | makes workflow semantics analyzable across inputs | looks like generic IR; too many node types before proof | reduce to core LTS + effect contracts + bindings; use optional extensions | high, if semantics/fidelity are evaluated |
| Parser/frontends | obtain workflows | source extraction from dynamic Python is fragile; MCP schemas insufficient | source/manifest frontend plus trace frontend; capability/coverage matrix | medium-high |
| Static analysis | candidate enumeration | generic taint story; check categories are underspecified | binding-aware abstract domain; resource contract library; relative-soundness core | highest |
| Dynamic validator | distinguish candidates from evidence | may become a hand-written benchmark oracle runner | adapter interface with predeclared mutation models and replayable witness format | high only if deterministic and reusable |
| Benchmark | evaluate | duplicative of existing 66-task TOCTOU-Bench | create an extension corpus focused on semantic binding, concurrency, and cross-framework fidelity; reuse/port existing cases when licensed | high if independently labeled and externalized |
| Severity | prioritization | arbitrary weights; adds little science | defer from main paper or make a small transparent report field | low; remove from critical path |
| Experiments | credible evidence | broad list but weak causal mapping | preregister H1–H6; include calibration, unsupported-construct coverage, and repair utility | essential |

**Simplification.** Do not begin with arbitrary AST, LLM plans, multi-agent natural-language “context drift,” all resource types, and full interprocedural Python. Start with a declarative core workflow language plus two ingestion paths, and support only effects with explicit contracts. “Context/retrieval drift” is currently too broad and overlaps prompt injection; exclude it unless a resource identity/predicate/binding can be formalized. Likewise, a human gate is not inherently a race; it matters only if it separates a checked predicate from an unbound effect.

**Strengthening.** Add a fourth artifact to each finding: a **repair obligation**. It states which binding property a fix must establish—e.g., “the effect must carry the checked ETag,” “use an atomic conditional update,” or “re-read authorization at the enforcement point.” This is a principled repair suggestion, not unsafe automatic code generation.

## 7. Experimental Plan Review

| Experiment | Keep? | Review | Required change |
| --- | --- | --- |
| E1 detection accuracy | yes | central but benchmark-only results are weak | frozen splits; include ports/external cases; report macro and per-class intervals |
| E2 dynamic confirmation | yes | central differentiator | measure static PPV, witness yield, schedules/time, inconclusive cases, and oracle coverage |
| E3 scalability | yes, reduced | useful only after correctness | synthetic graphs must preserve semantics; report precision/runtime tradeoff across context bounds |
| E4 ablation | yes | reviewers will demand it | ablate binding semantics, contracts, aliasing, trace augmentation, and validation separately |
| E5 frontend robustness | replace | “parse fidelity” is vague | semantic-fidelity benchmark: edges, effects, resource IDs, concurrency, bindings, and unknowns |
| E6 open-source study | conditional | strongest ecological evidence but high risk | protocol, selection criteria, manual triage, disclosure plan; do not block core paper on zero-days |
| New: repair utility | yes | current proposal lacks mitigation evidence | matched patched workflows: task success vs safety invariant |
| New: contract sensitivity | yes | analysis depends on summaries | measure degradation under missing/imprecise contracts and annotator effort |
| New: agreement study | yes | labels and effect models are subjective | independent annotation, kappa, adjudication before tuning |

For all rates, use task-level stratified bootstrap confidence intervals, report raw contingency tables, fix seeds/schedules, and disclose all timeouts/exclusions. A 30-run rule helps runtime measurements, not static deterministic accuracy; do not apply it mechanically.

## 8. Reviewer Simulation

### Reviewer #1 — Program analysis

“The submission calls an attributed graph an IR and taint propagation a static analysis contribution. Neither is new. The paper lacks a formal semantics for a check, resource identity, aliasing across tools, and a proof or even a sharply scoped soundness statement. Extracting LangGraph from Python is likely unsound and incomplete; MCP schemas do not reveal client control flow. I would reject unless the authors narrow the language, formalize binding, measure frontend semantic fidelity, and demonstrate that their abstraction—not more rules—produces the gains.”

**Likely score now:** 2/5. **Rescue:** core calculus + relative-soundness theorem + binding-centric ablation + documented unsupported constructs.

### Reviewer #2 — Empirical security

“The paper claims a benchmark but cites no comparison with the 66-task TOCTOU-Bench in Mind the Gap. Thirty-six handcrafted pairs risk being a test suite tailored to the detector. The dynamic validator seems to mutate benchmark mocks that the authors control, thus confirming only expected behavior. The open-source study is speculative. Severity weights are arbitrary. I need independent labels, external or ported cases, mutation-model coverage, strong baselines, and negative controls before I believe F1 or exploitability claims.”

**Likely score now:** 1–2/5. **Rescue:** benchmark extension rather than replacement, preregistered holdout, open mutation protocol, annotator agreement, negative/near-miss controls, and repair-utility experiment.

### Reviewer #3 — Agent security/systems

“Why is TOCTOU unique to agents rather than an ordinary distributed-workflow bug? Mind the Gap and browser-agent work already identify it. The agent-specific parts (LLMPlan, context drift) look hand-wavy. The paper needs evidence that planning, retries, tool abstraction, or multi-agent handoff introduces vulnerabilities or detection challenges not captured by conventional check-use analyses. Cross-framework support is asserted rather than evaluated. The work may be a useful engineering artifact but not yet a top-tier security contribution.”

**Likely score now:** 2/5. **Rescue:** matched experiments showing the contribution of agent workflow semantics; exact contrast with classical binding; at least two genuinely distinct frontends; trace/source disagreement study; meaningful real-world triage.

## 9. Contributions Worth Claiming (after redesign)

1. **Formal workflow validity-binding model.** Motivation: “gap length” is not the security condition. Novelty: models check predicates, mutable resource identity, and durable/atomic bindings across agent workflow semantics. Impact: defines what is and is not an agentic TOCTOU finding. Reviewer risk: may be judged a renaming of transactions; answer with agent-specific asynchronous/handoff/tool-effect semantics and proof scope.
2. **Binding-aware, dual-evidence analysis.** Motivation: source graphs are incomplete and traces are under-approximate. Novelty: one semantic representation accepts declared workflows and traces and treats disagreement/unknowns as evidence. Impact: credible cross-framework analysis. Reviewer risk: two shallow frontends; answer with fidelity and coverage measurements.
3. **Deterministic exploit-witness validation protocol.** Motivation: static candidates and trajectory-level attack rates do not establish exploitability. Novelty: reusable resource adapters, explicit mutation capabilities, and oracle-bearing replay artifacts. Impact: auditability and reproducibility. Reviewer risk: merely a test harness; answer with general adapter semantics, cross-resource evaluation, and public witnesses.
4. **AgentTOCTOU-Bind extension corpus.** Motivation: extant benchmarks do not necessarily isolate binding semantics. Novelty: independently labeled, paired cases with resource contracts, negative controls, repaired variants, and ports across two workflow representations. Impact: a reusable evaluation artifact. Reviewer risk: synthetic bias; answer with existing-benchmark ports and carefully scoped OSS cases.

Do not make severity scoring a headline contribution. Do not promise automatic repair; provide repair obligations and manually authored patterns unless repair is separately evaluated.

## 10. Venue Positioning (after redesign; conservative)

| Venue | Fit | Required evidence | Acceptance probability with excellent execution |
| --- | --- | --- | --- |
| USENIX Security | best fit for usable analysis + artifact | clear threat model, real/security-relevant findings, reproducible benchmark/witness artifact | 10–18% |
| ACM CCS | fit if formal/static technique is deep | formal result, rigorous baselines, scale and precision story | 8–15% |
| NDSS | fit for timely applied security | compelling agent-security impact, strong empirical validation, ethical real-world study | 10–18% |
| IEEE S&P | hardest fit | fundamental formal insight or broad high-impact findings beyond a tool | 4–10% |

These are field-level priors, not forecasts. With the current design, estimates are below 5% at all four venues because of duplicated framing and unvalidated methodology. A workshop or systems-security venue is a reasonable fallback if the work remains primarily an artifact/tool.

## 11. Risks and Mitigations

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Existing work already occupies claimed novelty | critical | rewrite claims; benchmark extension/port; full competitor analysis before coding |
| Effect contracts require manual annotations | high | measure contract effort and missing-contract sensitivity; publish model library and annotation guide |
| Static Python frontend is incomplete | high | trace/manifest path, conservative `Unknown`, semantic coverage matrix, no universal soundness claim |
| Synthetic benchmark overfits detector | critical | frozen split before rule design, external ports, independent annotators, negative controls |
| Dynamic results are flaky or circular | high | deterministic adapters, predeclared mutation models, public traces/oracles, inconclusive result class |
| Few/no OSS confirmations | medium | frame as feasibility/triage, not headline; do not rely on zero-days |
| Agent-specificity is rhetorical | high | matched ablations against ordinary workflow analysis and concrete language/runtime semantics |
| Severity model distracts | medium | defer or remove from main contribution |

## 12. Prioritized Action List

| Rank | Recommendation | Impact | Effort | Research rationale |
| ---: | --- | --- | --- | --- |
| 1 | **Replace the paper claim with validity-binding semantics and deterministic witnesses; explicitly retire “first detector/benchmark.”** | High | Medium | Prevents an immediate novelty rejection caused by Mind the Gap and related work; makes the core condition scientifically precise. |
| 2 | **Perform a systematic competitor audit, especially full-text comparison to Mind the Gap and Atomicity for Agents; then freeze a claim table.** | High | Low | Claims cannot be credible until exact overlaps in detection, benchmark, dynamic validation, and mitigation are resolved. |
| 3 | **Build a small formal core and prove relative soundness for binding violations under explicit effect contracts.** | High | High | Converts an engineering linter into a program-analysis paper and sharply scopes limitations. |
| 4 | **Redesign the corpus as an independently labeled extension/port suite focused on binding semantics, near-misses, and paired repairs—not a smaller replacement benchmark.** | High | High | Directly addresses benchmark duplication, overfitting, and the absence of negative controls. |
| 5 | **Make source/manifest and trace ingestion two equal frontends and evaluate semantic fidelity, coverage, and disagreement.** | High | Medium | Cross-framework support becomes measurable rather than aspirational, and handles dynamic agent graphs honestly. |
| 6 | **Specify an open deterministic mutation/witness protocol with resource adapters, safety oracles, and “inconclusive” outcomes.** | High | Medium | Gives dynamic validation scientific force beyond a bespoke fuzzing harness. |
| 7 | **Pre-register H1–H6, frozen splits, required baselines, and ablations before detector rules are tuned.** | High | Low | Prevents hindsight tuning and increases evaluation credibility at low cost. |
| 8 | **Add repair-obligation and repair-utility evaluation; defer arbitrary numerical severity scoring.** | Medium | Medium | Actionable mitigation with preserved benign utility is more publishable than unvalidated risk weights. |
| 9 | **Run an ethics-reviewed OSS triage study only after core results; treat it as supplementary ecological validity.** | Medium | High | Strong upside but should not create a fragile dependency on unconfirmed disclosures. |
| 10 | **Narrow the first supported language/resource subset and quantify contract effort and unsupported constructs.** | Medium | Medium | Precision and honest scope are preferable to broad but unverifiable framework claims. |

## 13. Implementation Readiness

Do **not** scaffold or implement M0 yet. First complete a revised research specification answering the following approval questions:

1. What exact capability is absent from *Mind the Gap* and *Atomicity for Agents*, with citations and a non-overlap table?
2. What is the formal definition of a binding, and which check/use operations in the first supported subset have effect contracts?
3. Which existing benchmark cases can be legally reused/ported, and which new cases uniquely test binding semantics?
4. What fixed hypotheses, splits, baselines, negative controls, and acceptance thresholds will be declared before implementation?
5. What is the proof claim (or explicitly non-proof claim), and what assumptions make it valid?

**Next gate:** write `REVISED_RESEARCH_SPEC.md` that resolves these five questions. Only then approve the minimal M0 scaffold. This extra design pass has higher expected acceptance value than beginning implementation now.

## References (starting set)

- Lilienthal and Hong, [Mind the Gap: TOCTOU Vulnerabilities in LLM-Enabled Agents](https://arxiv.org/abs/2508.17155), 2025.
- Wei et al., [AgentDojo](https://arxiv.org/abs/2406.13352), 2024.
- Yoon et al., [Modeling and Preventing TOCTTOU Vulnerabilities in Unix-Style File Systems](https://doi.org/10.1016/j.cose.2010.09.004), 2010.
- Tsafrir et al., [Portably Solving File TOCTTOU Races with Hardness Amplification](https://www.usenix.org/legacy/events/fast08/tech/full_papers/tsafrir/tsafrir_html/index.html), FAST 2008.
- Borisov et al., [Fixing Races for Fun and Profit](https://www.usenix.org/legacy/publications/library/proceedings/sec05/tech/full_papers/borisov/borisov_html/races.html), USENIX Security 2005.
- Yamaguchi et al., [Code Property Graph Specification](https://cpg.joern.io/).
- Arzt et al., [FlowDroid](https://doi.org/10.1145/2594291.2594299), PLDI 2014.
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices).
- [LangGraph Workflows and Agents](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/?h=tool).
