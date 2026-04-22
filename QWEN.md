# ARA Pipeline — Project Context

## Project Overview

**ARA (Adaptive Reasoning Architecture) Pipeline v2.0** is a sophisticated multi-phase LLM orchestration system designed for complex problem-solving. It implements a structured reasoning protocol that decomposes problems, analyzes them from multiple perspectives, critiques solutions, stress-tests outcomes, and synthesizes final answers with epistemic honesty.

### Key Features

- **6-Phase Pipeline**: Classification → Decomposition → Multi-Perspective → Critique → Stress Testing → Synthesis
- **8 LLM Calls Total**: 4 parallel calls in Phase 2 for true perspective independence
- **Multi-Language Support**: Auto-detects Greek, Russian, Arabic, Chinese, Japanese, Korean, Spanish, German, Turkish, English
- **10+ LLM Providers**: Anthropic, OpenAI, Google, xAI, Perplexity, Mistral, DeepSeek, Qwen, Kimi, GLM, MiniMax
- **Graceful Degradation**: Pipeline never hard-fails; each phase has fallbacks
- **Persistent History**: IndexedDB storage for conversation history
- **Web UI**: Modern, responsive single-page application

### Architecture

```
User Problem
     │
     ▼
Phase 0: Task Classification     [1 LLM call]
     │    → Detects language, classifies problem type
     ▼
Phase 1: Problem Decomposition   [1 LLM call]
     │    → ≤5 sub-problems + assumption audit + failure modes
     ▼
Phase 2: Multi-Perspective       [4 PARALLEL LLM calls]
     │    → Constructive, Destructive, Systemic, Minimalist
     ▼
Phase 3: Critique & Pruning      [1 LLM call]
     │    → Score 0-10 per criterion, keep top-k (default: 2)
     ▼
Phase 4: Stress Testing          [1 LLM call]
     │    → Optimal / Constraint Violation / Adversarial scenarios
     ▼
Phase 5: Synthesis               [1 LLM call]
          → VERIFIED/HYPOTHESIS/UNKNOWN labeled output
          → Action Blueprint with Go/No-Go criteria
          → Meta-Cognitive Audit
```

---

## Directory Structure

```
Reasoner/
├── main.py                    # CLI entry point with preset/routing support
├── api.py                     # FastAPI backend with SSE streaming
├── pipeline.py                # 6-phase orchestrator with async execution
├── models.py                  # Dataclasses: PipelineState, SolutionCandidate, etc.
├── llm.py                     # Provider abstraction (10+ ecosystems, 40+ models)
├── presets.py                 # 10 pre-built routing configurations
├── parsing.py                 # JSON extraction with markdown fence handling
├── phases.py                  # Phase prompts with language detection
├── renderer.py                # Rich terminal output + JSON export
├── exceptions.py              # Structured exception taxonomy
├── cache/                     # Server-side response cache (JSON files)
├── .env                       # API keys configuration
└── README.md                  # User documentation
```

---

## Building and Running

### Installation

```bash
pip install anthropic openai google-generativeai mistralai rich fastapi uvicorn pydantic
```

### Configuration

Set API keys in `.env` file. See README.md for all supported providers.

### CLI Usage

```bash
# List presets with API key status
python main.py --list-presets

# List available models
python main.py --list-models

# Run with preset
python main.py --problem "..." --preset cost-efficient

# Custom routing
python main.py --problem "..." --routing '{"primary":"claude-sonnet","scoring":"sonar-pro"}'

# Export results
python main.py --problem "..." --output results.json
```

### Web UI

```bash
uvicorn asgi:app --reload --port 8000
# Open http://localhost:8001 (default port, configurable via SERVER_PORT)
```

### Programmatic Usage

```python
import asyncio
from pipeline import ARAPipeline
from llm import ProviderRouter

async def run():
    router = ProviderRouter.from_model_ids(
        primary_id="claude-sonnet",
        routing={"scoring": "sonar-pro"}
    )
    pipeline = ARAPipeline(router=router, top_k=2)
    state = await pipeline.run("Your problem here")
    print(state.final_solution.core_solution)

asyncio.run(run())
```

---

## Available Presets

| Preset | Primary | Description |
|--------|---------|-------------|
| `cost-efficient` | deepseek-v3 | ~30x cheaper; Chinese OSS ecosystem |
| `max-quality` | claude-opus | Best model per phase; epistemic diversity |
| `debate` | claude-sonnet | Multi-agent: 2 models compete, 1 judges |
| `evolutionary` | claude-opus | Generate N solutions → critique → refine (max 5 iterations) |
| `eu-sovereign` | mistral-large-3 | GDPR compliant; Apache 2.0; on-prem deployable |

---

## Development Conventions

### Code Style

- **Type Hints**: Full typing with `from __future__ import annotations`
- **Dataclasses**: All data structures use `@dataclass`
- **Async/Await**: All LLM calls are async with retry logic
- **Error Handling**: Graceful degradation with fallbacks at every phase

### Exception Taxonomy (`exceptions.py`)

- `ARAError` - Base exception with `retryable` flag
- `ParseError` - JSON extraction failures
- `ProviderError` hierarchy:
  - `AuthenticationError` - Invalid/missing API key
  - `RateLimitError` - Rate limit exceeded
  - `ModelNotFoundError` - Invalid model ID
  - `ProviderTimeoutError` - Request timeout
  - `ProviderUnavailableError` - Service unavailable

### Temperature Handling

All phases use `temperature=1.0` because:
- Some models only support the default temperature value
- Some models don't accept ANY temperature parameter
- Using 1.0 ensures compatibility across all providers

