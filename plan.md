# Enterprise AI Governance & Compliance Agent — Plan

Scope note: this plan covers **Runtime Observability** and **Scheduled Observability** in depth, per an explicit scoping decision to defer full-blown approval-workflow engines, exception-management subsystems, and dashboard/reporting platforms to future enhancements. Those are referenced where relevant but not designed in detail here.

---

# Part 1 — System & Architecture

## 1.1 Objectives

- Continuous, automated assurance that every AI application/agent in the enterprise meets security, privacy, fairness, and regulatory bars — without becoming a velocity tax that pushes teams into shadow AI.
- Single system of record for all AI assets (models, agents, prompts, RAG pipelines, third-party AI APIs).
- Risk-tiered governance: a read-only FAQ bot and an autonomous agent with payment/HR-action authority must never clear the same bar.
- Shift-left: catch violations at design/CI time, not only after go-live.
- Continuous, not point-in-time: governance as an ongoing control loop (drift, new CVEs, new regulations, model updates), not a one-time launch gate.
- Regulator-ready evidence: every decision (approve/block/waive) traceable to a policy version, a scan result, and a human or automated approver.
- Human-in-the-loop where it matters, automated everywhere else.

## 1.2 Assumptions

- Enterprise already has baseline IAM/SSO, ticketing (Jira/ServiceNow), and an observability stack (Datadog/Grafana/OpenTelemetry-class) — this system integrates with those, it does not replace them.
- Initial scope is internal enterprise AI agents/apps, not consumer-facing products. Regulatory lens is EU AI Act / GDPR / general enterprise compliance, not sector-specific licensing (HIPAA/FDA, etc.) unless a specific business unit requires it.
- Given the HCM domain, HR/hiring/scheduling-related agents are treated as elevated-risk by default (consistent with EU AI Act Annex III "employment" categorization).
- Model providers are a mix of hosted third-party APIs and possibly self-hosted models — governance must be model-agnostic, cannot assume access to model internals/weights.
- Teams building agents are internal and cooperative self-registrants, not adversarial. Detecting agents that deliberately evade the registry entirely ("shadow AI discovery") is a harder, separate problem — noted as a future enhancement, not solved here.
- Demo phase operates at small scale (one or two toy agents), synthetic/fake data only — no real employee PII, no production traffic.
- "Approval workflows," "exception management," and "monitoring dashboards" as full standalone subsystems are required by the original problem statement but explicitly deferred beyond this runtime+scheduled plan.

## 1.3 Risk taxonomy & exposed surface area

| Lifecycle stage          | Surface                                                       | Representative risks                                                                                                                               |
| ------------------------ | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data/training            | Data lakes, feature stores, fine-tuning pipelines, RLHF loops | Training on PII/PHI without consent, data poisoning, no lineage, cross-border transfer violations                                                  |
| Model/prompt design      | Prompt repos, system prompts, model registry                  | System-prompt leakage, unversioned prompt changes, no risk classification at design time                                                           |
| Retrieval/RAG            | Vector DBs, embeddings stores, document connectors            | Indirect prompt injection via poisoned documents, cross-tenant embedding leakage, stale/unauthorized data in the index                             |
| Tool/agent orchestration | Function-calling brokers, MCP servers, multi-agent frameworks | Over-permissioned service accounts, tool abuse for lateral movement, cross-agent injection propagation, irreversible actions with no approval gate |
| Inference/runtime        | API gateways, inference endpoints, third-party model APIs     | Prompt injection (direct/indirect), jailbreaks, PII/PHI/PCI leakage, denial-of-wallet, insecure output → downstream XSS/SSRF/SQLi                  |
| Supply chain             | Plugins, MCP servers, third-party models/fine-tunes           | Malicious/compromised plugin, poisoned fine-tune data, vendor DPA gaps, silent model deprecation/behavior change                                   |
| Human layer              | End users, prompt engineers, approvers, auditors              | Shadow AI, approval fatigue → rubber-stamping, secrets pasted into prompts                                                                         |
| Governance system itself | Its own scanners, dashboards, credential store                | High-value target (broad read access across every AI system), tamperable audit logs                                                                |

**Risk category rollup**: Security (injection/jailbreak/tool abuse/exfiltration) · Compliance/regulatory (risk-tier misclassification, data-subject rights, vendor DPA gaps) · Data privacy (PII/PHI/PCI leakage, retention, memorization) · Fairness/bias (disparate impact in consequential HR/hiring/scheduling decisions, explainability) · Operational (hallucination harm, unbounded autonomous actions, drift, no kill-switch) · Governance-process risk (shadow deployments, inconsistent scoring, stale exceptions, non-tamper-evident logs).

