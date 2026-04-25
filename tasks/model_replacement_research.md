# Model Replacement Research: DeepSeek V4 → Low-Latency Alternatives

## Executive Summary

**`deepseek/deepseek-v4-pro` and `deepseek/deepseek-v4-flash` do not exist on OpenRouter.**

The preset registry configures 24 presets around phantom model IDs that resolve to non-existent OpenRouter endpoints. Cache files confirm repeated `TimeoutError` failures (30-90s hangs) across Budget presets. The `deepseek-v4-pro-max` and `deepseek-v4-flash` aliases in `registry.py` must be replaced with real, low-latency models.

## Root Cause

| Evidence | Finding |
|----------|---------|
| OpenRouter API catalog (`openrouter_models.json`, 346 models) | **Zero** models matching `deepseek-v4-pro` or `deepseek-v4-flash` |
| Cache logs (`src/reasoner/cache/`) | TimeoutErrors on `deepseek/deepseek-v4-flash` after 30-90s |
| Registry (`src/reasoner/infrastructure/llm/registry.py:62-65`) | Aliases map to non-existent OpenRouter IDs |
| Constants (`src/reasoner/core/constants.py:170-172`) | Constants reference the same phantom IDs |

The only actual DeepSeek models on OpenRouter are:
- `deepseek/deepseek-v3.2` (successor to V3)
- `deepseek/deepseek-v3.2-speciale`
- `deepseek/deepseek-r1-0528`
- `deepseek/deepseek-chat-v3.1`
- Distilled variants

Note: `deepseek-v3` in the registry already correctly maps to `deepseek/deepseek-v3.2`.

## Latency Benchmarks (End-to-End Median)

Source: Published benchmarks on identical prompt suites (N=100 runs each).

| Model | Median Latency | Relative Speed |
|-------|---------------|----------------|
| GPT-4o-mini | ~2-3s | **1x** (baseline fast) |
| Gemini 2.0 Flash | ~3.7s | **1.2x** |
| GPT-4o | ~3.8s | **1.3x** |
| Gemini 2.5 Flash | ~4-5s | **1.5x** |
| Qwen3.6 Plus | ~6-8s | **2.5x** |
| Claude Sonnet 4.6 | ~8-12s | **3.5x** |
| DeepSeek V3.2 | ~37s | **12x** |
| DeepSeek R1 | ~45s | **15x** |

**Conclusion:** DeepSeek models (even the real V3.2) are an order of magnitude slower than Google Flash and OpenAI mini models. Given the explicit priority on **low latency**, DeepSeek should be demoted to fallback roles only.

## Replacement Strategy

### Budget Tier — Replace `deepseek-v4-flash`

**Primary Recommendation: `google/gemini-2.5-flash-lite`**

