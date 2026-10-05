# DriftGuard — Agentic AIDevOps Project Plan

> **DriftGuard: An Autonomous Multi-Agent System for Cross-Artifact Consistency Analysis, Sandboxed Self-Healing, and Transparent Pull Request Actuation**
>
> An intelligent AIDevOps agentic system combining incremental git delta perception, Tree-sitter universal AST parsing, free open-source Sourcegraph SCIP symbol intelligence, OmniRoute dynamic model routing, and ephemeral Docker/Kubernetes sandboxed verification to automatically detect and repair software inconsistencies with verifiable reviewer transparency.

---

## 1. Project Overview

DriftGuard is an autonomous **AIDevOps system for detecting, verifying, and self-healing inconsistencies across heterogeneous software artifacts**—including source code, unit tests, documentation, API specifications (OpenAPI/Swagger), package dependencies, Dockerfiles, and CI/CD configurations.

Designed specifically as an **Intelligent Developer Tools (AIDevOps) systems project**, DriftGuard bridges the gap between passive static linters and autonomous agentic maintenance. Operating both as a **GitHub Action** in continuous integration pipelines and as a **Local Developer CLI**, the system:

-   monitors repository branches, triggering automatically upon code changes (push/PR) or manually via CLI on any targeted branch;
-   perceives incremental git deltas and maps cross-artifact dependencies using **Tree-sitter** universal AST parsing and **Sourcegraph SCIP** (100% free and open-source) cross-file symbol intelligence;
-   autonomously detects the project's technology stack (e.g., Next.js frontend + Python backend) and infers necessary build, lint, and test validation commands;
-   accepts explicit repository policies and overrides via a declarative `.driftguard.yml` configuration;
-   isolates repairs in ephemeral **Docker / Kubernetes sandboxed environments** away from production, executing real builds and test suites;
-   engages in an iterative, bounded self-correction loop where compiler and test errors guide automated patch refinement;
-   synthesizes an auditable, transparent **GitHub Pull Request (PR)** containing surgical fixes, verification proofs, and an explainable Chain of Thought (CoT) trace for human reviewer inspection;
-   dynamically routes model inferences through the **OmniRoute** pooled gateway to balance reasoning quality, latency, and token efficiency.

The project strictly separates:

1.  **Application / CI Layer** — GitHub Action runner, Local CLI, `.driftguard.yml` configuration parser, GitHub REST/GraphQL PR actuator, and developer review interface.
2.  **Agentic Systems & AIDevOps Layer** — Multi-agent orchestration, Tree-sitter multi-language AST extraction, open-source Sourcegraph SCIP symbol graphs, OmniRoute model routing, sandboxed container runtime (Docker / Kubernetes), and transparent reasoning telemetry.

---

## 2. Project Motivation & Industrial Context

Modern software engineering repositories are multi-artifact ecosystems. High-velocity feature development inevitably introduces subtle cross-artifact "drift":
- A developer updates an internal REST API endpoint but forgets to update the OpenAPI specification or the markdown documentation.
- A new third-party library is imported in application code, but the lockfile or `requirements.txt` / `package.json` is not updated, causing downstream deployment failures.
- A function signature is modified, rendering existing unit tests obsolete or causing silent mock failures.
- A Dockerfile or GitHub Action workflow continues to reference deprecated file paths, legacy runtime flags, or invalid build targets.

Existing static analysis tools (linters, formatters) operate within single-language silos and cannot reason across disparate artifact boundaries (e.g., contrasting markdown prose against Python route decorators). Conversely, purely conversational LLMs produce hallucinated "fixes" that fail to compile or break peripheral tests.

DriftGuard resolves this through an **AIDevOps Closed-Loop Paradigm**:
$$\text{Detect Drift} \longrightarrow \text{Ground in Tree-sitter \& SCIP} \longrightarrow \text{Synthesize Patch} \longrightarrow \text{Sandboxed Compilation} \longrightarrow \text{Iterative Repair} \longrightarrow \text{Transparent PR}$$

---

## 3. Project Goals

### Primary Goal
Design, implement, and benchmark **DriftGuard: an autonomous, evidence-grounded, sandboxed self-healing AIDevOps platform** that ingests repository branch changes, detects multi-artifact inconsistencies, verifies fixes within ephemeral Docker/Kubernetes sandboxes, and delivers verified Pull Requests with transparent Chain-of-Thought execution traces.

### Secondary Goals
- Demonstrate hierarchical multi-agent orchestration for software verification.
- Incorporate **Tree-sitter** for blazing-fast, universal AST and concrete syntax tree parsing across 40+ programming languages.
- Integrate **Sourcegraph SCIP** (free, open-source indexers) for precise, zero-cost cross-file symbol resolution and reference mapping without paid enterprise subscriptions.
- Deploy isolated, ephemeral **Docker and Kubernetes sandboxes** to execute real project builds (`npm run build`, `pytest`, `cargo test`) without polluting the host or production environments.
- Provide a declarative `.driftguard.yml` specification governing build rules, branch filters, sandbox resource limits, and retry budgets.
- Implement an iterative, compiler-driven reflection loop with configurable retry bounds to prevent infinite repair loops.
- Route LLM reasoning tasks dynamically via the **OmniRoute** pooled gateway across heterogeneous model families.
- Guarantee anti-hallucination by requiring verifiable verbatim citations and line-anchored claims for every identified drift.
- Emit structured execution traces and collapsible Chain of Thought (CoT) summaries directly into GitHub Pull Request descriptions.
- Conduct a rigorous scientific evaluation across 40+ real-world repositories, quantifying detection accuracy, repair convergence, and human reviewer acceptance.

---

## 4. Scope

### 4.1 In Scope

- **Trigger Mechanisms**:
  - Automated invocation via GitHub Actions on push or pull-request events targeting designated branches.
  - Manual on-demand invocation via local CLI (`driftguard analyze --branch <name>`).
- **Artifact Taxonomy**:
  - Source code, unit/integration tests, documentation (Markdown/RST), API specs (OpenAPI/Swagger), package dependencies (`package.json`, `requirements.txt`, `Cargo.toml`, `go.mod`), CI/CD workflows (`.github/workflows/*.yml`), Dockerfiles, and runtime configuration (`.env.example`, `config.yaml`).
- **Deterministic Multi-Language Code Parsing**:
  - Incremental parsing using Tree-sitter grammars (Python, TypeScript, Go, Rust, Java, YAML).
  - Cross-file symbol reference mapping via local open-source SCIP indexers (`scip-python`, `scip-typescript`, `scip-go`).
- **Autonomous Stack Detection**:
  - Automatic identification of monorepos, polyglot environments, and single-stack projects (e.g., Next.js, FastAPI, Django, Go Gin, Rust Actix).
  - Autonomous heuristic deduction of build, lint, and test scripts.
- **Sandboxed Execution**:
  - Ephemeral container execution (Docker containers locally; Kubernetes Pods/Jobs in cloud runners) ensuring zero environment pollution and total isolation.
  - Live capture of build stdout, stderr, exit codes, and test assertions.
- **Bounded Iterative Repair**:
  - Compiler-in-the-loop repair feedback: Feeding compiler/test error logs back to the LLM to iteratively refine code patches up to `.driftguard.yml` retry limits.
- **Actuation & Transparency**:
  - Automated creation of git fix branches and submission of Pull Requests via GitHub API.
  - Rich PR descriptions featuring collapsible CoT traces, verbatim evidence quotes, and sandbox validation certificates.
- **Evaluation & Benchmarking**:
  - Evaluation against curated synthetic and natural drift benchmarks across Python, TypeScript, Go, and polyglot repositories.

### 4.2 Out of Scope

- **Paid SaaS Tooling**: No paid Sourcegraph Enterprise, Cody Pro, or proprietary closed-source code intelligence subscriptions. All code indexing strictly uses free open-source tools.
- **Blind Production Merging**: DriftGuard will *never* push directly to protected production branches (`main`/`master`). Its actuation ceiling is strictly a **Pull Request** requiring human peer review.
- **Arbitrary Whole-Project Rewrites**: DriftGuard operates on surgical, Karpathy-style minimal diffs. Broad architectural refactorings without explicit drift provocation are out of scope.
- **Exotic Air-Gapped Tooling**: Sandboxed builds rely on standard containerized runtimes (Node, Python, Go, Rust, Java). Exotic proprietary build environments requiring physical hardware dongles are out of scope.

---

