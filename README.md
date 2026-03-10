# ARA Pipeline v2.0
## Adaptive Reasoning Architecture — Orchestrated Multi-Phase LLM Pipeline

---

### Architecture

```
User Problem
     │
     ▼
Phase 0: Task Classification   [1 LLM call]
     │    → analytical / strategic / creative / technical / hybrid
     │    → Language detection for multi-language support
     ▼
Phase 1: Problem Decomposition [1 LLM call]
     │    → ≤5 sub-problems + assumption audit + failure modes
     ▼
Phase 2: Multi-Perspective     [4 PARALLEL LLM calls]
     │    → Constructive  → Various models
     │    → Destructive   → Various models
     │    → Systemic      → Various models
     │    → Minimalist    → Various models
     ▼
Phase 3: Critique & Pruning    [1 LLM call]
     │    → Score 0-10 per criterion
     │    → Keep top-k (default: 2)
     ▼
Phase 4: Stress Testing        [1 LLM call]
     │    → Optimal / Constraint Violation / Adversarial scenarios
     ▼
Phase 5: Synthesis             [1 LLM call]
          → VERIFIED/HYPOTHESIS/UNKNOWN labeled output
          → Action Blueprint with Go/No-Go criteria
          → Meta-Cognitive Audit
```

**Total: 8 LLM calls** (4 parallel in Phase 2)  
**State**: Persisted as `PipelineState` dataclass between phases  
**Languages**: Auto-detects Greek, Russian, Arabic, Chinese, Japanese, Korean, English

---

### Installation

```bash
pip install anthropic openai google-generativeai rich fastapi uvicorn pydantic
```

### Configuration

Create a `.env` file with your API keys:

```bash
# OpenAI
OPENAI_API_KEY="sk-..."

# Anthropic Claude
ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
GOOGLE_API_KEY="..."

# DeepSeek
DEEPSEEK_API_KEY="sk-..."

# Qwen/DashScope
DASHSCOPE_API_KEY="..."

# GLM/ZhipuAI
ZHIPUAI_API_KEY="..."

# Moonshot/Kimi
MOONSHOT_API_KEY="..."

# Mistral
MISTRAL_API_KEY="..."

# xAI/Grok
XAI_API_KEY="..."

# Perplexity
PERPLEXITY_API_KEY="..."
```

### Usage

```bash
# List available presets
python main.py --list-presets

# List available models
python main.py --list-models

# Run with default preset (cost-efficient)
python main.py --problem "How should we prioritize our product roadmap for Q3?"

# Run with specific preset
python main.py --problem "..." --preset max-quality
python main.py --problem "..." --preset eu-sovereign
python main.py --problem "..." --preset claude-only

# Custom routing
python main.py --problem "..." --routing '{"primary":"claude-sonnet","scoring":"sonar-pro"}'

# From file + export results
python main.py --problem-file problem.txt --output results.json --preset max-quality

# Sequential mode (rate-limited environments)
python main.py --problem "..." --sequential

# Control pruning
python main.py --problem "..." --top-k 3
```

### Web Interface

Start the API server:

```bash
uvicorn api:app --reload --port 8000
```

Then open `http://localhost:8000` in your browser.

### Programmatic Usage

```python
import asyncio
from pipeline import ARAPipeline
from llm import ProviderRouter

async def run():
    router = ProviderRouter.from_model_ids(
        primary_id="claude-sonnet",
        routing={"scoring": "sonar-pro", "synthesis": "glm-5"}
    )
    
    pipeline = ARAPipeline(router=router, top_k=2)
    state = await pipeline.run("Your problem here")

    # Access results
    print(state.task_type)
    print(state.decomposition.sub_problems)
    print(state.scores)
    print(state.final_solution.core_solution)
    print(state.final_solution.meta_audit.non_obvious_insight)

asyncio.run(run())
```

---

### Available Presets

| Preset | Primary Model | Description |
|--------|--------------|-------------|
| `cost-efficient` | deepseek-v3 | ~30x cheaper; pure Chinese OSS ecosystem |
| `max-quality` | claude-opus | Best model per phase; cross-ecosystem diversity |
| `debate` | claude-sonnet | Two models compete, third judges the winner |
| `evolutionary` | claude-opus | Generate N solutions → critique → select best → refine (up to 5 iterations) |
| `eu-sovereign` | mistral-large-3 | GDPR/AI Act compliant; Apache 2.0 |

---

### Design Decisions

| Decision | Rationale |
|---|---|
| 6-phase pipeline | Avoids context saturation, enables real pruning |
| Parallel Phase 2 | True independence between perspectives |
| Strict JSON output format | Parseable state for pipeline continuity |
| Fallbacks in every phase | Pipeline never hard-fails — degrades gracefully |
| Token budgets per phase | Prevents runaway generation |
| ClaimLabel on every output | Epistemic honesty built into the protocol |
| Multi-language support | Auto-detects and responds in user's language |
| Temperature=1.0 | Compatible with all models (some only support default) |
| No temperature parameter | Some models don't accept ANY temperature parameter |

---

### File Structure

```
Reasoner/
├── main.py                    # CLI entry point
├── api.py                     # FastAPI web server
├── pipeline.py                # Main orchestrator (6 phases)
├── models.py                  # Dataclasses and enums
├── llm.py                     # Multi-provider abstraction (10+ providers)
├── presets.py                 # Pre-built routing configurations
├── parsing.py                 # JSON extraction with repair logic
├── phases.py                  # Phase prompts with language detection
├── renderer.py                # Terminal output + JSON export
├── exceptions.py              # Structured exception taxonomy
├── ui/
│   └── index.html             # Single-page web interface
└── cache/                     # Server-side response cache
```

---

### Security Features

- **Input Validation**: Problem length limits, character validation
- **Rate Limiting**: API-level rate limiting (when enabled)
- **Error Handling**: Generic error messages to clients, detailed server logs
- **CORS**: Restricted to localhost origins
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, HSTS, etc.

---

### Error Handling

The pipeline includes comprehensive error handling:

- **Authentication Errors**: Shows which model requires API key
- **Model Not Found**: Clear error messages for invalid model IDs
- **Parse Errors**: Graceful fallback with partial data extraction
- **Network Errors**: Retry logic with exponential backoff
- **Rate Limits**: Automatic retry after cooldown period

---

### Caching

- **Server-side**: JSON cache in `cache/` directory
- **Client-side**: IndexedDB for conversation history persistence
- **Cache Keys**: SHA256 hash of problem + preset + parameters
- **Cache Clearing**: Via UI button or API endpoint

---

### Multi-Language Support

Automatically detects and responds in:
- English (default)
- Greek (Ελληνικά)
- Russian (Русский)
- Arabic (العربية)
- Chinese (中文)
- Japanese (日本語)
- Korean (한국어)

Language detection happens in Phase 0 and is used throughout all phases.