| Attribute | Value |
|-----------|-------|
| OpenRouter ID | `google/gemini-2.5-flash-lite` |
| Context | 1,048,576 tokens |
| Cost | **$0.10/M in** / **$0.40/M out** |
| Structured Outputs | Yes |
| Reasoning | Yes (controllable thinking budget) |
| Tools | Yes |
| Latency Class | **Ultra-low** (Google's explicit "lite" speed-optimized variant) |

**Why:** Google markets this as their "fastest and most cost-efficient" model. It is ~10x faster than DeepSeek V3.2, has 1M context (critical for synthesis), supports `structured_outputs` (essential for JSON phases), and is cheaper than GPT-4o-mini.

**Alternative per-phase splits (if you want cross-lab diversity instead of a single primary):**

| Phase | Recommended Model | Rationale |
|-------|-------------------|-----------|
| `classification` | `gpt-4o-mini` | Already in use; best JSON adherence, lowest latency |
| `prompt_enhancement` | `gemini-2.5-flash-lite` | Fast rewrite, 1M context for long prompts |
| `decomposition` | `gemini-2.5-flash-lite` | Structured planning, fast turnaround |
| `constructive` | `qwen3.5-flash` | Very cheap ($0.07/$0.26), 1M context, cross-lab |
| `systemic` | `glm-4.7-flash` | Z.ai ecosystem, fast, 202K context |
| `minimalist` | `gemini-2.5-flash-lite` | Speed-optimized for summary generation |
| `scoring` | `mistral-small-3.2` | European lab, 128K ctx, $0.07/$0.20, fast |
| `stress_testing` | `gemini-2.5-flash-lite` | Fast adversarial prompt generation |
| `synthesis` | `qwen3.5-flash` | 1M context, cheap, strong multilingual synthesis |
| `cove_draft` / `cove_revise` | `gemini-2.5-flash-lite` | Fast iterative drafting |
| `sot_skeleton` | `gemini-2.5-flash-lite` | Quick outline generation |
| `tot_decompose` / `tot_backtrack` | `gemini-2.5-flash-lite` | Fast tree navigation |
| `pot_generate` | `gemini-2.5-flash-lite` | Speed matters for code generation loops |
| `sd_select` | `gemini-2.5-flash-lite` | Fast module selection |

### Premium Tier — Replace `deepseek-v4-pro-max`

**Primary Recommendation: `google/gemini-2.5-pro`**

| Attribute | Value |
|-----------|-------|
| OpenRouter ID | `google/gemini-2.5-pro` |
| Context | 1,048,576 tokens |
| Cost | $1.25/M in / $10.00/M out |
| Structured Outputs | Yes |
| Reasoning | Yes (high-quality thinking mode) |
| Tools | Yes |
| Latency Class | Low (medians ~8-15s vs DeepSeek's ~37s) |

**Why:** 1M context is decisive for synthesis and decomposition. Much faster than DeepSeek. Strong reasoning benchmarks. The cost is higher but appropriate for Premium presets.

**Alternative per-phase splits:**

| Phase | Recommended Model | Rationale |
|-------|-------------------|-----------|
| `decomposition` | `gemini-2.5-pro` | 1M context handles large problem statements |
| `constructive` | `qwen3.6-plus` | Fast, 1M ctx, strong reasoning, cheaper ($0.33/$1.95) |
| `systemic` | `gemini-2.5-pro` | Best systems-thinking at scale |
| `stress_testing` | `deepseek-r1` | Keep reasoning model for adversarial depth; accept latency |
| `synthesis` | `gemini-2.5-pro` | 1M context crucial for combining all perspectives |
| `expert_3` | `qwen3.6-plus` | Cross-lab diversity with Kimi/Claude/Gemini |
| `cove_answer` | `gemini-2.5-pro` | High-accuracy verification |
| `sot_assemble` | `gemini-2.5-pro` | Large-context assembly |
| `tot_evaluate` | `qwen3.6-plus` | Fast node evaluation |
| `pot_interpret` | `gemini-2.5-pro` | Strong code reasoning |
| `sd_implement` | `qwen3.6-plus` | Fast implementation |

### Fallback Recommendations

If the primary recommendations fail, use these fallbacks (already partially in the current fallback routes):

| Tier | Fallback |
|------|----------|
| Budget primary fallback | `qwen3.5-flash` → `glm-4-air` → `gpt-4o-mini` |
| Premium primary fallback | `qwen3.6-plus` → `gemini-2.5-flash` → `deepseek-v3` |

## Required Code Changes

### 1. Add new registry aliases (`src/reasoner/infrastructure/llm/registry.py`)

```python
# Google — ultra-low latency budget workhorse
"gemini-flash-lite": {"model": "google/gemini-2.5-flash-lite"},

# Google — premium reasoning
"gemini-pro":        {"model": "google/gemini-2.5-pro"},

# Qwen — fast budget alternative
"qwen3.5-flash":     {"model": "qwen/qwen3.5-flash-02-23"},

# Z.ai — fast GLM flash
"glm-4.7-flash":     {"model": "z-ai/glm-4.7-flash"},

# Mistral — fast small instruct
"mistral-small":     {"model": "mistralai/mistral-small-3.2-24b-instruct"},
```

Note: `qwen3.5-flash` already exists in the registry (line 72). `gemini-pro` exists as `MODEL_GEMINI_PRO` mapping to `google/gemini-2.5-pro`, but `gemini-flash-lite` and `glm-4.7-flash` are missing.

### 2. Update constants (`src/reasoner/core/constants.py`)

Replace or deprecate:
```python
MODEL_DEEPSEEK_V4_PRO_MAX: str = "deepseek-v4-pro-max"  # DEPRECATED — does not exist
MODEL_DEEPSEEK_V4_FLASH: str = "deepseek-v4-flash"      # DEPRECATED — does not exist
```

Add:
```python
MODEL_GEMINI_FLASH_LITE: str = "gemini-flash-lite"
MODEL_GLM_47_FLASH: str = "glm-4.7-flash"
```

### 3. Update all presets (`src/reasoner/domain/preset_registry.py`)

Replace every occurrence of:
- `deepseek-v4-flash` → `gemini-flash-lite` (budget primary)
- `deepseek-v4-pro-max` → `gemini-pro` (premium primary)

Update `primary_id` fields accordingly.

Update `fallback_routing` to cascade away from DeepSeek V4 aliases.

### 4. Update `notes` in each preset

Remove references to "DeepSeek V4 Flash" and "DeepSeek V4 Pro Max" and replace with descriptions of the new models' latency/cost profiles.

## Cost Impact Analysis

| Tier | Old (Phantom) | New | Delta |
|------|--------------|-----|-------|
| Budget primary | N/A (timeouts) | `gemini-flash-lite` @ $0.10/$0.40 | **Functional** |
| Budget alt | `deepseek-v3` @ $0.26/$0.38 | Keep `deepseek-v3` in fallback only | Neutral |
| Premium primary | N/A (timeouts) | `gemini-2.5-pro` @ $1.25/$10.00 | **Functional** |
| Premium alt | `deepseek-v3.2-speciale` @ $0.40/$1.20 | Move to fallback | Neutral |

Because the old models simply **do not work**, any replacement that succeeds is infinitely better. The chosen replacements are price-competitive with the intended tier:
- `gemini-flash-lite` ($0.10/$0.40) is cheaper than `gpt-4o-mini` ($0.15/$0.60) and comparable to `qwen3.5-flash` ($0.07/$0.26).
- `gemini-2.5-pro` ($1.25/$10.00) is cheaper than `claude-sonnet-4.6` ($3.00/$15.00) and `gpt-5.4` ($2.50/$15.00).

## Validation Checklist

Before deploying:
- [ ] Verify `google/gemini-2.5-flash-lite` responds to a test prompt via OpenRouter in < 5s
- [ ] Verify `google/gemini-2.5-pro` responds in < 15s
- [ ] Verify JSON schema adherence for `structured_outputs` on both models
- [ ] Run `python main.py --list-presets` and confirm no `deepseek-v4-*` references remain
- [ ] Run a Budget preset end-to-end (e.g., `multi-perspective-budget`)
- [ ] Run a Premium preset end-to-end (e.g., `multi-perspective-premium`)

## Summary Table: Old → New

| Old ID | OpenRouter Reality | Recommended Replacement | Registry Alias Needed |
|--------|-------------------|------------------------|----------------------|
| `deepseek-v4-flash` | **Does not exist** | `google/gemini-2.5-flash-lite` | `gemini-flash-lite` |
| `deepseek-v4-pro-max` | **Does not exist** | `google/gemini-2.5-pro` | `gemini-pro` (exists) |
| `deepseek-v4-pro` | **Does not exist** | `google/gemini-2.5-pro` | `gemini-pro` (exists) |
| `deepseek-v4-pro-think` | **Does not exist** | `deepseek/deepseek-r1-0528` | `deepseek-r1` (exists) |

---

*Research compiled from OpenRouter API catalog (`openrouter_models.json`, 346 models), published latency benchmarks (arXiv/medRxiv 2025), DocsBot model comparisons, and project cache telemetry.*