## 5. Core Multi-Agent Architecture

DriftGuard decomposes software maintenance into specialized agents operating over a shared blackboard state:

| Agent | Responsibility | Primary AIDevOps Concept |
| :--- | :--- | :--- |
| **Trigger & Delta Agent** | Ingests branch events (push/PR/CLI), identifies modified files, and computes incremental git deltas. | Perception, Git diff parsing, webhook ingestion |
| **Stack Detector & Policy Agent** | Detects repository frameworks (e.g. Next.js + FastAPI), parses `.driftguard.yml`, and formulates baseline build/test commands. | Environment discovery, policy enforcement |
| **Tree-sitter & SCIP Intelligence Agent** | Generates ASTs via **Tree-sitter** and queries local **SCIP** indices to establish cross-artifact dependency and call edges. | AST parsing, symbol resolution, cross-file reference tracking |
| **Drift Auditor Agent** | Analyzes candidate artifact pairs, evaluates semantic and structural contracts, and confirms inconsistencies with verbatim quotes. | ReAct reasoning, contract verification, anti-hallucination |
| **Sandboxed Repair Engineer** | Generates surgical patches, provisions Docker/Kubernetes ephemeral sandboxes, executes builds/tests, and captures compiler errors. | Action execution, isolated container orchestration, patch synthesis |
| **Reflection & Convergence Agent** | Evaluates sandbox build failures, updates error context, and manages the bounded retry loop against `.driftguard.yml` limits. | Self-critique, reflection, error-guided iteration |
| **PR Actuator & Reviewer Trace Agent** | Formats git diffs, commits to a fix branch, issues the GitHub PR, and formats transparent CoT reviewer traces. | Actuation, GitHub API, transparent explainability |

---

## 6. System Architecture

The following diagram illustrates the complete DriftGuard architecture—spanning triggers, multi-agent reasoning, code intelligence, sandboxed container execution, and pull request actuation.

``` mermaid
---
config:
  layout: elk
---
flowchart TB
    subgraph Trigger_Layer["Perception & Trigger Layer"]
        GH_EVENT["GitHub Webhook Event\n(push / pull_request)"]
        CLI_INPUT["Developer Local CLI\n(driftguard analyze --branch)"]
        DELTA_AGENT["Trigger & Delta Agent\n(Git Diff & Impact Scanner)"]

        GH_EVENT --> DELTA_AGENT
        CLI_INPUT --> DELTA_AGENT
    end

    subgraph Intelligence_and_Tools["Free Open-Source Code Intelligence & Gateway"]
        TREESITTER["Tree-sitter Multi-Language Engine\n(Fast AST & S-Expression Queries)"]
        SCIP["Sourcegraph SCIP Local Indexers\n(Free/OSS Cross-File Symbol Graphs)"]
        OMNIROUTE["OmniRoute Model Gateway\n(http://localhost:20128)"]
        CONFIG[(".driftguard.yml\n(Policy & Build Overrides)")]
    end

    subgraph Multi_Agent_Core["DriftGuard Multi-Agent Reasoning Core"]
        STACK_AGENT["Stack Detector & Policy Agent"]
        AUDITOR_AGENT["Drift Auditor Agent"]
        REPAIR_AGENT["Sandboxed Repair Engineer"]
        REFLECT_AGENT["Reflection & Convergence Agent"]
        PR_AGENT["PR Actuator & Reviewer Trace Agent"]

        BB[("Shared Blackboard Session State\n(Deltas, Claims, Patches, Logs)")]
    end

    subgraph Sandboxed_Runtime["Isolated Ephemeral Sandboxed Verification Engine"]
        RUNNER{"Execution Target\n(Local vs Cloud CI)"}
        DOCKER["Docker Engine\n(Ephemeral Container)"]
        K8S["Kubernetes Cluster\n(Ephemeral Job / Pod)"]
        SANDBOX_EXEC["Build & Test Matrix Runner\n(next build / pytest / cargo)"]
        LOGS["Compiler & Test Failure Logs\n(stdout / stderr / exit code)"]

        RUNNER -->|Local CLI Runner| DOCKER
        RUNNER -->|Cloud CI/CD Runner| K8S
        DOCKER --> SANDBOX_EXEC
        K8S --> SANDBOX_EXEC
        SANDBOX_EXEC --> LOGS
    end

    subgraph Output_Actuation["Reviewer Transparency & Actuation Layer"]
        GIT_COMMIT["Surgical Git Branch & Commit"]
        GH_PR["GitHub Pull Request"]
        PR_TRACE["Collapsible CoT Reviewer Trace HUD\n(Verbatim Quotes & Build Certificate)"]

        GIT_COMMIT --> GH_PR
        PR_TRACE --> GH_PR
    end

    %% Wiring Perception to Core
    DELTA_AGENT -->|Changed Files & Diffs| BB
    BB <--> STACK_AGENT
    STACK_AGENT <--> CONFIG

    %% Wiring Code Intelligence
    BB <--> AUDITOR_AGENT
    AUDITOR_AGENT <--> TREESITTER
    AUDITOR_AGENT <--> SCIP
    AUDITOR_AGENT <--> OMNIROUTE

    %% Wiring Sandboxed Repair Loop
    AUDITOR_AGENT -->|Confirmed Drift| REPAIR_AGENT
    REPAIR_AGENT <--> OMNIROUTE
    REPAIR_AGENT -->|Dispatch Candidate Patch| RUNNER
    LOGS -->|Execution Outcome| REFLECT_AGENT
    REFLECT_AGENT -->|Build Passed: Verified| PR_AGENT
    REFLECT_AGENT -->|Build Failed: Retry < Max| REPAIR_AGENT
    REFLECT_AGENT -->|Build Failed: Max Retries Exceeded| PR_AGENT

    %% Wiring Output Actuation
    PR_AGENT --> GIT_COMMIT
    PR_AGENT --> PR_TRACE
```

---

## 7. Why This Is Agentic

DriftGuard is not a static script. It operates within a **goal-driven, partially observable, dynamic, and continuous software environment**:

| Property | DriftGuard AIDevOps Interpretation |
| :--- | :--- |
| **Observability** | **Partially Observable** — The system cannot inspect runtime production memory or dynamic user traffic; it perceives the software state strictly through static code, AST graphs, build logs, and configuration files. |
| **Determinism** | **Stochastic & Uncertain** — While compiler syntax checks are deterministic, natural language doc claims, semantic intent, and LLM patch generation are stochastic. |
| **Time Structure** | **Sequential** — A repair applied to `package.json` directly affects the outcome of subsequent `next build` steps and downstream test runs. |
| **Dynamics** | **Dynamic** — Feature branches evolve as team members push concurrent commits; the environment changes between workflow invocations. |
| **State Space** | **Continuous and Discrete** — Multi-file source code trees, AST nodes, compiler exit codes, and dependency constraint trees represent a massive state space. |
| **Interaction** | **Human-in-the-Loop** — The agent proposes changes and provides verifiable rationales; the human developer retains ultimate merge authority. |
| **Goal Structure** | **Explicit Multi-Objective** — Eliminate artifact contradictions, achieve 100% sandboxed build/test pass rate, minimize line diff churn, and strictly honor `.driftguard.yml` limits. |

---

## 8. PEAS Specification

| Component | DriftGuard AIDevOps Definition |
| :--- | :--- |
| **Performance Measures** | - Inconsistency detection Precision, Recall, and F1-score.<br>- Sandboxed build & test pass rate (100% required for PR creation).<br>- Patch minimalism (ratio of changed lines to total file length).<br>- Repair convergence speed (number of iterations $\le \text{max\_retries}$).<br>- Reviewer acceptance rate (merged PR percentage).<br>- End-to-end execution latency ($< 180\text{s}$ per standard CI run). |
| **Environment** | - Git repositories (GitHub hosted or local workspaces).<br>- Multi-language file systems (Python, TypeScript, Go, Rust, Docker, YAML).<br>- Ephemeral Docker containers and Kubernetes clusters.<br>- GitHub Actions CI/CD runtime. |
| **Actuators** | - Git branch creation and surgical commit dispatch.<br>- GitHub REST/GraphQL API for Pull Request creation and inline reviews.<br>- Ephemeral container lifecycle controllers (`docker run` / `kubectl create job`).<br>- Build/test command executor.<br>- Transparent Markdown CoT report generator. |
| **Sensors / Percepts** | - Git delta streams (commit shas, diff hunks, modified file paths).<br>- **Tree-sitter** AST syntax trees and S-expression queries.<br>- **Sourcegraph SCIP** local symbol definition & reference maps.<br>- Declarative repository policies (`.driftguard.yml`).<br>- Sandbox process exit codes, compiler stdout/stderr streams, and test failure traces. |

