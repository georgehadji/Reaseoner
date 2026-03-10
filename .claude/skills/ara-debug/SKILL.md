---
name: ara-debug
description: Use when a pipeline phase fails, produces no output, JSON parsing error, rate limit hit, model not found error, or pipeline hangs. Diagnoses and resolves failures systematically.
version: 1.0.0
tools: Read, Grep, Bash, Edit
---

## Overview

Systematic diagnosis of ARA pipeline failures. Identifies failure class (JSON parsing, rate limit, auth, model mismatch, PerspectiveType routing, hung process), provides targeted fixes, and verifies resolution.

## When to Use

- Phase produces no output
- JSON parsing error during phase execution
- "Model not found" or "API key invalid" error
- Rate limit hit (429, 503 responses)
- Pipeline appears hung (no progress for >30 seconds)
- PerspectiveType mismatch (silent phase failure)
- Unexpected error in phase output

## When NOT to Use

- General code questions unrelated to pipeline execution
- Adding features (use ara-add-preset, ara-add-perspective, ara-add-provider instead)
- Optimizing performance (different skill needed)

## Step-by-Step Procedure

### 1. Confirm Failure & Capture Context

Run the failing command with `--sequential` flag to isolate which phase fails:
```bash
python main.py --problem "Your problem" --preset claude-only --sequential
```

This runs phases 1-6 sequentially instead of parallel, making failure clearer.

**Capture:**
- Exact error message
- Which phase number failed (0=classification, 1=decomposition, 2=perspectives, 3=scoring, 4=stress-test, 5=synthesis)
- Raw output if visible

### 2. Diagnose Failure Class

Use this decision tree:

#### JSON Parsing Error
**Symptoms:** `JSONDecodeError`, `ValueError: No JSON found`, parsing fails after LLM response

**Fix:**
- Check `parsing.py:extract_json()` — verify markdown fence handling
- If using non-Claude provider: provider wraps output differently (expected)
- Inspect raw phase output with `DEBUG=1` env var
- Provider-specific JSON wrappers:
  - Mistral: wraps in ```json ... ```
  - Google Gemini: may include reasoning text before JSON
  - OpenAI: usually clean JSON
  - Chinese providers: often add markdown + citations

**Action:** Use `--sequential` to see raw LLM output, then adjust `parsing.py` to handle provider's format

#### Rate Limit Hit
**Symptoms:** 429 status code, "rate_limit_exceeded", "quota exceeded", 503 Service Unavailable

**Fix:**
- Add `--sequential` flag to space out API calls
- Wait 30-60 seconds before retry (exponential backoff)
- Phase 2 makes 4 parallel calls — most rate limit culprit
- Reduce `max_tokens` in preset to use fewer tokens
- Consider switching to higher-tier API key or different provider

**Action:** Retry with `--sequential`, add delays if needed

#### Authentication Error
**Symptoms:** 401 Unauthorized, "invalid_api_key", "authentication failed", "API key not found"

**Fix:**
1. Verify API key environment variable is set:
   ```bash
   echo $ANTHROPIC_API_KEY  # Should print key, not empty
   ```
2. Check key is valid for the provider:
   ```bash
   python main.py --list-presets  # Will fail at import if key missing
   ```
3. If key is wrong, rotate it in provider dashboard
4. Verify env var name matches provider expectation in `llm.py:_REGISTRY`

**Critical files:**
- `llm.py:_REGISTRY` (line ~250) — env var names per provider
- `llm.py:AnthropicProvider.complete()` (line ~150) — key reading
- `presets.py:PRESETS` — which providers each preset uses

**Action:** Set correct env var, verify with `--list-presets`, retry

#### Model Not Found
**Symptoms:** "Model [name] not available", "Unknown model", provider doesn't recognize model ID

**Fix:**
1. List available models:
   ```bash
   python main.py --list-models
   ```
2. Verify model ID in preset matches registry:
   ```bash
   grep -n "model.*=.*\"gpt-4\"" presets.py  # Example
   ```
3. Check `llm.py:_REGISTRY` (line ~250-350) for exact model string
4. Update preset if model ID is outdated

**Critical files:**
- `llm.py:_REGISTRY` — dict of all {model_id: config}
- `presets.py:PRESETS` — which models each preset assigns to each phase

**Action:** Verify model ID with `--list-models`, update preset, retry

#### PerspectiveType Mismatch (Silent Failure)
**Symptoms:** Phase 2 completes but perspectives don't appear in output, synthesis uses wrong model, phase output is incomplete

**Fix:**
1. Check routing key matches `PerspectiveType` enum:
   ```bash
   grep -A 20 "class PerspectiveType" models.py
   grep -B 5 -A 5 "_KNOWN_ROUTING_ROLES" presets.py
   ```
2. Verify preset's `routing` dict keys match enum values exactly (case-sensitive):
   - `constructive`, `destructive`, `systemic`, `minimalist` are standard
   - Check if custom perspectives added

3. Verify models exist for all routing keys:
   ```bash
   python -c "from presets import PRESETS; p = PRESETS['your-preset']; print(p.routing)"
   ```