## 1.4 Things we want to fix

- No centralized inventory of AI apps/agents/models (shadow AI blind spot).
- No repeatable, automatable pre-launch testing for prompt injection / jailbreak resilience.
- Flat, non-risk-tiered review applied uniformly regardless of blast radius.
- Manual, spreadsheet-driven compliance checklists that don't scale past a handful of apps.
- Governance treated as a one-time launch gate instead of a continuous control loop.
- No unified audit trail linking policy version → evidence → approver → decision.
- No structured exception/waiver process with expiry and re-review.
- Fragmented ownership across security, privacy/legal, and AI/ML platform teams.
- Slow, opaque approval cycles that incentivize bypassing governance.

## 1.5 Anti-goals — things we don't want to happen

- The platform becoming the bottleneck that drives teams into shadow AI.
- Checkbox compliance that certifies static config but ignores actual runtime behavior.
- The governance agent itself becoming an attack vector (it needs broad read access across every AI system — must not become a privilege-escalation path).
- Alert fatigue from noisy false positives burying real findings.
- Single point of failure / single-team bottleneck from over-centralization.
- Rigid, hardcoded policy that can't track evolving regulation or new architectural patterns (agentic tool use, MCP, multi-agent).
- Black-box risk scoring — unreviewable automated approve/block decisions with no explanation.
- Mutable/tamperable audit logs.
- Uniform treatment regardless of blast radius.
- Governance bolted on post-deployment instead of integrated into the SDLC.

## 1.6 Runtime Observability

Inline, on the critical path of a live request/action. Bounded-latency decisions (block/allow/redact/escalate) _before_ the effect happens.

### 1.6.1 Prompt injection (direct + indirect)

- **Scenarios**: direct adversarial instructions from the user; indirect injection via tool-retrieved content (web page, email, doc) that the model treats as data but which contains instructions — higher blast radius since the attacker never talks to the system directly.
- **Approach/tradeoffs**: tiered stack — (a) fast regex/heuristic/signature blocklist, near-zero latency, high false-negative rate on novel attacks; (b) semantic similarity to known patterns, moderate cost; (c) LLM-as-judge on input _and_ on tool-result content before it re-enters context, highest accuracy/cost. Tier the _agent's_ risk level, not the message, to control cost: low-risk agents get (a) only, high-risk agents get all three with a hard latency budget and fail-closed on timeout.
- **Eval metrics**: precision/recall against a labeled, continuously updated corpus; false-positive rate (adoption killer); added p95/p99 latency; recall specifically on indirect injection; time from new attack pattern discovered → deployed detection.

### 1.6.2 Agent chains / jailbreak

- **Scenarios**: (a) conversational "crescendo" jailbreaks that erode guardrails across turns — invisible if scored per-message; (b) cross-agent propagation — a compromised/hallucinated sub-agent output becomes trusted input to the next agent (confused-deputy pattern).
- **Approach/tradeoffs**: rolling session-level risk score (not just per-message) for (a); treat inter-agent messages as untrusted input requiring the same scrutiny as external input for (b). Costs more state (session/trace store keyed by conversation + agent-chain ID) than a stateless per-call gateway.
- **Eval metrics**: jailbreak success rate on a standing red-team benchmark (re-run on every model/prompt version); escalation depth before detection; session-risk-score calibration.
- **Design note — the missing third tier**: for multi-step agents you often can't block mid-generation, but you _can_ gate the transition to the next hop/tool-call/agent handoff. Treat this **inter-step gating** as a first-class checkpoint distinct from both pure-runtime (per-token) and pure-scheduled (batch) enforcement.

### 1.6.3 Tool-call access privilege

- **Scenarios**: over-scoped service identity (privilege creep); authorized for a tool class but not the specific resource/parameter; chaining individually-benign tool calls into a harmful composite action (read PII + send-external-email = exfiltration).
- **Approach/tradeoffs**: fail-closed always, regardless of agent risk tier — this gates real-world side effects. Classic Policy Decision Point/Policy Enforcement Point pattern: every tool call evaluated against actor identity + tool + resource + parameters + recent call history _before_ execution. Tradeoff: becomes a hard synchronous dependency in every agent's execution path — must be highly available or every tool-using agent goes down with it.
- **Eval metrics**: 100% tool-call coverage (hard invariant); false-deny rate; mean policy-decision latency; caught composite-action attempts; time-to-propagate a permission change.

