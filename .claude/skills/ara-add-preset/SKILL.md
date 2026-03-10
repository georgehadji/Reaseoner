---
name: ara-add-preset
description: Use when adding a new routing preset to presets.py, creating a new provider configuration, or extending the PRESETS dictionary. Ensures all validation rules are met.
version: 1.0.0
tools: Read, Edit, Bash
---

## Overview

Adds a new `PipelinePreset` to the PRESETS dictionary. Validates all required fields and enforces constraints at import time. Optional: registers new METHOD (debate/evolutionary/research) with custom synthesis hints.

## When to Use

- Adding a preset (e.g., `--preset my-new-preset`)
- Creating new provider routing configuration
- Defining new LLM model combinations for specific phases
- Extending PRESETS dict with budget, quality, or provider-specific variants

## When NOT to Use

- Modifying an existing preset (just edit the dict entry, no validation changes)
- Adding a new perspective type (use ara-add-perspective instead)
- Adding a new provider (use ara-add-provider instead)
- General code changes unrelated to presets

## Step-by-Step Procedure

### 1. Understand PipelinePreset Structure

Each preset is a `PipelinePreset` dataclass with:

```python
PipelinePreset(
    name: str,                    # Unique identifier (used with --preset)
    description: str,             # Human-readable summary
    method: MethodType,          # STANDARD|DEBATE|EVOLUTIONARY|RESEARCH
    phases: dict[int, str],      # {0: "model-id", 1: "model-id", ...}
    routing: dict[str, str],     # {"perspective-key": "model-id", ...}
    temperature: float,          # 0.0-1.0 (higher = more creative)
    max_tokens: int,             # Per-phase token limit
    fallback_routing: dict[str, str] | None,  # Optional fallback models
    required_env_vars: list[str]  # ["ANTHROPIC_API_KEY", ...]
)
```

### 2. Check Validation Rules

These are enforced by `PipelinePreset.__post_init__()`:

1. **All routing keys MUST exist in `_KNOWN_ROUTING_ROLES`:**
   ```python
   # In presets.py, line ~40
   _KNOWN_ROUTING_ROLES = frozenset({
       "constructive", "destructive", "systemic", "minimalist",
       # ... add custom roles here if creating new perspectives
   })
   ```
   Mismatch → `ValueError` at import time

2. **All model IDs MUST exist in `llm.py:_REGISTRY`:**
   ```bash
   python main.py --list-models  # Shows all valid model IDs
   ```
   Invalid ID → `ValueError` at import time

3. **`required_env_vars` MUST list all env vars for referenced models:**
   ```python
   # If preset uses "claude-3-5-sonnet" (needs ANTHROPIC_API_KEY)
   # and "gpt-4" (needs OPENAI_API_KEY), include both
   required_env_vars: ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
   ```

4. **`phases` dict must have keys 0-5:**
   ```python
   phases: {
       0: "model-for-classification",
       1: "model-for-decomposition",
       2: "model-for-perspective-generation",
       3: "model-for-scoring",
       4: "model-for-stress-test",
       5: "model-for-synthesis"
   }
   ```
   Missing phase → `KeyError` during pipeline execution

5. **`method` must be MethodType enum value:**
   ```python
   from models import MethodType
   # Valid: MethodType.STANDARD, MethodType.DEBATE, etc.
   ```

### 3. Create Preset Entry

Open `presets.py` and add to PRESETS dict:

```python
PRESETS = {
    "existing-preset": PipelinePreset(...),
    
    # NEW PRESET HERE
    "my-new-preset": PipelinePreset(
        name="my-new-preset",
        description="Brief description of this preset's purpose",
        method=MethodType.STANDARD,
        phases={
            0: "claude-3-5-sonnet",  # Must exist in _REGISTRY
            1: "claude-3-5-sonnet",
            2: "claude-3-5-sonnet",
            3: "claude-3-5-sonnet",
            4: "claude-3-5-sonnet",
            5: "claude-3-5-sonnet",
        },
        routing={
            "constructive": "claude-3-5-sonnet",
            "destructive": "claude-3-5-sonnet",
            "systemic": "claude-3-5-sonnet",
            "minimalist": "claude-3-5-sonnet",
        },
        temperature=0.7,
        max_tokens=2000,
        fallback_routing=None,  # Or provide fallback models
        required_env_vars=["ANTHROPIC_API_KEY"],
    ),
    
    # ... other presets
}
```

### 4. If Adding New METHOD

If creating a preset with a new MethodType (e.g., `MethodType.CUSTOM`), register it:

#### In `renderer.py`:
Find the preset-to-rendering-function mapping and add:
```python
# Around line 50-100
_METHOD_RENDERERS = {
    MethodType.STANDARD: _render_standard,
    MethodType.DEBATE: _render_debate,
    MethodType.EVOLUTIONARY: _render_evolutionary,
    MethodType.RESEARCH: _render_research,
    MethodType.CUSTOM: _render_custom,  # NEW
}
```