---

## 9. Agent Communication Architecture

DriftGuard incorporates multiple communication patterns tailored to specific workflow phases:

### 9.1 Sequential Pipeline
Used during the initial discovery and verification phase where strict data dependencies exist:
```
Git Delta Ingestion ──> Stack Detection ──> Tree-sitter & SCIP Edge Mapping ──> Drift Auditing
```

### 9.2 Parallel / Broadcast Pattern
Used when analyzing independent candidate artifact pairs concurrently across multiple worker processes:
``` mermaid
flowchart TD
    M["Drift Auditor Manager"] --> A1["Audit Pair: API Spec ↔ Route Controller"]
    M --> A2["Audit Pair: README ↔ CLI Arguments"]
    M --> A3["Audit Pair: package.json ↔ Import Statements"]

    A1 --> AGG["Candidate Aggregator & Deduplicator"]
    A2 --> AGG
    A3 --> AGG
```

### 9.3 Shared Blackboard Architecture
Agents communicate state asynchronously during the repair loop via a structured, in-memory blackboard session state:
``` text
blackboard_state:
  git_context:
    target_branch: "feature/auth-v2"
    base_branch: "main"
    changed_files: ["src/auth.ts", "package.json", "docs/auth.md"]
  detected_stack:
    primary_language: "TypeScript"
    frameworks: ["Next.js", "Express"]
    inferred_build_cmd: "npm run build"
    inferred_test_cmd: "npm test"
  active_drifts:
    - drift_id: "drift-001"
      category: "dependency_vs_code"
      verbatim_evidence_1: "import { jwtVerify } from 'jose';"
      verbatim_evidence_2: "dependencies: { 'jsonwebtoken': '^9.0.0' }"
      suggested_fix: "Add jose to package.json or revert import"
  sandbox_state:
    current_attempt: 1
    max_retries: 3
    last_exit_code: 1
    compiler_error_context: "TS2307: Cannot find module 'jose' or its corresponding type declarations."
```

### 9.4 Hierarchical Coordination
The **Root AIDevOps Manager** supervises sub-agents, dispatches tasks, enforces timeout budgets, and halts execution if `.driftguard.yml` limits are reached.

---

## 10. Workflow Architecture

### 10.1 Drift Detection & Incremental Delta Workflow

``` mermaid
flowchart TD
    A["Branch Push / PR Event Triggered"] --> B["Extract Changed Files & Git Diff"]
    B --> C{"Check .driftguard.yml Exclusions"}
    C -->|Ignored Path| Z["Halt / Skip Analysis"]
    C -->|Active Target| D["Stack Detector: Identify Frameworks & Build Tools"]
    D --> E["Query Tree-sitter AST & Local SCIP for Related Artifacts"]
    E --> F["Generate Candidate Artifact Pairs"]
    F --> G["Static Pre-Screen: Check Existence & Basic Contracts"]
    G -->|Trivially Consistent| H["Log No Drift"]
    G -->|Ambiguous / Contract Mismatch| I["Drift Auditor LLM Reasoning (OmniRoute)"]
    I --> J["Evidence Verifier: Assert Verbatim Quotes in Code"]
    J -->|Verification Failed| K["Discard Hallucinated Finding"]
    J -->|Verification Passed| L["Register Confirmed Inconsistency on Blackboard"]
    L --> M["Trigger Sandboxed Self-Healing Workflow"]
```

### 10.2 Sandboxed Self-Healing & Iterative Patch Loop

``` mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (PR Reviewer)
    participant Core as DriftGuard Core
    participant Repair as Sandboxed Repair Engineer
    participant Model as OmniRoute Gateway
    participant Box as Ephemeral Sandbox (Docker/K8s)
    participant Git as GitHub Actuator

    Core->>Repair: Dispatch Confirmed Drift + AST Context
    loop Up to max_repair_attempts (from .driftguard.yml)
        Repair->>Model: Request Minimal Surgical Patch (with Error Context)
        Model-->>Repair: Proposed Patch (Unified Diff)
        Repair->>Box: Spin Up Ephemeral Container & Apply Patch
        Repair->>Box: Execute Build & Test Suite (e.g. npm run build)
        Box-->>Repair: Return Exit Code, stdout, stderr

        alt Build & Test Exit Code == 0 (PASS)
            Repair->>Core: Patch Verified (Passing Build)
            note over Repair,Core: Convergence Achieved
        else Build Failed (Exit Code != 0)
            Repair->>Repair: Extract Compiler / Linter Error Traces
            note over Repair: Increment Attempt Counter
        end
    end

    alt Verified Patch Available
        Core->>Git: Create Fix Branch (driftguard/fix-branch)
        Git->>Git: Commit Surgical Changes
        Git->>Dev: Submit Pull Request with Transparent CoT Trace
    else Retries Exhausted without Passing Build
        Core->>Git: Submit Advisory Review / PR Comment (Highlight Drift + Sandbox Failure Trace)
    end
```

---

## 11. Event-Driven Architecture

DriftGuard reacts to asynchronous system events across the AIDevOps lifecycle without blocking the host developer environment:

``` mermaid
---
config:
  layout: dagre
---
flowchart BT
    subgraph Git_Events["Source Control & Trigger Events"]
        E1["BranchPushedEvent"]
        E2["PullRequestOpenedEvent"]
        E3["ManualCLITriggerEvent"]
    end

    subgraph Sandbox_Events["Sandboxed Runtime Events"]
        E4["SandboxProvisionedEvent"]
        E5["BuildExecutionFailedEvent"]
        E6["BuildExecutionPassedEvent"]
        E7["MaxRetriesExceededEvent"]
    end

    subgraph Actuation_Events["Reviewer & Actuation Events"]
        E8["PatchVerifiedEvent"]
        E9["PullRequestCreatedEvent"]
        E10["ReviewerFeedbackReceivedEvent"]
    end

    E1 & E2 & E3 --> DISPATCH["AIDevOps Event Dispatcher"]
    DISPATCH --> ANALYZE["Trigger Incremental Drift Analysis"]

    E4 --> LOG["Stream Sandbox Telemetry"]
    E5 --> RETRY["Trigger Compiler-Feedback Repair Loop"]
    E6 --> E8
    E7 --> ESCALATE["Emit Non-Blocking Reviewer Advisory"]

    E8 --> E9
    E9 --> NOTIFY["Notify GitHub PR Reviewers"]
```

---

## 12. AIDevOps Foundation & Implementation Strategy

DriftGuard is engineered specifically for the **Intelligent Developer Tools (AIDevOps)** paradigm. Rather than recreating standard software components from scratch or relying on paid services, it maximizes the use of production-grade, 100% free open-source tools:

1. **Deterministic Multi-Language ASTs via Tree-sitter**:
   - Replaces bespoke Python parsers with **Tree-sitter** (MIT-licensed).
   - Operates across Python, TypeScript, Go, Rust, Java, and YAML with sub-millisecond parsing and resilient S-expression querying.
2. **Cross-File Symbol Resolution via Free Sourcegraph SCIP**:
   - Uses **Sourcegraph's open-source SCIP indexers** (`scip-python`, `scip-typescript`, `scip-go`).
   - Runs **100% locally and offline** without requiring any paid Sourcegraph Enterprise subscription or API token.
   - Extracts precise cross-file definition and reference graphs (e.g. matching an API definition to all calling tests and route consumers).
3. **Pooled Model Routing via OmniRoute**:
   - Connects directly to the local **OmniRoute** gateway (`http://localhost:20128`), dynamically routing tasks across pooled free providers (GitHub, Antigravity, Gemini, Groq, Trae) based on task complexity.
4. **Isolated Ephemeral Environments via Docker & Kubernetes**:
   - Docker executes rapid local container builds during developer CLI runs.
   - Kubernetes executes isolated Pods/Jobs in enterprise CI/CD environments, preventing noisy-neighbor contention and guaranteeing clean build states.
5. **Dual Interface**:
   - Native **GitHub Action** container executing headlessly in cloud CI.
   - Standalone **Local CLI** (`driftguard`) for pre-commit and local branch verification.

---

## 13. Execution Model

