# Vibe-Coding Reasoner

Multi-phase reasoning pipeline for structured adversarial thinking. You give it a problem statement, it runs 6 sequential LLM calls: classifies task type → decomposes into sub-problems → generates 4 parallel "perspectives" (constructive/destructive/systemic/minimalist) → scores + prunes → stress-tests survivors → synthesizes final answer. Designed for complex decisions and deep analysis, not code generation.

## Quick Start

```bash
# Requires ANTHROPIC_API_KEY environment variable
python main.py --problem "Should I rewrite our backend in Rust?" --preset claude-only

# Discovery (no API key needed)
python main.py --list-presets
python main.py --list-models

# Run with sequential phase execution (avoids rate limiting)
python main.py --problem "Your problem here" --sequential

# Note: python main.py alone will error — requires --problem or --problem-file
```

## Project Structure

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point; orchestrates pipeline execution |
| `pipeline.py` | Core pipeline logic; manages phase execution flow |
| `phases.py` | Processing phases (reasoning, generation, analysis, etc.) |
| `llm.py` | LLM integration; API calls and prompt handling |
| `models.py` | Data models; input/output types for each phase |
| `parsing.py` | Output parsing; extract structured results from LLM responses |
| `renderer.py` | Result formatting; method-specific rendering (STANDARD/DEBATE/EVOLUTIONARY/RESEARCH) |
| `presets.py` | Configuration presets; model params, prompt templates, etc. |

## The 6-Phase Pipeline

1. **Classification** — Determines task type (strategic/tactical/creative/analytical)
2. **Decomposition** — Breaks problem into sub-problems
3. **Perspective Generation** — 4 parallel LLM calls (constructive/destructive/systemic/minimalist)
4. **Scoring & Pruning** — Ranks perspectives, keeps best N
5. **Stress Testing** — Challenges survivors with edge cases
6. **Synthesis** — Combines results into final answer

All output is JSON. Each phase's output becomes the next phase's input via models defined in `models.py`. Presets define which provider/model to use for each phase — can mix providers per phase if you want (though not recommended).

## Development Workflow

### Tweaking a Phase
- Edit prompt in `presets.py` → test with `--preset <name>`
- Adjust temperature/max_tokens in `presets.py`
- Watch for JSON parsing failures in output

### Adding a New Provider
1. Subclass `BaseLLMProvider` in `llm.py`
2. Implement `complete()` method
3. Register in provider registry
4. Add to `--list-models` discovery
5. Test carefully — JSON extraction will likely break first