#### In `phases.py`:
Add synthesis prompt hint:
```python
# Around line ~800 (synthesis_prompt function)
_METHOD_SYNTHESIS_HINTS = {
    "STANDARD": "Synthesize into a structured solution...",
    "DEBATE": "Declare a winner based on steel-manned arguments...",
    "EVOLUTIONARY": "Describe fitness selection and optimized traits...",
    "RESEARCH": "Summarize evidence quality and gaps...",
    "CUSTOM": "Your custom synthesis guidance here...",  # NEW
}
```

### 5. Validate at Import Time

Test that the preset validates:
```bash
python main.py --list-presets
```

Expected output:
- No `ValueError` or `KeyError`
- Your preset name appears in list
- All presets listed (including new one)

Example success:
```
Available presets:
  claude-only
  max-quality
  my-new-preset  ← Your new preset here
  ... (others)
```

### 6. Test Full Pipeline with New Preset

Run a simple problem:
```bash
python main.py --problem "Is 2+2 equal to 4?" --preset my-new-preset --sequential
```

Verify:
- All 6 phases complete
- No routing errors
- Synthesis appears in output
- Method-specific rendering applies (STANDARD vs DEBATE vs RESEARCH format)

## Critical Files

| File | Key Lines | Purpose |
|------|-----------|---------|
| `presets.py` | ~1-50 | `PipelinePreset` class, `_KNOWN_ROUTING_ROLES` |
| `presets.py` | ~100-400 | `PRESETS` dict with all presets |
| `models.py` | ~40 | `MethodType` enum (STANDARD, DEBATE, EVOLUTIONARY, RESEARCH) |
| `llm.py` | ~250-350 | `_REGISTRY` dict (valid model IDs) |
| `renderer.py` | ~50-150 | Method-specific renderers (if new MethodType) |
| `phases.py` | ~800 | `_METHOD_SYNTHESIS_HINTS` (if new MethodType) |
| `main.py` | ~80 | `--preset` argument parsing |

## Verification Checklist

- [ ] All model IDs in `phases` dict exist in `--list-models` output
- [ ] All routing keys in `routing` dict exist in `_KNOWN_ROUTING_ROLES`
- [ ] `required_env_vars` lists ALL env vars needed (run with missing key to test)
- [ ] `phases` dict has keys 0-5 (all phases covered)
- [ ] `method` is valid MethodType enum value
- [ ] `--list-presets` runs without error
- [ ] `python main.py --problem "test" --preset my-new-preset --sequential` completes all 6 phases
- [ ] Output format matches method (STANDARD/DEBATE/EVOLUTIONARY/RESEARCH)

## Common Mistakes

1. **Routing key typo** — `"contructive"` instead of `"constructive"` → ValueError at import time
2. **Invalid model ID** — `"gpt-5-turbo"` (doesn't exist) → ValueError at import time
3. **Missing phase** — Only keys 0,1,2 in phases dict (missing 3,4,5) → KeyError during execution
4. **Forgetting required_env_vars** — Preset uses OpenAI but `required_env_vars: ["ANTHROPIC_API_KEY"]` → Auth failure at runtime
5. **Wrong MethodType** — Using string instead of enum (e.g., `"STANDARD"` instead of `MethodType.STANDARD`) → TypeError
6. **Fallback routing not validated** — Fallback models don't exist in _REGISTRY → silent failure during phase 2
7. **New method without registering** — Creating `MethodType.CUSTOM` but not adding to `_METHOD_RENDERERS` in `renderer.py` → rendering error at end

## Example: Adding "budget-conscious" Preset

```python
# In presets.py, PRESETS dict
"budget-conscious": PipelinePreset(
    name="budget-conscious",
    description="Minimal token usage, fast execution. Uses smaller models.",
    method=MethodType.STANDARD,
    phases={
        0: "claude-3-haiku",  # Cheapest Claude model
        1: "claude-3-haiku",
        2: "claude-3-haiku",
        3: "claude-3-haiku",
        4: "claude-3-haiku",
        5: "claude-3-5-sonnet",  # Splurge on final synthesis
    },
    routing={
        "constructive": "claude-3-haiku",
        "destructive": "claude-3-haiku",
        "systemic": "claude-3-haiku",
        "minimalist": "claude-3-haiku",
    },
    temperature=0.5,
    max_tokens=1000,  # Lower token limit = cheaper
    fallback_routing=None,
    required_env_vars=["ANTHROPIC_API_KEY"],
),
```

Test:
```bash
python main.py --problem "Test" --preset budget-conscious --sequential
```