**Critical files:**
- `models.py` (line ~80) — `PerspectiveType` enum values
- `presets.py` (line ~40) — `_KNOWN_ROUTING_ROLES` frozenset
- `presets.py:PRESETS` — routing dicts per preset

**Action:** Verify routing keys match enum, add missing keys, retry

#### Hung Pipeline
**Symptoms:** Command runs but produces no output for >30 seconds, CPU idle, no network activity

**Fix:**
- **No timeout mechanism exists** — pipeline has no per-phase timeout
- Kill the process: `Ctrl+C` or in another terminal:
  ```bash
  ps aux | grep "python main.py"
  kill -9 <pid>
  ```
- Likely causes:
  - Provider is very slow or down
  - Network connection broken
  - Large problem statement causing long processing
  
**Action:** Kill and retry, possibly with different provider or smaller problem

### 3. Verify Expected Output Schemas

Each phase should output JSON matching these schemas:

**Phase 0 (Classification):**
```json
{
  "task_type": "strategic|tactical|creative|analytical",
  "reasoning": "..."
}
```

**Phase 1 (Decomposition):**
```json
{
  "sub_problems": ["problem 1", "problem 2", ...],
  "reasoning": "..."
}
```

**Phase 2 (Perspectives):**
```json
{
  "perspectives": [
    {"type": "constructive", "content": "..."},
    {"type": "destructive", "content": "..."},
    {"type": "systemic", "content": "..."},
    {"type": "minimalist", "content": "..."}
  ]
}
```

**Phase 3 (Scoring):**
```json
{
  "scores": [
    {"perspective": "constructive", "score": 8.5, "reasoning": "..."},
    ...
  ],
  "top_k": 2
}
```

**Phase 4 (Stress Test):**
```json
{
  "stress_tests": [
    {"scenario": "...", "perspective": "constructive", "result": "..."},
    ...
  ]
}
```

**Phase 5 (Synthesis):**
```json
{
  "solution": "...",
  "confidence": 0.85,
  "caveats": ["..."]
}
```

If phase output doesn't match schema, error likely happened in LLM or parser.

### 4. Check Common Provider Issues

**Mistral:**
- Wraps JSON in markdown: ```json { } ```
- `extract_json()` handles this — usually works

**Google Gemini:**
- Adds reasoning preamble before JSON
- May not be deterministic (same problem gives different output)
- Set `temperature=0` for consistency

**OpenAI (untested):**
- Should return clean JSON like Claude
- Check if model ID is valid (gpt-4, gpt-3.5-turbo, etc.)

**Chinese providers (unverified):**
- Kimi (moonshot.cn): endpoint may have changed
- GLM (bigmodel.cn): auth headers different
- Qwen (aliyuncs.com): model list frequently updated
- MiniMax (minimax.chat): requires specific formatting

**Action:** If non-Claude provider fails, switch to `--preset claude-only` to confirm pipeline logic is sound

### 5. Verify Fix

After applying fix, re-run with `--sequential`:
```bash
python main.py --problem "Your problem" --preset claude-only --sequential
```

Confirm:
- All 6 phases complete (0-5)
- Each phase outputs valid JSON
- Final synthesis appears in terminal
- No error messages

## Critical Files

| File | Key Lines | Purpose |
|------|-----------|---------|
| `parsing.py` | ~50-120 | `extract_json()` — handles markdown fences, whitespace, provider variations |
| `exceptions.py` | all | Exception hierarchy with `retryable` flag |
| `pipeline.py` | ~80-200 | `ARAPipeline` class, phase execution sequencing |
| `llm.py` | ~250-350 | `_REGISTRY` dict, provider registration |
| `models.py` | ~80 | `PerspectiveType` enum values |
| `presets.py` | ~40, ~100-300 | `_KNOWN_ROUTING_ROLES`, `PRESETS` dict |
| `phases.py` | all | 6 phase prompt functions |
| `main.py` | ~50-150 | Entry point, CLI arg parsing |

## Verification

1. **Syntax check:**
   ```bash
   python main.py --list-presets
   ```
   If imports succeed, no ValueError or syntax errors.

2. **Full pipeline run:**
   ```bash
   python main.py --problem "Simple test: Is 2+2=4?" --preset claude-only --sequential
   ```
   Should complete all 6 phases without error.

3. **Check output format:**
   - Terminal shows Rich-formatted output
   - No "ERROR" lines
   - Synthesis section appears at end

## Common Mistakes

1. **Forgetting `--sequential`** — Parallel Phase 2 makes debugging harder. Always use `--sequential` first.
2. **Wrong API key env var name** — Check `llm.py:_REGISTRY` for exact var name (ANTHROPIC_API_KEY vs OPENAI_API_KEY)
3. **Stale provider endpoints** — Chinese providers change URLs frequently. Check docs if "connection refused"
4. **Assuming provider equivalence** — Non-Claude providers have different JSON formatting, temperature behavior, response times. They are NOT drop-in replacements.
5. **Ignoring parsing errors** — If `extract_json()` fails, provider is wrapping JSON differently. Use `DEBUG=1` to see raw output.
6. **Not checking PerspectiveType enum** — Routing key typos don't error — phase silently uses fallback. Verify keys match exactly.