### Debugging a Phase Failure
1. Run with `--sequential` (slower but clearer which phase fails)
2. Check if output is valid JSON (often isn't with non-Claude providers)
3. Verify `PerspectiveType` enum keys match preset routing
4. Check API key / rate limits

## Environment

**Install dependencies:**
```bash
pip install anthropic openai mistralai rich
# Optional: Google Gemini support
pip install google-generativeai
```

**No pinned versions** — anthropic and openai SDKs break frequently. If something fails, check `pip show anthropic` and ensure you have ≥0.40.

**Required env vars:**
- `ANTHROPIC_API_KEY` — Primary provider, this is what the pipeline was built against

**Optional env vars (for other providers):**
- `OPENAI_API_KEY` (untested in this pipeline)
- `MISTRAL_API_KEY` (untested in this pipeline)
- `GOOGLE_API_KEY` (untested in this pipeline)
- `DEBUG=1` for verbose logging

## Method-Specific Output

The pipeline dispatches to different renderers based on the preset used, producing tailored output for each reasoning method:

| Method | Presets | Output Format | Best For |
|--------|---------|---|---|
| **STANDARD** | claude-only, max-quality, epistemic-diversity, etc. | Structured analysis: classification → decomposition → scores → stress tests → solution | General analysis, strategy, design decisions |
| **DEBATE** | debate, debate-budget | Arena format: Proposition vs Opposition scorecards → Winner → Verdict | Adversarial thinking, comparing trade-offs |
| **EVOLUTIONARY** | evolutionary, evolutionary-budget | Population genetics: fitness evaluation → survivors → optimized solution | Iterative refinement, fitness-based selection |
| **RESEARCH** | research | Evidence report: quality matrix → claim verification → evidence gaps | Empirical questions, fact-checking, grounded analysis |

Each method adapts the narrative and emphasizes different data:
- **DEBATE**: Shows side-by-side scores, identifies winner, highlights steel_man counter-arguments
- **EVOLUTIONARY**: Fitness table with [SURVIVOR]/[ELIMINATED] tags, emergent properties
- **RESEARCH**: Evidence quality highlighted, claim labels (VERIFIED/HYPOTHESIS/UNKNOWN), evidence gaps flagged

Example commands:
```bash
python main.py --problem "..." --preset debate            # Debate arena output
python main.py --problem "..." --preset evolutionary      # Evolutionary optimization output
python main.py --problem "..." --preset research          # Evidence synthesis report
```

## Common Tasks

| Task | Command |
|------|---------|
| Run with Claude (works reliably) | `python main.py --problem "..." --preset claude-only` |
| Run in debate mode | `python main.py --problem "..." --preset debate` |
| Run in evolutionary mode | `python main.py --problem "..." --preset evolutionary` |
| Run in research mode (Sonar grounded) | `python main.py --problem "..." --preset research` |
| Avoid rate limits | Add `--sequential` flag |
| List available presets | `python main.py --list-presets` |
| List available models | `python main.py --list-models` |
| Test a single phase | Add debug/breakpoint in `phases.py` |
| Add new preset | Edit `presets.py`, add to PRESETS dict (watch PerspectiveType keys) |
| Try another provider | Set API key, use `--preset openai-only` (but expect JSON parsing issues) |

## Testing

**Current state: No pytest. No automated tests.** Manual testing only: run against Claude with a real problem, check the Rich terminal output, verify the JSON makes sense.

**If you want to add tests (high-leverage approach):**
Mock `BaseLLMProvider.complete()` and feed it controlled JSON responses. Assert `PipelineState` fields are populated correctly after each phase.

**Manual testing:**
```bash
export ANTHROPIC_API_KEY="your-key"
python main.py --problem "Your test problem" --preset claude-only
# Verify output makes sense, JSON is well-formed, all 6 phases complete
```

## Gotchas & Real Issues

**Critical:**
1. **JSON parsing is fragile.** Every phase expects JSON from the LLM. Claude usually returns clean JSON. Other providers wrap it in markdown, add prose preamble, or use slightly different schemas. `core/parsing.py:extract_json()` handles markdown fences but not all variations. Non-Claude providers will likely fail Phase 1+ on first run.

2. **Chinese provider endpoints are unverified.** Kimi (api.moonshot.cn), GLM (open.bigmodel.cn), MiniMax (api.minimax.chat), Qwen (dashscope.aliyuncs.com) — pulled from docs, never live-tested. Endpoint paths, auth headers, model names change frequently.

3. **Perplexity Sonar breaks the pipeline.** Sonar is search-augmented and appends citation text to responses. JSON extraction will fail. You'd need Sonar-specific post-processing before Phase 3.

4. **Phase 2 rate limits.** 4 parallel API calls hit rate limiting on free tiers. `--sequential` flag exists but wasn't stress-tested.

5. **PerspectiveType mismatches are silent.** If a preset routes "constructive" but the enum value changed, the router falls back to primary without warning. You won't know a phase used the wrong model.

6. **No timeout per phase.** A hung API call blocks the entire pipeline indefinitely.

**Less critical:**
- Other providers are wired up in the registry but never live-tested — only the abstraction layer was written
- `state/` directory is scaffolded but empty — no state persistence implemented

## Key Files to Know

- `main.py:main()` — Entry point; orchestrates all 6 phases, passes preset_name to pipeline
- `pipeline.py` — `PipelineState` and phase sequencing; `ARAPipeline` tracks preset for method-aware rendering
- `phases.py` — Each of the 6 phase implementations; synthesis prompt receives method hint (debate/evolutionary/research)
- `llm.py` — `BaseLLMProvider` abstraction and all provider implementations; fallback routing on provider failure
- `models.py` — Data models (input/output for each phase); `PipelineState` now carries `preset_name` for renderer dispatch
- `presets.py:PRESETS` — Provider routing and LLM parameters; fallback_routing per preset for resilience
- `parsing.py` — JSON extraction from LLM responses (the fragile part)
- `renderer.py` — Method-specific rendering dispatched by `MethodType`; STANDARD/DEBATE/EVOLUTIONARY/RESEARCH layouts

## Performance & Cost

- **Phase 2 is expensive.** 4 parallel perspective calls = 4x the tokens (and cost) of a single sequential call. Use `--sequential` or limit perspectives in presets.
- **Each phase calls the LLM once** (except Phase 2). Full run ~6 API calls. Claude 3.5 Sonnet via Anthropic API is reasonably fast; others TBD.
- **No caching.** Every run is fresh. Consider adding output caching if you run the same problem twice.

## When Things Break

1. **JSON parsing error** → Non-Claude provider or LLM schema drift. Check `parsing.py:extract_json()`.
2. **Rate limit hit** → Add `--sequential`. Consider batching runs.
3. **Silent provider mismatch** → Check `PerspectiveType` enum keys in presets.
4. **"Model not found" error** → Verify model name in presets matches provider's actual model list.
5. **Hung pipeline** → Provider is slow/down. No timeout mechanism exists — kill it and retry.
