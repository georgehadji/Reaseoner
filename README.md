<div align="center">

<!-- ASCII Banner -->
<pre>
 █████╗ ██████╗  █████╗         ██████╗ ██╗██████╗ ███████╗██╗     ██╗███╗   ██╗███████╗
██╔══██╗██╔══██╗██╔══██╗        ██╔══██╗██║██╔══██╗██╔════╝██║     ██║████╗  ██║██╔════╝
███████║██████╔╝███████║        ██████╔╝██║██████╔╝█████╗  ██║     ██║██╔██╗ ██║█████╗  
██╔══██║██╔══██╗██╔══██║        ██╔═══╝ ██║██╔══██╗██╔══╝  ██║     ██║██║╚██╗██║██╔══╝  
██║  ██║██║  ██║██║  ██║        ██║     ██║██║  ██║███████╗███████╗██║██║ ╚████║███████╗
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝        ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝
v2.2 — Adaptive Reasoning Architecture
</pre>

<!-- Badges -->
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js_16-000000.svg?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4.svg?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
<br>
[![Tests](https://img.shields.io/badge/tests-800%2B%20passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-~70%25-yellow.svg?style=flat-square)](.)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/tesse/Reasoner?style=flat-square&logo=github)](https://github.com/tesse/Reasoner)

**A production-grade reasoning engine that orchestrates 16+ LLM methodologies — from multi-perspective analysis to scientific hypothesis testing — with automatic method selection, cross-lab diversity, and real-time streaming.**

[🚀 Quick Start](#quick-start) · [📖 Documentation](#documentation) · [🧠 Methods](#reasoning-methods) · [🏗️ Architecture](#architecture) · [🤝 Contributing](#contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Why ARA?](#why-ara)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [Web Interface](#web-interface)
  - [Programmatic API](#programmatic-api)
- [Architecture](#architecture)
  - [HyperGate Pre-Router](#hypergate-pre-router)
  - [Core Pipeline](#core-pipeline)
- [Reasoning Methods](#reasoning-methods)
- [Available Presets](#available-presets)
- [Model Routing Philosophy](#model-routing-philosophy)
- [Features](#features)
- [Project Structure](#project-structure)
- [Security](#security)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

ARA Pipeline is not a chatbot. It is a **reasoning orchestrator** that decomposes complex problems into structured phases, leverages multiple LLMs in parallel from diverse training ecosystems, applies rigorous independent critique, stress-tests solutions under adversarial conditions, and synthesizes actionable recommendations with epistemic labeling.

> *"Give me six hours to chop down a tree and I will spend the first four sharpening the axe."*  
> — Abraham Lincoln

ARA spends its first phases **sharpening** — classifying, decomposing, vetting context — before a single solution is generated.

### Key Capabilities

| Capability | Description |
|-----------|-------------|
| 🧠 **HyperGate Pre-Router** | 6 parallel sub-agents automatically detect language, complexity, directness, web-search need, and optimal reasoning method. Simple questions are answered instantly; complex ones are routed to the right methodology. |
| 🔀 **16 Reasoning Methods** | Scientific, Socratic, Debate, Jury, Bayesian, Delphi, Chain-of-Verification, Skeleton-of-Thought, Tree-of-Thoughts, Program-of-Thoughts, Self-Discover, and more. |
| 🌍 **Cross-Lab Diversity** | Each phase routes to a different model family to prevent echo chambers and maximize epistemic coverage. |
| 🔄 **Intelligent Fallbacks** | Automatic cross-lab fallback routing when a provider fails — never falls back blindly to a single primary. |
| ⚡ **Real-Time Streaming** | Server-Sent Events (SSE) deliver per-phase progress, token usage, cost tracking, and model attribution. |
| 🔍 **Web-Grounded Research** | Integrated SearXNG search for evidence-based reasoning with iterative RAG. |
| 🧠 **Persistent Memory** | Neuro-based long-term memory with compression, embedding-based similarity search, and tenant isolation. |
| 🛡️ **Defense in Depth** | Prompt-injection filtering, input sanitization, rate limiting, CSRF protection, and adversarial persuasion defense. |

---

## 💡 Why ARA?

Traditional LLM applications send your question to a single model and return the first answer. ARA treats reasoning as a **first-class engineering problem**:

```
Traditional:    User → GPT-4 → Answer (1 call, 1 perspective)
ARA Pipeline:   User → HyperGate → Classify → Decompose → Vet Context
                      → [16 methods] → Generate (parallel, cross-lab)
                      → Critique (independent scorer)
                      → Stress Test (adversarial scenarios)
                      → Synthesize → Epistemic Labels → Action Blueprint
                      (8-20+ calls, 4+ model families, rigorous quality gates)
```

**The result:** fewer hallucinations, better coverage of edge cases, and outputs you can actually act on.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** (for the web UI)
- **OpenRouter API Key** (recommended — single key, 350+ models)

### 1. Clone & Setup

```bash
git clone https://github.com/tesse/Reasoner.git
cd Reasoner

# Backend
cp .env.example .env
# Edit .env and add: OPENROUTER_API_KEY=sk-or-v1-your-key-here
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ui-next && npm install && cd ..
```

### 2. Start Everything (One Command)

```bash
python start_all.py
```

This starts:
- 🐍 **FastAPI Backend** on `http://localhost:8001` (configurable via `SERVER_PORT`)
- ⚛️ **Next.js Frontend** on `http://localhost:3000`
- 🔍 **SearXNG Search** on `http://localhost:8888`

Open [http://localhost:3000](http://localhost:3000) and start reasoning.

### 3. Or Start Services Individually

```bash
# Terminal 1 — Backend API
uvicorn asgi:app --reload --host 0.0.0.0 --port 8001

# Terminal 2 — Search Engine
docker-compose -f docker-compose.searxng.yml up -d

# Terminal 3 — Frontend
cd ui-next && npm run dev
```

### 4. CLI Quick Run

```bash
# Default preset — balanced quality and cost (~$0.05/run)
python main.py --problem "How should we prioritize our Q3 product roadmap?"

# Budget option — approximately $0.02 per run
python main.py --problem "..." --preset debate-budget

# Maximum quality — premium models with 4-lab diversity (~$0.20/run)
python main.py --problem "..." --preset multi-perspective-premium
```

---

## 🔧 Installation

<details>
<summary><b>Backend Installation (click to expand)</b></summary>

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify installation
python -m pytest tests/ -q
```

</details>

<details>
<summary><b>Frontend Installation (click to expand)</b></summary>

```bash
cd ui-next
npm install

# Dev server
npm run dev

# Production build
npm run build
```

</details>

---

## ⚙️ Configuration

### Option 1: OpenRouter (Recommended)

One key. 350+ models. Simplest billing.

```bash
# .env
OPENROUTER_API_KEY="sk-or-v1-..."
```

### Option 2: Individual Provider Keys

Mix and match direct provider access:

```bash
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
GOOGLE_API_KEY="..."
DEEPSEEK_API_KEY="sk-..."
MISTRAL_API_KEY="..."
XAI_API_KEY="..."
PERPLEXITY_API_KEY="..."
OLLAMA_BASE_URL="http://localhost:11434"
```

### Optional Settings

```bash
# Web search engine
SEARXNG_URL="http://localhost:8888"

# Admin API key for cache clearing and key management
ADMIN_API_KEY="your-admin-key"

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

## 🎮 Usage

### CLI

```bash
# List available presets and models
python main.py --list-presets
python main.py --list-models

# Run with specific preset
python main.py --problem "Should we adopt microservices?" --preset debate-premium

# Custom routing per role
python main.py --problem "..." --routing '{"primary":"claude-sonnet","scoring":"sonar-pro"}'

# Load from file and export JSON
python main.py --problem-file problem.txt --output results.json --preset multi-perspective-premium

# Sequential mode for rate-limited environments
python main.py --problem "..." --sequential

# Adjust top-k pruning (default: 2)
python main.py --problem "..." --top-k 3
```

### Web Interface

The web interface provides a chat-like experience with:
- ⚡ **Real-time SSE streaming** of phase progress
- 📊 **Per-phase token usage**, cost tracking, and model attribution
- 🧠 **Auto-method selection** — HyperGate chooses the best reasoning method for you
- 💬 **Persistent conversation history** with IndexedDB
- 🔍 **Web search mode** — bypass the pipeline for direct search results

### Programmatic API

```python
import asyncio
from reasoner.pipeline import ARAPipeline
from reasoner.llm import ProviderRouter

async def main():
    router = ProviderRouter.from_model_ids(
        primary_id="claude-sonnet",
        routing={"scoring": "sonar-pro", "synthesis": "glm-5"}
    )
    pipeline = ARAPipeline(router=router, preset_name="multi-perspective-premium")
    state = await pipeline.run("Your complex problem here")

    print(f"Task Type: {state.task_type}")
    print(f"Sub-problems: {state.sub_problems}")
    print(f"Final Answer: {state.final_solution.core_solution}")
    print(f"Epistemic Label: {state.final_solution.epistemic_label}")
    print(f"Cost: ${state.total_cost_usd:.4f}")

asyncio.run(main())
```

### REST API

```bash
# Run pipeline (returns SSE stream)
curl -X POST http://localhost:8001/api/run \
  -H "Content-Type: application/json" \
  -d '{"problem": "How to optimize cloud costs?", "preset": "research-premium"}'

# Web search
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest LLM reasoning benchmarks 2025"}'

# Health check
curl http://localhost:8001/api/health
```

---

## 🏗️ Architecture

### HyperGate Pre-Router

Every request passes through the HyperGate before any reasoning pipeline starts. Six specialized sub-agents run **in parallel**, and a TieBreaker resolves conflicts if needed.

```
User Problem
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│              HyperGateAgent (Phase 1 — parallel)            │
│                                                             │
│  LanguageDetector    ComplexityEstimator    DirectDetector  │
│       (lang?)            (simple/med/        (pipeline or   │
│                           complex?)           direct?)      │
│                                                             │
│  WebSearchDetector       MethodClassifier                   │
│  (real-time data         (16 methods:                       │
│   needed?)                debate/scientific/tot/…?)        │
└──────────────────────────┬──────────────────────────────────┘
                           │ synthesize()  (pure Python)
          ┌────────────────┼────────────────┐
          │ DIRECT         │ WEB_SEARCH     │ PIPELINE
          ▼                ▼                ▼
  Answer immediately   Run live search    Full ARA Pipeline
  (no pipeline)        and return         (method auto-selected)
```

**Fail-safe design**: any sub-agent error becomes a graceful fallback — never a crash.  
**Security**: real method names are never exposed to the LLM. Only opaque letters (B–Q) appear in sub-agent prompts.  
**Caching**: per-sub-agent LRU cache (512 entries) + top-level HyperGateAgent cache.

### Core Pipeline (6 Phases)

```
User Problem  (routed here by HyperGateAgent when action = "pipeline")
     │
     ▼
Phase 0: Task Classification
     │    → Classifies task type (analytical, strategic, creative, technical)
     │    → Auto-detects language for multi-language synthesis
     ▼
Phase 1: Problem Decomposition
     │    → Generates ≤5 sub-problems, assumption audit, failure modes
     ▼
Phase 2: Multi-Perspective Generation
     │    → Constructive, Destructive, Systemic, Minimalist perspectives
     │    → Executed in parallel across diverse models from different labs
     ▼
Phase 3: Critique & Pruning
     │    → Independent model scores candidates 0-10 per criterion
     │    → Retains top-k solutions (default: 2)
     ▼
Phase 4: Stress Testing
     │    → Evaluates under Optimal, Constraint Violation, Adversarial scenarios
     ▼
Phase 5: Synthesis
          → VERIFIED / HYPOTHESIS / UNKNOWN labeled output
          → Action Blueprint with Go/No-Go criteria
          → Meta-Cognitive Audit
```

**State Management**: Immutable `PipelineState` dataclass persisted between phases.  
**Total LLM Calls**: 8+ per run (4 parallel in Phase 2); varies by method.  
**Languages**: Auto-detects and responds in 10+ languages.

---

## 🧠 Reasoning Methods

ARA supports **16 specialized reasoning methodologies** beyond the default orchestrated pipeline:

| Method | Description | Best For |
|--------|-------------|----------|
| **Orchestrated** | Default 6-phase pipeline with multi-perspective generation | General complex problems |
| **Debate** | Two models compete; a third judges the winner | Polarized decisions |
| **Scientific** | Hypothesis generation, falsification tests, evidence scoring | Research & validation |
| **Socratic** | Elenchus questioning to expose assumptions | Clarifying ambiguous problems |
| **Jury** | Multiple generators scored by an independent panel of critics | High-stakes decisions |
| **Research** | Web-grounded deep research with iterative SearXNG search | Evidence-heavy questions |
| **Pre-Mortem** | Prospective hindsight failure analysis (Gary Klein methodology) | Risk assessment |
| **Bayesian** | Prior → likelihood → posterior → sensitivity reasoning | Probabilistic reasoning |
| **Dialectical** | Hegelian thesis-antithesis-synthesis progression | Philosophical analysis |
| **Analogical** | Structure-mapping and cross-domain transfer | Creative problem solving |
| **Delphi** | Expert consensus with convergence tracking | Forecasting |
| **Chain-of-Verification** | Draft → verify → answer → revise | Fact-checking |
| **Skeleton-of-Thought** | Skeleton → parallel solve → assemble | Latency reduction |
| **Tree-of-Thoughts** | Reasoning as tree search with evaluation and backtracking | Planning & optimization |
| **Program-of-Thoughts** | Executable code as intermediate reasoning | Quantitative problems |
| **Self-Discover** | Dynamic selection and composition of reasoning modules | Novel problem types |

---

## 🎛️ Available Presets

Every method has a **Budget** (~$0.02/run) and **Premium** (~$0.15–$0.30/run) variant.

<details>
<summary><b>View all 24+ presets (click to expand)</b></summary>

| Preset | Tier | Primary | Phase 2 Diversity |
|--------|------|---------|-------------------|
| `multi-perspective-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `multi-perspective-premium` | Premium | `claude-opus` | Kimi + DeepSeek + Claude + Mistral |
| `debate-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `debate-premium` | Premium | `claude-sonnet` | GPT-5 + Claude + DeepSeek |
| `scientific-budget` | Budget | `sonar` | DeepSeek + Qwen + GLM |
| `scientific-premium` | Premium | `sonar-pro` | Sonar Deep Research + Claude + DeepSeek |
| `research-budget` | Budget | `sonar` | DeepSeek + Qwen + GLM |
| `research-premium` | Premium | `sonar-pro` | Sonar Deep Research + Claude + DeepSeek |
| `jury-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `jury-premium` | Premium | `claude-sonnet` | Kimi + DeepSeek + Claude + Mistral |
| `cove-budget` | Budget | `deepseek-v3` | DeepSeek draft → Qwen verify → GLM answer → DeepSeek revise |
| `cove-premium` | Premium | `claude-opus` | Claude draft → Sonar verify → DeepSeek answer → Claude revise |
| `sot-budget` | Budget | `deepseek-v3` | DeepSeek skeleton → Qwen parallel solve → DeepSeek assemble |
| `sot-premium` | Premium | `claude-opus` | Claude skeleton → Kimi parallel solve → Claude assemble |
| `tot-budget` | Budget | `deepseek-v3` | DeepSeek decompose → Qwen generate → GLM evaluate → DeepSeek backtrack |
| `tot-premium` | Premium | `claude-opus` | Claude decompose → DeepSeek generate → Sonar evaluate → Claude backtrack |
| `pot-budget` | Budget | `deepseek-v3` | DeepSeek code generation + simulated execution |
| `pot-premium` | Premium | `gpt-5` | GPT-5 code generation + Claude interpretation |
| `self-discover-budget` | Budget | `deepseek-v3` | DeepSeek module selection → Qwen adaptation → DeepSeek implementation |
| `self-discover-premium` | Premium | `claude-opus` | Claude module selection → DeepSeek adaptation → Claude implementation |
| `pre-mortem-budget` / `pre-mortem-premium` | — | — | Prospective failure analysis |
| `bayesian-budget` / `bayesian-premium` | — | — | Probabilistic reasoning |
| `dialectical-budget` / `dialectical-premium` | — | — | Thesis-antithesis-synthesis |
| `analogical-budget` / `analogical-premium` | — | — | Cross-domain transfer |
| `delphi-budget` / `delphi-premium` | — | — | Expert consensus |

</details>

---

## 🔀 Model Routing Philosophy

### Why Cross-Lab Diversity Matters

Different model families are trained on different data distributions, reward functions, and safety paradigms. When multiple perspectives come from the **same lab**, the pipeline converges to an **echo chamber** — the models agree on the same hidden assumptions and miss the same blind spots.

### Design Rules

1. **Phase 2 (Perspectives)** — Minimum 3 different labs in Budget, 4 in Premium.
2. **Phase 3 (Scoring)** — Scorer must be from a different ecosystem than the dominant Phase-2 generator.
3. **Fallbacks** — Failures fall back to a **cross-lab equivalent**, not automatically to the preset primary.
4. **Phase 0 (Classification)** — Optimized for speed and cost; diversity is secondary.
5. **Phase 5 (Synthesis)** — Optimized for coherence and depth; diversity is useful but not at the expense of consistency.

### Example: Budget Tier Routing

| Phase | Role | Model | Fallback |
|-------|------|-------|----------|
| 0 | classification | `qwen3-turbo` | `glm-4-air` |
| 1 | decomposition | `deepseek-v3` | `glm-4-air` |
| 2 | constructive | `deepseek-v3` | `qwen3-max` |
| 2 | destructive | `qwen3-max` | `deepseek-v3` |
| 2 | systemic | `glm-4-air` | `deepseek-v3` |
| 2 | minimalist | `qwen3-turbo` | `deepseek-v3` |
| 3 | scoring | `qwen3-max` | `glm-4-air` |
| 4 | stress_testing | `deepseek-v3` | `qwen3-max` |
| 5 | synthesis | `deepseek-v3` | `glm-4-air` |

---

## ✨ Features

<details>
<summary><b>Core Engine Features</b></summary>

- **🔀 16 Reasoning Methods** — From scientific hypothesis testing to Socratic elenchus
- **🧠 HyperGate Auto-Routing** — Automatic method selection with 6 parallel sub-agents
- **🌍 Cross-Lab Diversity** — Prevents echo chambers by routing phases to different model families
- **🔄 Intelligent Fallbacks** — Cross-lab fallback chains when providers fail
- **📊 Token & Cost Tracking** — Per-phase input/output tokens and model attribution streamed live
- **🛡️ Epistemic Labeling** — Every claim labeled `VERIFIED`, `HYPOTHESIS`, or `UNKNOWN` (Decomposition + Perspectives + Synthesis)
- **📝 Action Blueprints** — Structured Go/No-Go criteria with meta-cognitive audit
- **🔍 Web-Grounded Research** — Integrated SearXNG search with iterative RAG (covers historical, religious, and philosophical topics)
- **🧠 Neuro Memory** — Long-term memory with compression, embeddings, and tenant isolation
- **⚡ Real-Time Streaming** — SSE per-phase progress with typewriter synthesis effect
- **🌐 Multi-Language** — Auto-detects and responds in 10+ languages with dual-layer enforcement (system prompt + user prompt)
- **🔒 JSON Schema Hardening** — Strict perspective schema validation with graceful fallback for non-standard LLM outputs

</details>

<details>
<summary><b>Security & Reliability</b></summary>

- **Input Validation** — XSS stripping, null-byte removal, prompt-injection regex guards, unicode NFKC normalization
- **Rate Limiting** — Token-bucket + sliding window per client (configurable)
- **Authentication** — SHA-256 API key auth with scope-based authorization
- **CSRF Protection** — HMAC-signed tokens via Next.js proxy layer
- **Circuit Breakers** — Resilience patterns for external provider failures
- **Error Sanitization** — Generic messages to clients; detailed logging server-side
- **Security Headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Prompt Schema Validation** — Strict JSON schema enforcement for structured LLM outputs with defensive serialization fallback
- **Prompt Schema Validation** — Strict JSON schema enforcement for structured LLM outputs with defensive serialization fallback

</details>

<details>
<summary><b>Infrastructure</b></summary>

- **FastAPI Backend** — Async Python 3.12 with ~30 REST endpoints + WebSocket
- **Next.js 16 Frontend** — App Router, TypeScript 5, Tailwind CSS v4, Zustand state
- **CQRS / Event Sourcing** — SQLite (default) / PostgreSQL (optional) event stores
- **Caching Layers** — Disk JSON + in-memory + Neuro L1/L2/L3 hierarchy
- **Self-Healing CI/CD** — GitHub Actions with 4-loop introspection pipeline
- **Widget System** — Pluggable weather, stocks, calculator, discover, image/video search

</details>

---

## 📁 Project Structure

```
Reasoner/
├── main.py                          # CLI entry point
├── asgi.py                          # ASGI entry point (FastAPI)
├── start_all.py                     # Dev orchestrator (backend + frontend + docker)
├── requirements.txt                 # Python dependencies
├── docker-compose.searxng.yml       # SearXNG search engine
│
├── src/reasoner/
│   ├── api/                         # FastAPI HTTP/SSE interface (~30 endpoints)
│   ├── application/                 # CQRS commands, queries, event bus, handlers
│   ├── core/                        # Domain core: constants, settings, protocols, search
│   ├── hypergate/                   # Auto-method selector (6 sub-agents)
│   ├── infrastructure/              # Adapters: LLM ports, persistence, WebSocket, widgets
│   ├── neuro/                       # Persistent memory engine (L1/L2/L3 cache)
│   ├── subagents/                   # PhaseSubAgent v2.2 (critique, decomposition, etc.)
│   ├── healing/                     # Self-healing system + auto-generated tests
│   ├── pipeline.py                  # ARAPipeline orchestrator (~2,300 lines)
│   ├── llm.py                       # Multi-provider LLM abstraction
│   ├── models.py                    # PipelineState + 20+ dataclasses
│   ├── presets.py                   # 24+ PipelinePreset configs
│   ├── auth.py                      # API key authentication
│   ├── rate_limiter.py              # Token-bucket rate limiting
│   ├── sanitization.py              # Prompt-injection defense
│   └── phases.py                    # Phase prompt template library
│
├── ui-next/                         # Next.js 16 + React 19 + TypeScript 5
│   ├── src/app/                     # App Router pages + API proxy routes
│   ├── src/components/              # Chat, layout, phases, widgets, UI
│   ├── src/hooks/                   # usePipelineStream, useKeyboardShortcuts
│   ├── src/lib/                     # API client, security, IndexedDB
│   └── src/stores/                  # Zustand global state
│
├── tests/                           # pytest suite (~800 tests)
├── docs/                            # Additional documentation
├── cache/                           # Server-side response cache
└── uploads/                         # File upload storage
```

---

## 🔒 Security

- **Defense in Depth** — Multiple layers: input sanitization → auth → rate limiting → CSRF → header security
- **Prompt Injection Defense** — Regex-based pattern detection + truncation-aware checks
- **Path Traversal Protection** — TaggedMemory validates tag names against path traversal
- **Rate Limiting** — Per-client token buckets with sliding windows and hard caps
- **Memory Limits** — RSS guard middleware returns 503 before OOM kills
- **Request Timeouts** — 300s default (skipped for SSE streaming endpoints)

---

## 🛠️ Development

### Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# Quick run (skip slow/integration tests)
python -m pytest tests/ -v -m "not slow and not integration"

# With coverage
python -m pytest tests/ --cov=src/reasoner --cov-report=html
```

### Frontend Development

```bash
cd ui-next

# Type checking
npx tsc --noEmit

# Dev server
npm run dev

# Production build
npm run build

# E2E tests
npx playwright test
```

### Code Quality

```bash
# Python linting
ruff check src/reasoner/
ruff format src/reasoner/

# Frontend linting
cd ui-next && npm run lint
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [`ARCHITECTURE_MINDMAP.md`](ARCHITECTURE_MINDMAP.md) | **Complete architectural analysis** — structural, behavioral, domain, and infrastructure views |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture and design patterns |
| [`docs/METHODS.md`](docs/METHODS.md) | Reasoning method specifications |
| [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) | Implementation details and track records |
| [`docs/OPENROUTER_MIGRATION.md`](docs/OPENROUTER_MIGRATION.md) | Migrating from direct APIs to OpenRouter |
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Environment variable reference |
| [`SAAS.md`](SAAS.md) | SaaS roadmap and production deployment plan |
| [`TODO.md`](TODO.md) | Development roadmap and task tracking |

---

## 🤝 Contributing

Contributions are welcome! Please read our [TODO.md](TODO.md) for the current roadmap and open tasks.

### Quick Contribution Guide

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/amazing-feature`)
3. **Run tests** (`python -m pytest tests/ -x`)
4. **Commit** your changes (`git commit -m 'Add amazing feature'`)
5. **Push** to the branch (`git push origin feature/amazing-feature`)
6. **Open a Pull Request**

### Areas Where Help is Especially Welcome

- 🐳 **Docker deployment** — Full-stack `docker-compose.yml`
- 📊 **Observability** — Prometheus metrics, structured logging, distributed tracing
- 🧪 **Test coverage** — Expanding beyond the current ~70%
- 🌍 **i18n** — Additional language support and translation infrastructure
- 📱 **Mobile responsiveness** — Frontend UI improvements for smaller screens

---

## 🙏 Acknowledgments

- **OpenRouter** — For democratizing access to 350+ models through a single API
- **SearXNG** — For the privacy-respecting, self-hosted search engine
- **FastAPI** — For the modern, high-performance Python web framework
- **Next.js Team** — For the React framework that powers our frontend
- The broader **open-source LLM community** — For the rapid innovation in reasoning methodologies

---

## 📜 License

This project is released under the [MIT License](LICENSE).

> **Disclaimer**: This is a research and development tool. Outputs should be reviewed by human experts before making high-stakes decisions. The epistemic labels (`VERIFIED` / `HYPOTHESIS` / `UNKNOWN`) are heuristic estimates, not guarantees of factual correctness.

---

<div align="center">

**[⬆ Back to Top](#ara-pipeline-v22)**

Made with ❤️ and a lot of reasoning

</div>
