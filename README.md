# ARA Pipeline v2.2

**Adaptive Reasoning Architecture** — A dynamic, multi-method reasoning pipeline that orchestrates Large Language Models to decompose complex problems, generate multi-perspective solutions, critique rigorously, stress-test under adversarial conditions, and synthesize actionable recommendations.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js_16-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [Web Interface](#web-interface)
  - [Programmatic API](#programmatic-api)
- [Available Presets](#available-presets)
- [Reasoning Methods](#reasoning-methods)
- [Model Routing Philosophy](#model-routing-philosophy)
- [Features](#features)
- [Development](#development)
- [Project Structure](#project-structure)
- [Security](#security)
- [Caching](#caching)
- [Error Handling](#error-handling)
- [Multi-Language Support](#multi-language-support)

---

## Overview

ARA Pipeline is a production-grade reasoning engine for complex decision-making. Unlike simple chat completions, it decomposes problems into structured phases, leverages multiple LLMs in parallel from diverse training ecosystems, applies rigorous independent critique, stress-tests solutions, and synthesizes a final recommendation with epistemic labeling (`VERIFIED` / `HYPOTHESIS` / `UNKNOWN`) and an action blueprint.

### Key Capabilities

- **HyperGate Pre-Router**: Five focused sub-agents run in parallel before any pipeline starts — detecting language, complexity, directness, web-search need, and optimal reasoning method. Simple questions are answered immediately; complex ones are routed to the right method automatically.
- **Multi-Phase Orchestration**: 6 core phases from classification to synthesis
- **Specialized Reasoning Methods**: 16 methodologies — Scientific, Socratic, Debate, Jury, Bayesian, Delphi, Chain-of-Verification, Skeleton-of-Thought, Tree-of-Thoughts, Program-of-Thoughts, Self-Discover, and more
- **Cross-Lab Diversity**: Each phase routes to a different model family to prevent echo chambers and maximize epistemic coverage
- **Intelligent Fallbacks**: Automatic cross-lab fallback routing when a provider fails — never falls back blindly to a single primary
- **Real-Time Streaming**: Server-Sent Events (SSE) deliver per-phase progress, token usage, and model attribution
- **Web-Grounded Research**: Integrated SearXNG search for evidence-based reasoning
- **Persistent Memory**: Neuro-based long-term memory with compression and tenant isolation

---

## Architecture

### HyperGate Agent (Pre-Pipeline Router)

Every request passes through the HyperGate before any reasoning pipeline starts. Five specialized sub-agents run **in parallel** (Phase 1), and a TieBreakerSubAgent resolves conflicts if needed (Phase 2).

```
User Problem
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HyperGateAgent (Phase 1 — parallel)          │
│                                                                 │
│  LanguageDetector  ComplexityEstimator  DirectDetector          │
│       (lang?)          (simple/med/     (pipeline needed?       │
│                         complex?)        or answer directly?)   │
│                                                                 │
│  WebSearchDetector      MethodClassifier                        │
│  (real-time data        (which of 16 methods:                   │
│   needed?)               debate/scientific/tot/…?)             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ synthesize()  (pure Python, no LLM)
          ┌────────────────┼────────────────┐
          │ DIRECT         │ WEB_SEARCH     │ PIPELINE
          ▼                ▼                ▼
  Answer immediately  Run live search  Full ARA Pipeline
  (no pipeline)       and return       (method auto-selected)
                      results
```

**Fail-safe design**: any sub-agent error becomes a graceful fallback — never a crash.  
**Security**: real method names are never exposed to the LLM. Only opaque letters (B–Q) appear in sub-agent prompts.  
**Caching**: per-sub-agent LRU cache (512 entries) + top-level HyperGateAgent cache for repeat problems.

### Core Pipeline (6 Phases)

```
User Problem  (routed here by HyperGateAgent when action = "pipeline")
     │
     ▼
Phase 0: Task Classification
     │    → Classifies task type (analytical, strategic, creative, technical, hybrid)
     │    → Auto-detects language for multi-language synthesis
     ▼
Phase 1: Problem Decomposition
     │    → Generates ≤5 sub-problems, assumption audit, and failure modes
     ▼
Phase 2: Multi-Perspective Generation
     │    → Constructive, Destructive, Systemic, and Minimalist perspectives
     │    → Executed in parallel across diverse models from different labs
     ▼
Phase 3: Critique & Pruning
     │    → Scores candidates 0-10 per criterion using an independent model
     │    → Retains top-k solutions (default: 2)
     ▼
Phase 4: Stress Testing
     │    → Evaluates under Optimal, Constraint Violation, and Adversarial scenarios
     ▼
Phase 5: Synthesis
          → Produces VERIFIED / HYPOTHESIS / UNKNOWN labeled output
          → Generates Action Blueprint with Go/No-Go criteria
          → Includes Meta-Cognitive Audit
```

**Total**: 8 LLM calls per run (4 parallel in Phase 2) for standard methods; varies by method  
**State Management**: Immutable `PipelineState` dataclass persisted between phases  
**Languages**: Auto-detects and responds in 10+ languages  
**Post-Synthesis Verification**: Optional cross-model fact-checking for CoVe presets

---

## Quick Start

OpenRouter is the recommended configuration — a single API key provides access to 350+ models.

### 1. Obtain an OpenRouter API Key

Visit [https://openrouter.ai/keys](https://openrouter.ai/keys) to create an account and generate a key.

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Run the Pipeline

```bash
# Recommended default — balanced quality and cost
python main.py --problem "How should we prioritize our product roadmap for Q3?" --preset multi-perspective-budget

# Budget option — approximately $0.02 per run
python main.py --problem "..." --preset debate-budget

# Maximum quality — premium models with 4-lab diversity
python main.py --problem "..." --preset multi-perspective-premium
```

### 4. Start the Web Interface

```bash
# Terminal 1 — Backend
uvicorn asgi:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (Next.js)
cd ui-next
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 20+ (for the Next.js frontend)
- An API key from OpenRouter or individual providers

### Backend

```bash
# Clone or navigate to the repository
cd Reasoner

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend

```bash
cd ui-next
npm install
```

---

## Configuration

### Option 1: OpenRouter (Recommended)

The simplest configuration requires only one key:

```bash
OPENROUTER_API_KEY="sk-or-v1-..."
```

Benefits:
- Single API key for 350+ models
- Simplified billing and key management
- Cross-ecosystem diversity with automatic routing

### Option 2: Individual Provider Keys

If you prefer direct provider access, add the relevant keys to `.env`:

```bash
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
GOOGLE_API_KEY="..."
DEEPSEEK_API_KEY="sk-..."
DASHSCOPE_API_KEY="..."
ZHIPUAI_API_KEY="..."
MOONSHOT_API_KEY="..."
MISTRAL_API_KEY="..."
XAI_API_KEY="..."
PERPLEXITY_API_KEY="..."
OLLAMA_API_KEY="..."
```

You may also mix both approaches — OpenRouter for most models and direct keys where needed.

### Optional: SearXNG Search

For web-grounded reasoning, configure a SearXNG instance:

```bash
SEARXNG_URL="http://localhost:8080"
```

A Docker Compose file is provided for quick setup:

```bash
docker-compose -f docker-compose.searxng.yml up -d
```

---

## Usage

### CLI

```bash
# List available presets
python main.py --list-presets

# List available models
python main.py --list-models

# Run with default preset
python main.py --problem "How should we prioritize our product roadmap for Q3?"

# Run with a specific preset
python main.py --problem "..." --preset multi-perspective-budget

# Custom routing per role
python main.py --problem "..." --routing '{"primary":"claude-sonnet","scoring":"sonar-pro"}'

# Load problem from file and export results
python main.py --problem-file problem.txt --output results.json --preset multi-perspective-premium

# Sequential mode for rate-limited environments
python main.py --problem "..." --sequential

# Adjust pruning threshold
python main.py --problem "..." --top-k 3
```

### Web Interface

The web interface provides a chat-like experience with:
- Real-time SSE streaming of phase progress
- Per-phase token usage and model attribution
- Interactive preset and method selection
- Persistent conversation history

```bash
uvicorn asgi:app --reload --host 0.0.0.0 --port 8000
cd ui-next && npm run dev
```

### Programmatic API

```python
import asyncio
from pipeline import ARAPipeline
from llm import ProviderRouter

async def main():
    router = ProviderRouter.from_model_ids(
        primary_id="claude-sonnet",
        routing={"scoring": "sonar-pro", "synthesis": "glm-5"}
    )

    pipeline = ARAPipeline(router=router, top_k=2)
    state = await pipeline.run("Your complex problem here")

    print(state.task_type)
    print(state.decomposition.sub_problems)
    print(state.scores)
    print(state.final_solution.core_solution)
    print(state.final_solution.meta_audit.non_obvious_insight)

asyncio.run(main())
```

---

## Available Presets

Every method has a **Budget** and a **Premium** variant. The Budget tier emphasizes cross-lab diversity at the lowest possible cost (~$0.02/run). The Premium tier uses best-in-class models with explicit cross-lab fallback routing for maximum reliability and epistemic breadth (~$0.15–$0.30/run).

### All Method Presets

| Preset | Tier | Primary | Phase 2 Diversity |
|--------|------|---------|-------------------|
| `multi-perspective-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `multi-perspective-premium` | Premium | `claude-opus` | Kimi + DeepSeek + Claude + Mistral |
| `iterative-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `iterative-premium` | Premium | `claude-opus` | Claude + DeepSeek + Gemini + Sonar |
| `debate-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `debate-premium` | Premium | `claude-sonnet` | GPT-5 + Claude + DeepSeek |
| `scientific-budget` | Budget | `sonar` | DeepSeek + Qwen + GLM |
| `scientific-premium` | Premium | `sonar-pro` | Sonar Deep Research + Claude + DeepSeek |
| `socratic-budget` | Budget | `deepseek-v3` | DeepSeek + Qwen + GLM |
| `socratic-premium` | Premium | `deepseek-v3` | Kimi + DeepSeek + GLM + Qwen |
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

### Specialized Method Presets

| Preset | Method | Description |
|--------|--------|-------------|
| `multi-perspective-budget` / `multi-perspective-premium` | Multi-Perspective | Default 6-phase pipeline with cross-lab perspective generation |
| `iterative-budget` / `iterative-premium` | Iterative Refinement | Multi-round generate → critique → refine cycles |
| `debate-budget` / `debate-premium` | Debate | Two models compete; a third judges the winner |
| `scientific-budget` / `scientific-premium` | Scientific | Hypothesis generation, falsification tests, and evidence scoring |
| `socratic-budget` / `socratic-premium` | Socratic | Elenchus questioning to expose assumptions and clarify definitions |
| `research-budget` / `research-premium` | Research | Web-grounded deep research with iterative SearXNG search |
| `jury-budget` / `jury-premium` | Jury | Multiple generators scored by an independent panel of critics |
| `pre-mortem-budget` / `pre-mortem-premium` | Pre-Mortem | Prospective failure analysis (Gary Klein methodology) |
| `bayesian-budget` / `bayesian-premium` | Bayesian | Prior → likelihood → posterior → sensitivity |
| `dialectical-budget` / `dialectical-premium` | Dialectical | Thesis → antithesis → Aufhebung |
| `analogical-budget` / `analogical-premium` | Analogical | Structure-mapping and cross-domain transfer |
| `delphi-budget` / `delphi-premium` | Delphi | Expert consensus with convergence tracking |
| `cove-budget` / `cove-premium` | Chain-of-Verification | Draft → verify → answer → revise (structured fact-checking) |
| `sot-budget` / `sot-premium` | Skeleton-of-Thought | Skeleton → parallel solve → assemble (latency reduction) |
| `tot-budget` / `tot-premium` | Tree-of-Thoughts | Decompose → generate → evaluate → backtrack (planning) |
| `pot-budget` / `pot-premium` | Program-of-Thoughts | Code generation → execution → interpretation (quantitative) |
| `self-discover-budget` / `self-discover-premium` | Self-Discover | Dynamic reasoning module composition |

---

## Reasoning Methods

ARA Pipeline supports multiple specialized reasoning methodologies beyond the default orchestrated pipeline:

| Method | Description |
|--------|-------------|
| **Orchestrated** | Default 6-phase pipeline with multi-perspective generation |
| **Debate** | Two models compete; a third judges the winner |
| **Scientific** | Hypothesis generation, falsification tests, and evidence scoring |
| **Socratic** | Elenchus questioning to expose assumptions and clarify definitions |
| **Jury** | Multiple generators scored by an independent panel of critics |
| **Research** | Web-grounded deep research with iterative SearXNG search |
| **Pre-Mortem** | Prospective hindsight failure analysis |
| **Bayesian** | Prior-likelihood-posterior-sensitivity reasoning |
| **Dialectical** | Hegelian thesis-antithesis-synthesis progression |
| **Analogical** | Structure-mapping and cross-domain transfer |
| **Delphi** | Expert consensus with convergence tracking |
| **Chain-of-Verification** | Structured fact-checking: draft → verify → answer → revise |
| **Skeleton-of-Thought** | Parallel decomposition: skeleton → parallel solve → assemble |
| **Tree-of-Thoughts** | Reasoning as tree search with candidate evaluation and backtracking |
| **Program-of-Thoughts** | Executable code as intermediate reasoning (Python generation + execution) |
| **Self-Discover** | Dynamic selection and composition of reasoning modules per problem |

---

## Model Routing Philosophy

### Why Cross-Lab Diversity Matters

Different model families are trained on different data distributions, reward functions, and safety paradigms. When multiple perspectives (Phase 2) or critiques (Phase 3) come from the **same lab**, the pipeline converges to an **echo chamber** — the models agree on the same hidden assumptions and miss the same blind spots.

### Our Design Rules

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

## Features

- **Token & Cost Tracking**: Per-phase input/output token counts and model attribution streamed live via SSE
- **Cross-Lab Fallbacks**: If a provider fails, the pipeline retries with an alternative model from a different training ecosystem
- **Structured JSON Protocol**: Strict output schemas ensure parseable, pipeline-continuous state
- **Epistemic Labeling**: Every claim is labeled `VERIFIED`, `HYPOTHESIS`, or `UNKNOWN`
- **Token Budgets**: Per-phase generation limits prevent runaway costs
- **Neuro Memory**: Long-term memory with `Recall` (bootstrap) and `Learn` (ingest) endpoints
- **Compression**: Automatic context compression to optimize token usage

---

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Building the Frontend

```bash
cd ui-next
npm run build
```

### Linting and Type Checking

```bash
cd ui-next
npx tsc --noEmit
```

---

## Project Structure

```
Reasoner/
├── main.py                    # CLI entry point
├── api.py                     # FastAPI server with SSE streaming
├── pipeline.py                # Core orchestrator (ARAPipeline)
├── gate_agent.py              # Legacy GateAgent + HyperGateAgent re-export
├── models.py                  # Dataclasses, enums, and state persistence
├── llm.py                     # Multi-provider LLM abstraction
├── presets.py                 # Pre-built routing configurations
├── parsing.py                 # JSON extraction and repair logic
├── phases.py                  # Phase prompts and language detection
├── renderer.py                # Terminal output and JSON export
├── exceptions.py              # Structured exception taxonomy
├── hypergate/                 # HyperGate multi-agent pre-router
│   ├── hyperagent.py          # HyperGateAgent orchestrator (Phase 1 + 2)
│   ├── base_sub_agent.py      # BaseSubAgent ABC with cache + LLM wiring
│   ├── models.py              # SubAgentInput, SubAgentOutput, HyperContext
│   └── sub_agents/
│       ├── language_detector.py     # Detects input language
│       ├── complexity_estimator.py  # simple / medium / complex
│       ├── direct_detector.py       # Is a pipeline needed at all?
│       ├── web_detector.py          # Is real-time web data needed?
│       ├── method_classifier.py     # Opaque taxonomy B–Q → method name
│       └── tie_breaker.py           # Phase 2: resolve ambiguous Phase 1
├── neuro/                     # Neuro memory and compression modules
├── ui-next/                   # Next.js 16 frontend
│   ├── src/app/page.tsx
│   ├── src/components/
│   └── package.json
├── tests/                     # pytest suite
├── cache/                     # Server-side response cache
└── docs/                      # Additional documentation
```

---

## Security

- **Input Validation**: Problem length limits and character sanitization
- **Rate Limiting**: Configurable API-level rate limiting
- **CORS Restriction**: Limited to localhost origins in development
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options, and more
- **Error Sanitization**: Generic error messages to clients; detailed logging on the server

---

## Caching

- **Server-Side**: JSON cache in `cache/` keyed by SHA256 hash of problem + preset + parameters
- **Client-Side**: IndexedDB for conversation history in the browser
- **Cache Invalidation**: Automatic versioning ensures stale caches are discarded on protocol updates
- **Manual Clearing**: Available via the UI or the `/api/cache` endpoint

---

## Error Handling

The pipeline is designed to degrade gracefully rather than fail hard:

- **Authentication Errors**: Identifies which model requires an API key
- **Model Not Found**: Returns clear, actionable error messages for invalid model IDs
- **Parse Errors**: Graceful fallback with partial data extraction and repair logic
- **Network Errors**: Exponential backoff retry logic
- **Rate Limits**: Automatic cooldown and retry

---

## Multi-Language Support

Language detection occurs in Phase 0 and is propagated throughout all subsequent phases. Supported languages include:

- English (default)
- Greek (Ελληνικά)
- Russian (Русский)
- Arabic (العربية)
- Chinese (中文)
- Japanese (日本語)
- Korean (한국어)
- Spanish (Español)
- German (Deutsch)
- Turkish (Türkçe)

---

## Documentation

- [`OPENROUTER_MIGRATION.md`](docs/OPENROUTER_MIGRATION.md) — Migrating from direct APIs to OpenRouter
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture and design patterns
- [`METHODS.md`](docs/METHODS.md) — Reasoning method specifications
- [`IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — Implementation details and track records
- [`tasks/model_optimization_plan.md`](tasks/model_optimization_plan.md) — Phase-by-phase model routing optimization plan

---

## License

This project is provided as-is for research and development purposes.