### 1.6.4 Response validation against compliance

- **Scenarios**: PII/PHI/PCI in the completion (regurgitated or leaked from context); policy-violating content (bias, toxicity, unlicensed advice); hallucinated claims in a consequential HR/hiring decision; insecure output that becomes a downstream vulnerability if rendered/executed as-is.
- **Approach/tradeoffs**: layered filter — deterministic pattern matchers for structured PII/PCI (fast, high precision) + classifier for unstructured sensitive-content leakage + policy-rule engine mapped to the agent's risk tier. Aggressive redaction reduces usefulness; under-redaction is the failure being prevented — needs tier-specific thresholds.
- **Eval metrics**: PII leakage false-negative rate (critical); redaction precision; regulatory-rule coverage (% with automated checks vs. still manual); business-harm rate from hallucination in consequential decisions.

### 1.6.5 Runtime system placement

```
Caller -> [Input Guard] -> Orchestrator/Agent -> [Tool Guard / PEP] -> Tool Execution
                                  |  (inter-step gating on hop transitions)
                                  v
                          -> [Output Guard] -> Response -> Caller
```

- **Entry point**: gateway/proxy (or sidecar) in front of the orchestrator — hosts Input Guard and Output Guard.
- **Mid-flight point**: Tool Guard/PEP called inline by the orchestrator before every tool invocation — cannot sit behind an async proxy, must be in the call path.
- **Exit point**: every decision emits a structured event to the observability pipeline — the sole connective tissue to Part 2 (Scheduled). Runtime produces signal; it does not do its own long-term storage/analysis.

## 1.7 Scheduled Observability

Out-of-band, batch/async, triggered by cron or by event (registry webhook, CI/CD, runtime violation stream). No latency budget; value comes from breadth and feedback into policy/risk scores.

### 1.7.1 Onboarding / pre-deployment validation

- **Scenarios**: new agent registered without review (shadow AI); risk tier self-misdeclared; missing vendor DPA for the backing model; no owner/on-call assigned.
- **Approach/tradeoffs**: registration is a gate triggered by CI/CD or registry webhook — automated checks (tool-scope scan, data-source scan, vendor-contract lookup) before an agent reaches prod. Too strict recreates the shadow-AI failure mode; too lenient is checkbox theater. Mitigate by auto-approving low-tier agents that pass automated checks, escalating only ambiguous/high-risk ones.
- **Eval metrics**: onboarding cycle time (p50/p95); % auto-approved vs. escalated; defect-escape rate (things onboarding missed that runtime/audit later caught).

### 1.7.2 Usage & flag reporting

- **Scenarios**: no visibility into which agents are used, by whom, at what volume/cost; violation flags pile up unaggregated across hundreds of agents; anomalous usage spikes go unnoticed until the bill or the incident.
- **Approach/tradeoffs**: aggregate runtime's emitted events into a warehouse; trend dashboards (per-agent risk trend, org-wide violation heatmap, cost anomalies). Key design choice: what triggers a ticket vs. just a dashboard update — not every flag should page someone.
- **Eval metrics**: dashboard data freshness/lag; % agents with complete telemetry coverage; mean time from anomaly occurrence to ticket creation.

### 1.7.3 Version management

- **Scenarios**: model provider silently updates the underlying model with no re-review triggered; prompt template changed without governance review; an agent's approved risk assessment goes stale relative to its current running config.
- **Approach/tradeoffs**: tie to the model/prompt registry as source of truth; any diff (model version, prompt hash, tool-scope) auto-triggers a _scoped_ re-review, not full re-onboarding. Too granular = friction on every tweak; too coarse = meaningful drift slips through.
- **Eval metrics**: version-drift detection lag; % of changes that triggered appropriate re-review; rollback readiness.

### 1.7.4 Prompt auditing

- **Scenarios**: retrospective sampling to catch what runtime's latency-bounded checks missed; pattern-mining across an agent's history for systemic bias or repeated near-misses.
- **Approach/tradeoffs**: run the expensive checks here — full LLM-judge review, statistical bias/fairness analysis, cross-referencing flagged sessions against actual outcomes. Risk-tiered sampling rate (audit high-risk agents more) rather than 100% audit at scale.
- **Eval metrics**: sample coverage %; violation detection rate in audit that runtime missed (tells you if runtime thresholds are correctly calibrated); false-negative correction rate.