``` mermaid
sequenceDiagram
    participant GH as GitHub CI / CLI
    participant Mgr as DriftGuard Coordinator
    participant Ext as Tree-sitter & SCIP
    participant Aud as Drift Auditor
    participant Sand as Docker / K8s Sandbox
    participant Route as OmniRoute Gateway
    participant PR as GitHub API

    GH->>Mgr: Ingest Branch Trigger & .driftguard.yml
    Mgr->>Ext: Parse ASTs & Query Symbol References
    Ext-->>Mgr: Return Cross-Artifact Dependency Edges
    Mgr->>Aud: Evaluate Inconsistencies
    Aud->>Route: Request Drift Verification
    Route-->>Aud: Return Grounded Contradiction Claims
    Aud-->>Mgr: Register Confirmed Drift List
    Mgr->>Sand: Spin Up Ephemeral Container
    loop Self-Healing Loop
        Mgr->>Route: Generate Minimal Unified Diff
        Route-->>Mgr: Candidate Patch
        Mgr->>Sand: Apply Patch & Run Build Command
        Sand-->>Mgr: Return Exit Code & Compiler Stderr
    end
    Mgr->>PR: Push Branch & Open Pull Request with Transparent CoT
    PR-->>GH: PR Available for Human Review
```

---

## 14. Reasoning & Diagnosis Strategy

| Stage | Reasoning Paradigm | AIDevOps Objective |
| :--- | :--- | :--- |
| **Stack & Rule Discovery** | Rule-Based Heuristic Inference | Determine whether to invoke `npm run build`, `pytest`, `cargo build`, or `go test` without user manual input. |
| **Cross-Artifact Auditing** | **ReAct** (Reason + Act) via Tools | Query Tree-sitter AST nodes, verify SCIP symbol cross-references, and check file contracts. |
| **Inconsistency Proof** | **Evidence Grounding** | Forbid abstract speculation; require exact verbatim quote from Artifact A and Artifact B. |
| **Patch Synthesis** | **Surgical Minimal Diff (Karpathy-style)** | Generate minimal unified diffs modifying only out-of-sync lines, preserving untouched codebase logic. |
| **Self-Healing Loop** | **Compiler-in-the-Loop Reflection** | Ingest raw compiler error logs (`tsc`, `gcc`, `pytest`) into prompt context to iteratively correct errors. |

---

## 15. Transparent Execution Trace & Reviewer Visibility

To ensure developer trust and eliminate "black box" agent skepticism, DriftGuard posts an **auditable, transparent execution trace** directly into the generated GitHub Pull Request body:

``` markdown
# 🛡️ DriftGuard Automated Consistency Fix

### 📌 Summary of Changes
- **Category:** `dependency_vs_code`
- **Target Files:** [`package.json`](file:///package.json), [`src/services/auth.ts`](file:///src/services/auth.ts)
- **Status:** ✅ Verified in Ephemeral Sandbox (`next build` & `npm test` passed)

---

### 🔍 Evidence & Inconsistency Proof
> **Artifact 1 (`src/services/auth.ts`, Line 14):**
> ```typescript
> import { jwtVerify } from 'jose';
> ```
> 
> **Artifact 2 (`package.json`, Lines 22-26):**
> ```json
> "dependencies": {
>   "jsonwebtoken": "^9.0.0"
> }
> ```
> 
> **Contradiction Rationale:**
> `src/services/auth.ts` imports the `jose` library on line 14, but `jose` is completely absent from `package.json` dependencies. This causes a build break during cold deployment.

---

### 🛠️ Sandboxed Verification Certificate
- **Sandbox Environment:** Ephemeral Docker Container (`node:20-alpine`)
- **Validation Commands Executed:**
  - `npm install --dry-run` ──> **PASS** (0.8s)
  - `npm run build` ──> **PASS** (14.2s)
  - `npm test` ──> **PASS** (3 passed, 0 failed)
- **Convergence:** Resolved in **Attempt 2/3** (Attempt 1 failed on missing TypeScript declaration types).

<details>
<summary><b>🔍 Expand Full Chain of Thought & Compiler Reflection Trace</b></summary>

```text
[00:01] Ingestion: Branch 'feature/jwt-migration' checked out.
[00:03] Tree-sitter: Parsed modified ASTs across 8 changed files.
[00:04] SCIP Indexer: Discovered 12 cross-artifact symbol dependency edges.
[00:05] Auditor: Flagged potential dependency drift between package.json and src/services/auth.ts.
[00:06] Verifier: Verbatim quotes verified against commit 4a9f1c.
[00:08] Sandbox: Spun up Docker container driftguard-sandbox-8f2a.
[00:10] Repair (Attempt 1): Injected "jose": "^5.2.0" into package.json.
[00:22] Sandbox Build (Attempt 1): FAILED (Exit Code 2).
        Stderr: "error TS7016: Could not find a declaration file for module 'jose'."
[00:24] Reflection Agent: Ingested TS7016. Adjusting patch to pin compatible typed build.
[00:26] Repair (Attempt 2): Updated import structure and resolved dependency lockfile.
[00:41] Sandbox Build (Attempt 2): SUCCESS (Exit Code 0).
[00:43] Actuation: Fix branch created: 'driftguard/fix-auth-jose-dependency'.
[00:44] Actuation: PR opened with verified surgical diff.
```
</details>
```

---

## 16. Cross-Artifact Grounding & Verbatim Attribution Model

To prevent LLM hallucinations from creating false alarms or faulty PRs, DriftGuard enforces a mathematical invariant on all reported inconsistencies:

### Verbatim Verification Invariant
Let $C_1$ and $C_2$ be the raw byte strings of Artifact 1 and Artifact 2 at commit $S$. Let $F_1$ and $F_2$ be the extracted fact strings quoted by the Drift Auditor:

$$\text{ValidDrift}(C_1, C_2, F_1, F_2) \iff (F_1 \sqsubseteq C_1) \land (F_2 \sqsubseteq C_2) \land \text{Contradicts}(F_1, F_2)$$

Where $\sqsubseteq$ denotes exact verbatim substring containment. If either $F_1 \not\sqsubseteq C_1$ or $F_2 \not\sqsubseteq C_2$, the verification layer immediately discards the finding as an ungrounded hallucination, preventing false positive notifications.

---

## 17. Declarative Configuration: The `.driftguard.yml` Specification

DriftGuard respects repository-level governance through a root `.driftguard.yml` file:

``` yaml
version: "1.0"

# Target branch filters
branches:
  include:
    - main
    - "release/*"
    - "feature/*"
  exclude:
    - "docs-only/*"

# Autonomous Stack Detection & Command Overrides
build_matrix:
  auto_detect: true          # Automatically infer stack if true
  overrides:
    frontend:
      working_directory: "./frontend"
      build_command: "npm run build"
      test_command: "npm test -- --watchAll=false"
    backend:
      working_directory: "./app"
      build_command: "python -m py_compile app/**/*.py"
      test_command: "pytest tests/"

# Sandboxed Verification Engine
sandbox:
  runtime: "docker"          # Options: 'docker' (local/standard) | 'kubernetes' (cloud cluster)
  memory_limit: "2Gi"
  cpu_limit: "2.0"
  timeout_seconds: 120
  network_access: "restricted" # Restrict outbound internet except package registries

# Bounded Self-Healing Loop
repair:
  enabled: true
  max_attempts: 3            # Bounded retry limit to prevent infinite loops
  require_passing_tests: true
  minimal_diff_only: true

# Review & Pull Request Actuation
pull_request:
  auto_create: true
  target_branch_prefix: "driftguard/fix-"
  labels:
    - "driftguard"
    - "automated-fix"
    - "needs-review"
  reviewers:
    - "core-dev-team"

# Multi-Model Routing Configuration (via OmniRoute)
model_routing:
  auditing_tier: "fast"      # Options: 'fast' (Groq/Qwen) | 'deep' (Claude/GPT-4o)
  repair_tier: "deep"
```

---

## 18. Tools Specification