The provider layer omits the temperature parameter when it equals 1.0 to avoid "unsupported value" errors.

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | CLI with argparse, preset resolution, routing |
| `api.py` | FastAPI backend, SSE streaming, caching |
| `pipeline.py` | 6-phase orchestrator with error handling |
| `models.py` | PipelineState, 15+ dataclasses/enums |
| `llm.py` | Provider implementations, model registry |
| `presets.py` | PipelinePreset definitions |
| `phases.py` | Prompts with language detection |
| `parsing.py` | JSON extraction with repair logic |
| `renderer.py` | Terminal output, JSON export |
| `exceptions.py` | Exception hierarchy |

---

## Model Registry

The `_REGISTRY` dict in `llm.py` defines 40+ models across 10 ecosystems:

- **Anthropic**: claude-opus, claude-sonnet, claude-haiku
- **OpenAI**: gpt-5, gpt-5-mini, gpt-4o, o3, o3-mini
- **Google**: gemini-pro, gemini-flash
- **xAI**: grok-4, grok-3, grok-3-mini
- **Perplexity**: sonar-pro, sonar, sonar-deep-research
- **Mistral**: mistral-large-3, mistral-medium, codestral
- **DeepSeek**: deepseek-v3, deepseek-r1
- **Qwen**: qwen3-max, qwen3-plus, qwen3-turbo
- **Kimi**: kimi-k2, kimi-k2-5
- **GLM**: glm-5, glm-4-plus, glm-4-air

---

## UI Features

- **Centered Composer**: Large input area when idle
- **Bottom Composer**: Compact during execution
- **Conversation History**: IndexedDB persistence
- **Model Routing Display**: Shows which model handles each phase
- **Export Options**: Copy to clipboard or download JSON
- **Error Handling**: User-friendly error messages with model-specific hints

---

## Security Features

- **Input Validation**: Length limits, character validation
- **CORS**: Restricted to localhost origins
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, HSTS
- **Error Messages**: Generic client messages, detailed server logs
- **API Key Management**: Environment variables only, never client-side

---

## Notes

- All imports use root-level modules (no `core/`, `providers/`, `prompts/` subdirectories)
- Temperature parameter is omitted when value is 1.0 to avoid provider errors
- JSON parsing handles markdown fences, truncated responses, and malformed JSON
- Conversation history persists across browser restarts via IndexedDB
- Cache directory stores successful responses for faster re-runs

---

## Evaluation Architecture: Current vs. Lab-Style

### Current Implementation (ARA Pipeline)

The ARA pipeline is a **sequential 6-phase** reasoning architecture:

```
Problem → Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Solution
```

**Characteristics:**
- Linear execution with fallback routing
- Single critic model per phase
- 8 LLM calls total (4 parallel in Phase 2)
- No external tool integration (verification, search, code execution)
- Method-specific output rendering (STANDARD/DEBATE/EVOLUTIONARY/RESEARCH)

### Lab-Style Multi-Agent Evaluation (Not Yet Implemented)

Research teams at OpenAI, Anthropic, and DeepMind use a **parallel orchestration architecture**:

```
                    Orchestrator (LangGraph/Ray/Temporal)
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    Generation      Critique Agents   Verifiers
    (3+ models)   (3+ independent    (tools: search,
                    critics)          code exec, APIs)
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                   Scoring Engine
                   (numeric signals)
                         ▼
                  Meta-Evaluator
                (evaluates judges)
                         ▼
            Selection/Improvement Loop
```

**Key Differences from ARA:**

| Aspect | ARA Pipeline | Lab-Style |
|--------|---|---|
| **Orchestration** | Sequential phases | Parallel agents + state machine |
| **Generation** | 1 model per phase | 3+ models per step |
| **Critique** | 1 critic model | 3+ independent critics |
| **Verification** | Stress testing only | External tools (web search, code exec, symbolic validation) |
| **Scoring** | Phase-specific criteria | Numeric evaluation signals (factuality, reasoning, safety, helpfulness) |
| **Meta-Evaluation** | N/A | Evaluates quality of critics themselves |
| **Self-Improvement** | Manual synthesis | Automated critique-revise loops |
| **Evaluation Depth** | 6 phases | Hierarchical scoring with pairwise ranking |

### When Lab-Style Architecture Is Needed

Consider implementing this when ARA requirements expand to:
1. **Fact-checking**: Verify claims against web sources
2. **Code correctness**: Execute generated code before synthesis
3. **Adversarial robustness**: Multiple independent judges competing
4. **Automated improvement**: Iterative refinement loops without human intervention
5. **Research evaluation**: Benchmark datasets with ground truth
6. **Hybrid reasoning**: Mix symbolic verification with LLM reasoning

### Implementation Path (Future)

If implementing lab-style architecture:
1. Replace sequential `ARAPipeline` with `OrchestrationLayer` (LangGraph)
2. Create `GenerationPool` (3+ models, run in parallel)
3. Create `CritiquePool` (3+ critic models, independent scoring)
4. Add `VerificationTools` (retrieval, code execution, API validation)
5. Implement `ScoringEngine` (convert critiques to numeric signals)
6. Add `MetaEvaluator` (judge the judges)
7. Implement `ImprovementLoop` (critique → revise → re-score)

**Stack for implementation:**
- **Orchestration**: LangGraph (state machine) or Ray (distributed)
- **Evaluation**: DeepEval or OpenAI Evals framework
- **Observability**: LangSmith (tracing) + Weights & Biases (experiment tracking)
- **Verification**: Custom tools for domain-specific validation