### 1.7.5 Additional scheduled jobs

- **Standing red-team suite**, re-run on every model/prompt/tool-scope diff (event-triggered, not purely clock-triggered) — direct link back to 1.6.2's jailbreak benchmark.
- **Entitlement/permission drift audit** — periodically re-verify each agent's actual tool/data scope still matches its approved risk assessment; catches quiet, cumulative privilege creep that no runtime check is positioned to see.
- **Exception/waiver expiry sweep** — sweep for waivers past their review date, force re-attestation or auto-escalate; directly addresses the "stale exceptions never revisited" anti-goal.

### 1.7.6 Scheduled system placement

- **Entry points**: CI/CD or registry webhook (onboarding, version-change triggers); cron scheduler (nightly/weekly batch jobs); event-bus consumer on runtime's violation-event stream.
- **Exit points**: dashboards; ticket creation for items needing human remediation; feedback into the risk-scoring engine (a finding moves an agent's risk tier, which changes runtime strictness for that agent — closing the loop back into Part 1); feedback into the approval workflow (a failed scheduled scan can block promotion of a new version to prod).

## 1.8 Cross-cutting integration

```
Runtime Guards --emit events--> Observability Pipeline --> Scheduled Jobs
      ^                                                          |
      |                                                          v
      +---- risk-tier / policy updates ---- Risk Scoring Engine <+
```

External systems both parts integrate with: IAM/SSO (actor identity for the Tool Guard/PEP) · model/prompt registry (version-management source of truth) · CI/CD (onboarding and version-change triggers) · SIEM (injection/jailbreak attempts are security events, forwarded there too) · ticketing (exception tracking, remediation) · GRC platform, if present (natural consumer of scheduled audit reports for regulator-facing evidence).

## 1.9 Future enhancements (explicitly out of scope for now)

- Full approval-workflow engine (multi-stage sign-off, delegation, SLA tracking).
- Full exception-management subsystem (self-service waiver requests, approval chains, automated expiry enforcement at scale).
- Production-grade monitoring dashboards / GRC reporting integration.
- ML-based (vs. rubric-based) risk scoring model.
- Shadow-AI discovery (detecting agents that were never registered at all).
- Cross-agent/multi-agent orchestration risk at production scale.

---

# Part 2 — Demo Plan

## 2.1 Philosophy

Don't attempt to demo the whole governance platform at once — nobody believes an end-to-end enterprise suite in a demo, and building toward full scope first means showing nothing for weeks. Instead: **one small toy agent, three views over it, real detection logic where it matters, everything else mocked or stubbed.**

## 2.2 Shared toy agent (built once, reused across all 3 cases)

**"HR Assistant"** with 3 tools:

- `lookup_employee(id)` — returns fake PII (name, salary, SSN-lite fake data)
- `update_pto_balance(id, days)` — a write action
- `send_email(to, body)` — an external-effect action

One agent definition, reused by all three demo cases below — avoids rebuilding fake data/tool definitions three times, and lets the demo tell one continuous story (register → run → attack → drift) instead of three disconnected vignettes.

**Data model needed** (all synthetic, no real employee data):

- A small fake employee table (5–10 rows: id, name, salary, SSN-lite, PTO balance).
- A tiny "knowledge base" of 4–5 fake documents for Case 2 (PTO policy, benefits FAQ, a compensation-bands doc, and one poisoned "meeting notes" doc containing a hidden injected instruction).
- A JSON-driven attack/prompt corpus (see 2.5 — kept external to code for easy iteration).

## 2.3 What's real vs. mocked (least-effort principle)

| Component                                          | Real or mocked                                                                  | Why                                                                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Injection/jailbreak detection                      | **Real** (actual LLM-judge or classifier call)                                  | The credibility moment — a scripted "detected!" with nothing behind it gets called out immediately         |
| Tool-call PEP/policy check                         | **Real**, simple hardcoded rule set (not a full policy DSL)                     | Shows the enforcement-point concept without building OPA-grade infra                                       |
| PII leakage detection                              | **Real**, deterministic regex/pattern matcher only (skip ML)                    | Cheap to build, still genuinely catches SSN/salary leakage                                                 |
| IAM/SSO, SIEM, ticketing integrations              | **Mocked** — a log line or fake webhook payload shown on screen                 | The point is showing _where_ the integration point is, not building it                                     |
| Risk scoring model                                 | **Mocked as a simple weighted formula**, not ML                                 | Believable, explainable, and matches the "no black-box scoring" principle                                  |
| RAG retrieval                                      | **Mocked** — JSON documents + basic keyword/embedding lookup, no real vector DB | Demonstrates the concept identically to production RAG infra at near-zero build cost                       |
| Scheduled jobs (red-team suite, entitlement sweep) | **Real logic, manually triggered** instead of a real cron                       | A "Run nightly audit now" button is more demo-friendly than waiting for 2am, and proves the mechanism live |

## 2.4 The 3 demo cases

### Case 1 — UI for prompt injection + guardrails

- **Layout**: chat window + a persistent "Guardrail Trace" side panel (intentionally more verbose than a shipped product would be — showing the _why_ is the point). Shows per message: which layer fired, the score/signal, the decision, latency added. A toggle to disable guardrails, for before/after replay of the same attack.
- **Script**: (1) benign question → passes instantly, proves no false-positive friction; (2) blunt direct injection → caught by the fast heuristic layer; (3) subtler injection missed by heuristics but caught by the semantic/LLM-judge layer → justifies the tiered stack.

### Case 2 — RAG retrieval + compliance validation

- **Layout**: adds a "Sources" panel showing the actual retrieved chunk content verbatim before it's summarized — the audience needs to _see_ the poisoned text sitting in an otherwise-mundane document.
- **Script**: (1) clean question → clean doc retrieved → clean answer; (2) question that legitimately retrieves the compensation doc → output guard redacts the salary/SSN live; (3) question that retrieves the poisoned "meeting notes" doc → injected instruction caught at the _output_ stage specifically, called out as having slipped past the Case 1 _input_ guard because the attack arrived via retrieval, not the user's own prompt — this is the moment that justifies multiple guard points.

### Case 3 — Agent onboarding checks + versioning

- **Layout**: "Agent Registry" view — a registration form that on submit shows a live checklist (✅/⚠️/❌ per automated check) plus a computed risk tier and _reasoning_, not just a verdict; a "Version History" tab showing prior versions as a timeline with diffs and which changes auto-triggered a re-review.
- **Script**: (1) register the HR Assistant → `send_email` + PII access pushes it to Medium/High tier → escalated for human approval rather than auto-approved; (2) approve → agent goes live, becomes the actual agent used in Cases 1 and 2; (3) edit its tool scope or system prompt later → diff detected automatically → scoped re-review triggered (not full re-onboarding).

## 2.5 Configurability — keep everything that changes often out of code

To make scenarios cheap to add/tweak without touching application logic:

- **Attack/prompt corpus** as an external JSON/YAML file: `{id, category (direct-injection/indirect-injection/jailbreak/pii-probe), prompt text, expected_outcome}`. Adding a new attack for a future demo = adding a row, not writing code.
- **Knowledge base documents** (Case 2) as plain files in a folder, including the poisoned one — swapping in a new injection scenario means dropping in a new file.
- **Onboarding checklist rubric** (Case 3) as a declarative rule list: `{check_name, condition, weight, tier_impact}` — new checks or reweighting doesn't touch the scoring engine's code.
- **Risk-tier thresholds** and **guard latency budgets** as config values, not hardcoded — lets you demo the risk-tiering story (same attack, different agent, different strictness) by editing config rather than code.
- **Fake employee dataset** as a single seed file — regenerating or resizing the demo dataset is a data change, not a code change.

## 2.6 Build order (least effort, most convincing first)

1. **v0 — Storyboard/mock only** (slides or a static clickable mock, no backend): validate the narrative with stakeholders before writing detection logic.
2. **v1 — Case 1 real**: Input/Output guard sandwich around the HR Assistant, canned attack set, live trace panel.
3. **v2 — Case 3 real**: registration form + rubric-based checklist + version diffing, wired to gate the same agent used in v1.
4. **v3 — Case 2 real**: add the mocked RAG layer and the poisoned document, reusing the guard stack already built in v1.
5. **v4 — Scheduled layer**: manually-triggered "run nightly audit" / "run red-team suite" buttons layered on top of the same agent, closing the loop back to the risk score shown in Case 3.

## 2.7 Demo narrative order (for delivery, distinct from build order)

Case 3 (register/onboard, establish declared scope + risk tier) → Case 1 (run normally, then attacked directly, guardrails catch it) → Case 2 (harder indirect path via RAG) → back to Case 3 (change something, show version drift catching it) → scheduled sweep (show an exception expiring or a red-team regression after a version change).