| Tool Name | Owner Agent | Input Schema | Output Schema | Target SLA |
| :--- | :--- | :--- | :--- | :--- |
| `query_treesitter_ast` | Code Intelligence | `file_path: str, query_sexpr: str` | `matched_nodes: list[ASTNode]` | $< 50\text{ ms}$ |
| `query_scip_symbols` | Code Intelligence | `symbol_id: str, repo_path: Path` | `definitions: list, references: list` | $< 150\text{ ms}$ |
| `detect_repo_stack` | Stack Detector | `workspace_path: Path` | `manifests: list, build_cmds: list` | $< 100\text{ ms}$ |
| `verify_verbatim_evidence` | Drift Auditor | `f1: str, f2: str, c1: str, c2: str` | `is_valid: bool, line_anchors: dict` | $< 10\text{ ms}$ |
| `provision_sandbox` | Sandboxed Repair | `image: str, limits: dict` | `container_id: str, status: str` | $< 2,000\text{ ms}$ |
| `execute_sandbox_build` | Sandboxed Repair | `container_id: str, cmd: str` | `exit_code: int, stdout: str, stderr: str` | $< 30,000\text{ ms}$ |
| `omniroute_generate` | All Agents | `prompt: str, tier: str` | `completion: str, latency: float` | $< 3,000\text{ ms}$ |
| `create_github_pr` | PR Actuator | `branch: str, diff: str, cot: str` | `pr_url: str, pr_number: int` | $< 1,500\text{ ms}$ |

---

## 19. External Protocols & Tooling Strategy

DriftGuard leverages the **Model Context Protocol (MCP)** and local CLI interfaces to interact uniformly with developer tools:

``` mermaid
flowchart LR
    A["DriftGuard Multi-Agent Core"] --> M["Tool & MCP Client Layer"]
    M --> S1["Tree-sitter Parser Engine\n(In-Process Multi-Language AST)"]
    M --> S2["Sourcegraph SCIP Local CLI\n(Open-Source Symbol Graph)"]
    M --> S3["OmniRoute MCP Gateway\n(Model Routing & Telemetry)"]
    M --> S4["Docker/K8s Sandbox Controller\n(Isolated Container Execution)"]
```

This ensures zero dependency on proprietary cloud code intelligence APIs, zero subscription fees, and complete offline capability for developer CLI runs.

---

## 20. Memory Architecture

DriftGuard maintains a two-tier memory hierarchy:

```
Memory Hierarchy
├── Tier 1: Ephemeral Session State (Blackboard)
│   ├── Active git commit shas & modified file paths
│   ├── Candidate cross-artifact pairs
│   ├── Candidate unified diffs
│   ├── Active sandbox container IDs & mapped volumes
│   └── Compiler stderr logs per attempt
│
└── Tier 2: Persistent Repository Profile (Long-Term Memory)
    ├── Cached Tree-sitter & SCIP symbol cross-reference index
    ├── Historical build & test command discovery cache
    ├── Known false-positive suppression rules
    └── Success/failure convergence rates by drift category
```

---

## 21. Safety & Guardrails

To operate safely inside developer repositories, DriftGuard enforces strict AIDevOps safety guardrails:

``` mermaid
---
config:
  layout: elk
---
flowchart TD
    P["Proposed Candidate Patch"] --> G1["Guardrail 1: Syntax & AST Validation\n(Ensure file compiles syntactically via Tree-sitter)"]
    G1 -->|Fail| R["Reject & Re-synthesize"]
    G1 -->|Pass| G2["Guardrail 2: Read-Only Host Policy\n(Original repo workspace is strictly mounted READ-ONLY)"]
    G2 --> G3["Guardrail 3: Isolated Ephemeral Sandbox\n(Build runs inside non-root container with network egress clamping)"]
    G3 -->|Compiler Error| F["Feedback to Reflection Agent\n(Attempt < max_retries)"]
    G3 -->|Success| G4["Guardrail 4: PR Merge Barrier\n(Never push to main; always open PR for human review)"]
    G4 --> PR["Submit Pull Request"]
```

---

## 22. Sandboxed Verification & Self-Healing Execution Engine

A core differentiator of DriftGuard is that **patches are never accepted on theoretical plausibility**. They must be empirically compiled and tested in an isolated environment.

### Sandbox Architecture
- **Docker Engine (Local CLI)**: Uses `docker run --rm -v /repo_copy:/workspace:rw --network none` to execute builds in a clean container.
- **Kubernetes Runner (Enterprise CI/CD)**: Provisions ephemeral `BatchV1/Job` pods with strict resource limits (`limits.memory`, `limits.cpu`), executing builds inside dedicated namespaces and terminating immediately upon completion.
- **Network Isolation**: By default, network egress is clamped to prevent supply chain tampering or data exfiltration.

---

## 23. Iterative Self-Healing Loop & Utility Model

When a patch fails during sandboxed execution, DriftGuard computes a **Patch Utility Score** to determine whether to iterate, accept, or abandon the candidate:

$$U(patch) = w_1 \cdot \text{ExitCodeSuccess} + w_2 \cdot \text{PassedTestRatio} - w_3 \cdot \Delta_{\text{churn}} - w_4 \cdot \text{AttemptNumber}$$

Where:
- $\text{ExitCodeSuccess} \in \{0, 1\}$ indicates compilation success.
- $\text{PassedTestRatio} = \frac{\text{tests passed}}{\text{total tests}}$ ensures regression prevention.
- $\Delta_{\text{churn}} = \frac{\text{modified lines}}{\text{total lines}}$ penalizes bloated, non-minimal diffs.
- $\text{AttemptNumber}$ penalizes excessive retry iterations.

If the sandbox fails and $\text{Attempt} < \text{max\_retries}$, the compiler error output is injected into the prompt:
> *"The previous patch produced compiler error: `Cannot find module 'jose'`. Analyze why this failed and provide a revised minimal diff."*

---

## 24. Automated Tech-Stack Detection Heuristics

The **Stack Detector & Policy Agent** executes deterministic discovery before invoking any LLMs:

``` text
Discovery Matrix:
├── package.json present?
│   ├── "next" in dependencies ──> Next.js: run "npm run build"
│   ├── "react-scripts" present ──> CRA: run "npm test -- --watchAll=false"
│   └── Default ──> Node: run "npm test"
├── pyproject.toml / requirements.txt present?
│   ├── "fastapi" in file ──> FastAPI: run "pytest"
│   └── Default ──> Python: run "pytest" / "python -m unittest"
├── Cargo.toml present? ──> Rust: run "cargo check && cargo test"
├── go.mod present? ──> Go: run "go test ./..."
└── Dockerfile present? ──> Container: run "docker build --no-cache ."
```

Explicit definitions in `.driftguard.yml` immediately override inferred defaults.

---

## 25. GitHub Actions Integration & Automated Pull Request Actuation

DriftGuard is distributed as a reusable GitHub Action:

``` yaml
# Example user repo workflow: .github/workflows/driftguard.yml
name: DriftGuard Inconsistency Audit

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run DriftGuard Self-Healing Audit
        uses: driftguard/action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          config_path: ".driftguard.yml"
          sandbox_mode: "docker"
```

---

## 26. Evaluation Strategy & Benchmark Dataset

Evaluation will be conducted using a structured benchmark suite of **at least 44 real-world and synthetic evaluation runs** across diverse software repositories:

### Benchmark Suite Distribution

| Category | Repositories / Languages | Test Runs | Key Inconsistency Evaluated |
| :--- | :--- | :--- | :--- |
| **Dependency vs Code** | Python (FastAPI), TS (Next.js), Go | 10 | Unpinned packages, missing lockfile entries, undeclared imports |
| **Test vs Implementation** | Python (SQLModel), TypeScript | 8 | Modified function signatures, stale test mocks, obsolete assertions |
| **Docs vs Implementation** | Markdown, Python, Rust | 8 | Deprecated CLI arguments, inaccurate return types, deleted endpoints |
| **API Spec vs Route** | FastAPI (OpenAPI), Express (Swagger) | 6 | Undocumented path parameters, modified response schemas |
| **CI/CD vs Code** | GitHub Actions YAML, Docker | 6 | Broken build matrix paths, outdated Node/Python versions |
| **Polyglot Monorepo** | Next.js Frontend + Python Backend | 6 | Cross-stack contract drift, end-to-end build failures |
| **Total Structured Runs** | | **44** | |

---

## 27. Per-Run Trace Schema

Every run generates an auditable, machine-readable execution trace:

``` json
{
  "run_id": "dg_run_042",
  "trigger_type": "github_action_push",
  "commit_sha": "a7b3c9f",
  "branch": "feature/nextjs-api-v2",
  "detected_stack": {
    "languages": ["TypeScript", "Python"],
    "frameworks": ["Next.js", "FastAPI"]
  },
  "treesitter_ast_nodes_analyzed": 142,
  "scip_symbols_queried": 28,
  "drifts_detected": [
    {
      "drift_id": "d-01",
      "category": "api_spec_vs_code",
      "artifact_1": "openapi.json",
      "artifact_2": "app/api/routes.py",
      "verbatim_1": "\"/api/v1/users/{id}\"",
      "verbatim_2": "@router.get(\"/api/v2/users/{user_id}\")",
      "contradiction_proof": "API specification declares route under v1 with parameter 'id', but backend implementation moved to v2 with 'user_id'."
    }
  ],
  "sandbox_verification": {
    "engine": "docker",
    "image": "python:3.11-slim",
    "total_attempts": 2,
    "build_command": "pytest tests/",
    "final_exit_code": 0,
    "verification_certificate": "PASS"
  },
  "actuation": {
    "pr_created": true,
    "pr_number": 104,
    "pr_url": "https://github.com/org/repo/pull/104"
  },
  "total_duration_ms": 34200,
  "token_metrics": {
    "prompt_tokens": 4200,
    "completion_tokens": 850,
    "gateway_provider": "omniroute/qwen2.5-coder:7b"
  }
}
```

---

## 28. Evaluation Metrics

1. **Drift Detection Precision & Recall**:
   $$\text{Precision} = \frac{\text{True Drifts Confirmed}}{\text{Total Drifts Flagged}}, \quad \text{Recall} = \frac{\text{True Drifts Confirmed}}{\text{Total Ground-Truth Drifts}}$$
2. **Sandboxed Repair Success Rate**:
   $$\text{SRSR} = \frac{\text{Patches Passing 100\% Sandbox Builds \& Tests}}{\text{Total Patches Attempted}}$$
3. **Repair Convergence Efficiency**: Average number of retry attempts required to reach a passing build ($\le \text{max\_retries}$).
4. **Verbatim Evidence Attribution Rate**: Percentage of flagged drifts backed by exact substring verification.
5. **Reviewer Acceptance Rate**: Ratio of DriftGuard-generated PRs approved or merged by human developers without major manual edits.

---

## 29. Human-in-the-Loop (HITL) Reviewer Panel & Trust Model

In software engineering, autonomous agents must not be unchecked authorities. Developers reject bots that produce unexplainable noise or broken code.

### Human-Centric Review Rubric
Human reviewers evaluate DriftGuard PRs across 4 dimensions:

| Dimension | Score Range | Description | Critical Rejection Rule |
| :--- | :--- | :--- | :--- |
| **1. Grounding & Validity** | 1 (Hallucinated) – 5 (Flawless) | Evaluates whether the identified inconsistency is a genuine software bug. | Any fabricated file quote results in immediate PR rejection. |
| **2. Patch Minimality** | 1 (Bloated) – 5 (Surgical) | Verifies that the patch only touches necessary lines and does not refactor unrelated code. | Unsolicited style/formatting rewrites receive $\le 2$. |
| **3. Sandbox Build Validity** | 1 (Broken) – 5 (Verified) | Verifies that the patch builds cleanly and does not break existing test suites. | Any build or test failure in sandbox results in rejection. |
| **4. Transparency & Traceability** | 1 (Opaque) – 5 (Crystal Clear) | Evaluates the clarity of the PR explanation, verbatim quotes, and reasoning CoT. | Vague "AI fixed this" descriptions receive $\le 2$. |

---

## 30. Architecture Comparison Experiment

The project will benchmark 4 multi-agent orchestration topologies on identical software test suites:

- **Configuration A (Sequential)**: Trigger $\rightarrow$ Stack Detect $\rightarrow$ AST $\rightarrow$ Audit $\rightarrow$ Repair $\rightarrow$ PR.
- **Configuration B (Parallel/Broadcast)**: Parallel audit of independent artifact pairs followed by sequential repair.
- **Configuration C (Blackboard)**: Shared state where Auditor, Repair Engineer, and Reflection Agent asynchronously read/write to blackboard.
- **Configuration D (Hierarchical)**: Root Coordinator supervising all sub-agents with dynamic task delegation.

Metrics tracked: End-to-end latency, token overhead, repair convergence rate, and failure recovery.

---

## 31. Multi-Model Intelligence & Dynamic Model Routing

DriftGuard avoids vendor lock-in by utilizing the local **OmniRoute** gateway (`http://localhost:20128`), dynamically selecting models based on task requirements:

| Task Class | Model Class / Provider | Justification |
| :--- | :--- | :--- |
| **File Classification & Stack Detection** | Deterministic Python Heuristics | Zero token cost, sub-5ms latency |
| **AST Candidate Filtering** | Lightweight Code Model (Qwen 2.5 Coder 7B / Groq) | Fast structured JSON output, low latency |
| **Semantic Inconsistency Auditing** | Strong Reasoning Model (Claude 3.5 Sonnet / GPT-4o / Trae) | High precision, nuanced contract comprehension |
| **Surgical Patch Repair** | Code-Specialized Model (Qwen 2.5 Coder 32B / Claude) | High syntax compliance, minimal diff discipline |
| **Compiler Error Reflection** | Deep Reasoning Model (Claude / Gemini 1.5 Pro) | Complex trace analysis, multi-step debugging |

---

## 32. Enterprise Containerized Runtime & Kubernetes Architecture

### Docker Compose Architecture (Local Developer CLI)
Local developers run DriftGuard via a lightweight Compose environment:
``` text
driftguard-cli (Host or Container)
   ├── omniroute (Model Gateway: http://localhost:20128)
   ├── treesitter-runtime (In-Process C/Python bindings)
   ├── scip-local-indexers (Open-source CLI indexers)
   └── ephemeral-docker-runner (Mounts Docker socket for nested sandbox execution)
```

### Kubernetes Architecture (Enterprise Cloud CI/CD)
In cloud environments, DriftGuard runs as an ephemeral Kubernetes Job:
- **Controller Pod**: Ingests webhook, coordinates agents via OmniRoute.
- **Worker Jobs**: Spawns isolated ephemeral Pods with non-root security contexts (`runAsNonRoot: true`, `readOnlyRootFilesystem: false`), executing `npm build` or `pytest` within dedicated namespaces.

---

## 33. Observability Architecture

Observability is maintained at both the system and agent levels:
- **OpenTelemetry Instrumentation**: Distributed tracing across all agent spans (`delta_scan`, `treesitter_parse`, `scip_query`, `drift_audit`, `sandbox_build`, `pr_create`).
- **Telemetry Metrics**: Latency waterfalls, token counts by model provider, sandbox CPU/RAM utilization, and compiler iteration counts.
- **Real-Time Stream**: Live CLI terminal progress bars and GitHub Action step annotations.

---

## 34. Detailed Phasing & Milestones

### Phase 0 — Research, Scope & AIDevOps Architecture Freeze
- [x] Problem statement & AIDevOps scope approved
- [x] PEAS and environment formalization completed
- [x] Technology stack justified (Tree-sitter, Sourcegraph SCIP, OmniRoute, Docker, Kubernetes)
- [x] Baseline repository analysis and gap assessment completed
- [x] Comprehensive `PLAN.md` drafted and approved

### Phase 1 — Repository Transition, Architectural Reconditioning & Foundation
- [ ] Decouple codebase from legacy dataset snapshot paths (`driftguard-dataset/`), establishing a universal, live git-workspace ingestion interface.
- [ ] Recondition repository structure into the modular agentic layout (`app/agents/`, `app/intelligence/`, `app/sandbox/`, `app/actuation/`).
- [ ] Implement `GitDeltaScanner` extracting incremental changed files, hunks, and commit ranges from active/targeted branches.
- [ ] Implement `StackDetector` for autonomous framework and build-pipeline discovery (Next.js, FastAPI, Rust, Go).
- [ ] Implement `.driftguard.yml` declarative configuration parser and Pydantic schema validator.
- [ ] Establish the foundational unified CLI (`driftguard analyze --branch <name>`) operating on live repository workspaces.
- [ ] Re-align FastAPI backend and Vite frontend to interface with dynamic workspace branches instead of static dataset paths.

### Phase 2 — Tree-sitter & Open-Source SCIP Integration & Enhanced Drift Auditor
- [ ] Integrate **Tree-sitter** Python bindings across target grammars (Python, TypeScript, Go).
- [ ] Integrate **Sourcegraph SCIP** local CLI indexers for cross-file symbol reference mapping (100% free open-source).
- [ ] Upgrade `DriftAuditorAgent` to query Tree-sitter AST nodes before prompting LLM.
- [ ] Enforce verbatim quote anti-hallucination verification invariant.
- [ ] Connect agent model calls through local **OmniRoute** gateway (`http://localhost:20128`).

### Phase 3 — Docker & Kubernetes Ephemeral Sandboxed Self-Healing Engine
- [ ] Implement Docker sandbox runner (`app/sandbox/docker_runner.py`) with resource limits.
- [ ] Implement Kubernetes ephemeral Job runner (`app/sandbox/k8s_runner.py`) for cloud CI.
- [ ] Implement `SandboxedRepairEngineer` generating surgical unified diffs.
- [ ] Implement compiler error ingestion and reflection loop honoring `max_attempts`.
- [ ] Unit test sandbox execution across Python (`pytest`) and Next.js (`npm run build`).

### Phase 4 — GitHub Actions Workflow & PR Actuator with Reviewer Trace HUD
- [ ] Implement GitHub API PR creator (`app/actuation/github_pr.py`) with branch committer.
- [ ] Implement Reviewer Trace HUD generator formatting collapsible CoT summaries.
- [ ] Package DriftGuard as a production-ready, reusable GitHub Action (`action.yml`).
- [ ] Test end-to-end flow: Git push $\rightarrow$ Drift detected $\rightarrow$ Sandbox repair $\rightarrow$ PR opened.

### Phase 5 — Scientific Evaluation & Benchmark Experiments (44+ Runs)
- [ ] Execute 44+ structured evaluation runs across multi-language repository test suites.
- [ ] Conduct 4-way architectural comparison (Sequential vs Parallel vs Blackboard vs Hierarchical).
- [ ] Benchmark OmniRoute dynamic model routing against static single-model baselines.
- [ ] Conduct Human-in-the-Loop (HITL) domain expert evaluation on PR quality.
- [ ] Analyze latency bottlenecks, sandbox build overhead, and token efficiency.

### Phase 6 — Enterprise Packaging, Whitepaper & Viva Defense Deliverables
- [ ] Production multi-stage `Dockerfile` and enterprise `docker-compose.yml`.
- [ ] Comprehensive IEEE-style AIDevOps final technical report (`docs/FINAL_REPORT.md`).
- [ ] Interactive live demonstration script and executive slide deck.
- [ ] Viva defense guide with architectural trade-off rationales.

---

## 35. Subsystem Integration & Protocol Matrix

| Source Subsystem | Target Subsystem | Interaction Pattern | Transport / Protocol | Message / Payload Schema | SLA / Target Latency | Failure & Recovery Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Git / GitHub Action** | **Delta Scanner** | Webhook / CLI Exec | Git CLI / Webhook JSON | `GitDeltaEvent` (commit, branch, files) | $< 1,000\text{ ms}$ | Retry checkout with fetch-depth=0 |
| **Delta Scanner** | **Stack Detector** | In-Process Function | Python Object | `ChangedFileList` | $< 50\text{ ms}$ | Fallback to `.driftguard.yml` defaults |
| **Stack Detector** | **Tree-sitter / SCIP** | In-Process / CLI | C-FFI / Local CLI | `ASTQuery` -> `SymbolGraph` | $< 200\text{ ms}$ | Fallback to local regex artifact extractor |
| **Drift Auditor** | **OmniRoute Gateway** | HTTP Request | REST (OpenAI-compatible) | `DriftPrompt` -> `StructuredDriftReport` | $< 2,500\text{ ms}$ | Fallback to secondary model in pool |
| **Repair Engineer** | **Docker / K8s Sandbox** | Container Exec | Docker API / K8s Client | `PatchPayload` -> `BuildLogResponse` | $< 30,000\text{ ms}$ | Timeout at 120s; kill sandbox container |
| **Repair Engineer** | **Reflection Agent** | Blackboard State | In-Memory Dictionary | `SandboxExecutionResult` (code, stderr) | $< 5\text{ ms}$ | Break loop if attempt == max_retries |
| **PR Actuator** | **GitHub REST API** | HTTPS REST | GitHub API v3 / Octokit | `CreatePRPayload` (title, body, diff) | $< 1,500\text{ ms}$ | Retry on rate limit with exp-backoff |

---

## 36. Phase Timeline & Team Matrix

| Period | Milestone | Deliverable |
| :--- | :--- | :--- |
| **Weeks 1–2** | Repository Transition, Conditioning & Foundation | Legacy dataset decoupling, agentic modular reconditioning, `.driftguard.yml` schema, Git delta scanner, Stack detector, unified CLI |
| **Weeks 3–4** | Tree-sitter, SCIP & OmniRoute Integration | Tree-sitter grammars, SCIP indexers, grounded drift prompts |
| **Weeks 5–6** | Docker & Kubernetes Sandboxed Repair Engine | Ephemeral sandbox execution, compiler feedback reflection loop |
| **Weeks 7–8** | GitHub Action Packaging & PR Actuator | Reusable GitHub Action, automated PR creation with CoT trace |
| **Weeks 9–10** | Benchmark Evaluation & HITL Review | 44+ benchmark runs, 4-way architecture comparison, human review |
| **Weeks 11–12** | Enterprise Packaging & Final Defense | Docker Compose, final report, demonstration, viva defense |

---

## 37. Technology Stack Summary

- **Agent Framework & Core**: Python 3.11+, Pydantic v2, FastAPI, Click/Typer (CLI).
- **Code Intelligence**: **Tree-sitter** (universal AST parser), **Sourcegraph SCIP** (100% free open-source cross-file symbol indexers).
- **Model Routing**: **OmniRoute** local pooled gateway (`http://localhost:20128`), LiteLLM.
- **Sandboxed Container Runtime**: **Docker** (Docker Engine API / `docker-py`), **Kubernetes** (`kubernetes-client` Python SDK for ephemeral Jobs/Pods).
- **CI/CD & Actuation**: **GitHub Actions** (`action.yml`), GitHub REST/GraphQL API (`PyGithub` / Octokit).
- **Vector DB & Embeddings**: ChromaDB, Sentence-Transformers (`all-MiniLM-L6-v2`).
- **Observability & UI**: OpenTelemetry, Streamlit, Vite + React + Tailwind CSS.

---

## 38. Repository Structure

``` text
DriftGuard_Repo/
├── .github/
│   └── workflows/
│       ├── driftguard.yml               # Production GitHub Action workflow
│       └── ci.yml                       # Internal repository CI
│
├── .driftguard.yml                      # Default declarative repository policy
│
├── app/
│   ├── actuation/
│   │   ├── git_committer.py             # Surgical git branch & commit manager
│   │   └── github_pr.py                 # GitHub PR creator & reviewer trace formatter
│   │
│   ├── agents/
│   │   ├── coordinator.py               # Hierarchical AIDevOps Root Manager
│   │   ├── delta_scanner.py             # Git diff & branch perception agent
│   │   ├── stack_detector.py            # Framework & build-rule inference agent
│   │   ├── drift_auditor.py             # Inconsistency verification agent
│   │   ├── repair_engineer.py           # Sandboxed self-healing patch agent
│   │   └── reflection_agent.py          # Compiler-error feedback & retry agent
│   │
│   ├── intelligence/
│   │   ├── treesitter_parser.py         # Tree-sitter multi-language AST engine
│   │   └── scip_indexer.py              # Sourcegraph SCIP open-source symbol runner
│   │
│   ├── sandbox/
│   │   ├── base.py                      # Abstract sandbox interface
│   │   ├── docker_runner.py             # Ephemeral Docker container executor
│   │   └── k8s_runner.py                # Ephemeral Kubernetes Job/Pod executor
│   │
│   ├── analysis/
│   │   ├── drift_pipeline.py            # Pipeline orchestrator
│   │   ├── evidence_verifier.py         # Verbatim anti-hallucination verifier
│   │   ├── prompts.py                   # Grounded drift prompts
│   │   └── relationship_graph.py        # Cross-artifact relationship builder
│   │
│   ├── ingestion/
│   │   ├── repository_scanner.py        # Ingestion & file classifier
│   │   └── artifact_extractor.py        # AST fact extractor
│   │
│   ├── api/
│   │   └── main.py                      # FastAPI server
│   │
│   └── config.py                        # Central settings
│
├── frontend/                            # Vite + React + Tailwind management UI
├── scripts/
│   ├── run_cli.py                       # Local developer CLI entrypoint
│   └── benchmark_runner.py              # 44-run evaluation suite runner
│
├── data/
│   ├── benchmarks/                      # Curated multi-language test repos
│   └── traces/                          # Recorded execution traces
│
├── action.yml                           # GitHub Action definition
├── Dockerfile.action                    # Production GitHub Action container
├── docker-compose.yml                   # Local developer runtime
├── requirements.txt
└── PLAN.md
```

---

## 39. AIDevOps & Course Concept → Implementation Mapping

| Course Concept | DriftGuard AIDevOps Implementation |
| :--- | :--- |
| **Intelligent Developer Tools** | Automated cross-artifact consistency auditing & PR generation bot |
| **PEAS Framework** | Formal definition of Git environment, PR actuators, AST sensors |
| **Model-Based Reflex Agent** | Incremental git delta perception paired with `.driftguard.yml` rules |
| **Goal-Based & Utility Planning** | Sandboxed repair candidate scoring ($U(patch)$) optimizing build success & minimal diffs |
| **ReAct Paradigm** | Interleaved Tree-sitter AST inspection, SCIP symbol queries, and evidence verification |
| **Reflection & Self-Correction** | Ingestion of raw compiler stderr logs to refine broken patches up to retry limits |
| **Sandboxed Execution** | Ephemeral Docker containers and Kubernetes Jobs isolating builds from production |
| **Multi-Agent Orchestration** | Division of labor: Coordinator, Auditor, Repair Engineer, PR Actuator |
| **Anti-Hallucination & Grounding** | Verbatim substring containment proof against Git blob snapshots |
| **Model Routing & Cost Optimization**| Local OmniRoute gateway routing across heterogeneous LLM families |
| **Reviewer Explainability** | Transparent Chain of Thought traces and build certificates in PR comments |

---

## 40. Design Decisions

### DD-01 — GitHub Actions & Local CLI Dual-Delivery
**Decision:** Package DriftGuard as both a reusable GitHub Action and a local CLI.  
**Reason:** Software engineers require consistency checks both locally during pre-commit/feature development and asynchronously in CI pipelines before code merges.

### DD-02 — Ephemeral Docker & Kubernetes Sandboxing over Host Execution
**Decision:** Never run candidate patch builds directly on the host operating system.  
**Reason:** Untrusted or faulty code patches can damage host configurations, leave zombie processes, or introduce security vulnerabilities. Ephemeral containers provide guaranteed isolation, repeatable clean states, and resource governance.

### DD-03 — Tree-sitter & Free Sourcegraph SCIP over Paid Cloud APIs
**Decision:** Use Tree-sitter for AST syntax parsing and Sourcegraph's open-source SCIP indexers for cross-file symbol intelligence. Strictly forbid paid Sourcegraph subscriptions.  
**Reason:** Tree-sitter is the undisputed industry standard (MIT, used by GitHub & Cursor). Sourcegraph's SCIP indexers are 100% free, open-source (Apache 2.0/MIT), run locally and offline, and incur $0 in licensing fees while delivering production-grade definition/reference graphs.

### DD-04 — OmniRoute for Pooled Multi-Model Routing
**Decision:** Route all agent LLM calls through OmniRoute (`http://localhost:20128`).  
**Reason:** Enables seamless model cascading (fast models for pair filtering; strong reasoning models for repair) and leverages the user's pooled free provider gateway without vendor lock-in.

### DD-05 — Pull Request as the Ultimate Actuation Boundary
**Decision:** DriftGuard never pushes directly to `main` or production branches.  
**Reason:** Human developers must maintain final architectural and release authority. The system presents verified, pre-tested PRs with transparent rationale, honoring the Human-in-the-Loop paradigm.

### DD-06 — Bounded Repair Retry Limits in `.driftguard.yml`
**Decision:** Enforce hard ceilings on self-correction loops (`max_attempts: 3`).  
**Reason:** Prevents infinite LLM repair thrashing, excessive token consumption, and CI pipeline timeouts on unresolvable semantic bugs.

---

## 41. Risk Register

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Infinite Sandbox Repair Loop** | High | Medium | Enforce strict `max_attempts` and sandbox execution timeouts (120s) in `.driftguard.yml`. |
| **Compiler Error Hallucination** | High | Low | Ingest raw, unedited compiler stdout/stderr directly into reflection context without intermediate summarization. |
| **Sandbox Resource Exhaustion** | High | Medium | Apply strict Docker/K8s CPU (2.0) and memory (2Gi) ceilings; kill containers exceeding limits. |
| **CI/CD Token & Latency Overhead** | Medium | Medium | Use static pre-screening to skip non-drifts; route routine tasks to lightweight models via OmniRoute. |
| **Developer Alert Fatigue** | High | Medium | Enforce verbatim evidence verification invariant; discard any drift lacking exact line citations. |

---

## 42. Definition of Done

### Phase 1 — Repository Transition, Architectural Reconditioning & Foundation
- [ ] Decouple codebase from legacy dataset snapshot paths (`driftguard-dataset/`), enabling dynamic live-workspace analysis
- [ ] Recondition directory structure to modular agentic architecture (`app/agents/`, `app/intelligence/`, `app/sandbox/`, `app/actuation/`)
- [ ] Git delta scanner operational on active/targeted branch commits (`GitDeltaScanner`)
- [ ] Autonomous stack detector identifying Next.js, Python, Rust, and Go frameworks (`StackDetector`)
- [ ] `.driftguard.yml` declarative parser and Pydantic schema validator passing all test fixtures
- [ ] Foundational local CLI command (`driftguard analyze --branch <name>`) operational on live repositories
- [ ] FastAPI backend and Vite frontend re-wired to support live workspace branch analysis

### Phase 2 — Tree-sitter & Open-Source SCIP Grounded Auditor
- [ ] Tree-sitter Python bindings integrated across target languages (Python, TypeScript, Go)
- [ ] Local SCIP open-source CLI indexers integrated for cross-file symbol resolution
- [ ] Verbatim substring verification invariant passing unit test assertions
- [ ] OmniRoute gateway integrated and routing prompt calls

### Phase 3 — Docker & Kubernetes Sandboxed Self-Healing
- [ ] Ephemeral Docker sandbox executing clean builds with resource governance
- [ ] Ephemeral Kubernetes Job runner operational for cloud CI execution
- [ ] Iterative compiler feedback loop repairing broken builds up to `max_attempts`
- [ ] Zero environment leakage verified across test runs

### Phase 4 — GitHub Actions Workflow & PR Actuator
- [ ] Automated branch creation and surgical git commit manager operational
- [ ] GitHub PR creation bot functional via GitHub REST/GraphQL API
- [ ] Collapsible Reviewer Trace HUD formatting verbatim quotes and build certificates
- [ ] Reusable GitHub Action (`action.yml`) verified in live repository test

### Phase 5 — Scientific Evaluation (44+ Runs)
- [ ] 44+ structured benchmark runs executed across multi-language repositories
- [ ] 4-way multi-agent architecture comparison benchmark completed
- [ ] OmniRoute dynamic routing efficiency quantified against single-model baseline
- [ ] Human-in-the-Loop (HITL) domain expert evaluation completed with Kappa agreement

### Phase 6 — Enterprise Deliverables & Defense
- [ ] Production multi-stage `Dockerfile` and enterprise `docker-compose.yml` operational
- [ ] Comprehensive IEEE-style final technical report completed (`docs/FINAL_REPORT.md`)
- [ ] Executive presentation slide deck and interactive live demonstration ready
- [ ] Viva defense preparation guide completed

---

## 43. Final Project Positioning & Guiding Principles

DriftGuard should ultimately be evaluated as:

> **A measurable, closed-loop AIDevOps multi-agent system that transforms static software repositories into self-healing codebases by integrating Tree-sitter AST parsing, open-source SCIP symbol intelligence, sandboxed container verification, and transparent Pull Request actuation.**

### Guiding Principles

1. **Never Propose an Untested Fix**: If a code patch has not compiled and passed test suites inside an isolated sandbox, it must never be submitted as a pull request.
2. **Never Hallucinate an Inconsistency**: Every reported contradiction must be grounded in verbatim quoted evidence from existing repository artifacts.
3. **100% Free Open-Source Tooling**: Rely strictly on open-source standards (Tree-sitter, local SCIP indexers) with $0 commercial license or API costs.
4. **Transparency Over Autonomy**: Human developers are the ultimate reviewers. DriftGuard provides explainable, auditable Chain of Thought traces so developers can review changes with total confidence.
