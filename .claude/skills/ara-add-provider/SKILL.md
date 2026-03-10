---
name: ara-add-provider
description: Use when adding a new LLM provider (API integration) into llm.py. Covers subclassing BaseLLMProvider, registering in _REGISTRY, handling JSON extraction, and testing with --sequential flag.
version: 1.0.0
tools: Read, Edit, Bash
---

## Overview

Integrates a new LLM provider (e.g., Cohere, Together.ai, custom endpoint) into the pipeline. Requires subclassing `BaseLLMProvider`, implementing the `complete()` method, registering in `_REGISTRY`, and extensive testing of JSON output parsing.

## When to Use

- Integrating new LLM API (OpenAI, Mistral, Google Gemini, Cohere, Together.ai, etc.)
- Adding custom OpenAI-compatible endpoint (local LLM server, etc.)
- Adding Chinese provider endpoints (Kimi, GLM, Qwen, MiniMax)
- Extending model diversity beyond current providers

## When NOT to Use

- Modifying existing provider (just edit the provider class)
- Adding presets (use ara-add-preset instead)
- Adding perspectives (use ara-add-perspective instead)
- Testing performance optimization (different skill needed)

## Critical Warning: JSON Extraction Will Break First

**Expected behavior:** When adding a new provider, JSON extraction will likely fail on first run. This is normal and expected. Different providers wrap JSON differently:
- Some use markdown fences: ```json { } ```
- Some prepend reasoning text before JSON
- Some include prose preamble or citations after JSON
- Chinese providers use non-standard formatting

Use `--sequential` flag and `DEBUG=1` to see raw output, then adjust `parsing.py:extract_json()` if needed.

## Step-by-Step Procedure

### Step 1: Create Provider Subclass

Open `E:\Documents\Vibe-Coding\Reasoner\llm.py`

Find the provider class hierarchy (around line 100-200). Example:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str, temperature: float, max_tokens: int) -> tuple[str, dict]:
        """
        Returns: (response_text: str, tokens: dict)
        tokens dict must have 'input' and 'output' keys
        """
        pass

class AnthropicProvider(BaseLLMProvider):
    # ... implementation
```

**Add your provider subclass:**

```python
class MyNewProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key or ""
        self.base_url = "https://api.mynewprovider.com"
    
    async def complete(self, prompt: str, system: str, temperature: float, max_tokens: int) -> tuple[str, dict]:
        """
        Calls MyNewProvider API and returns (response_text, tokens)
        """
        import httpx
        
        # Fail-fast if no API key
        if not self.api_key:
            raise AuthenticationError("API_KEY_ENV_VAR not set")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,  # Set in __init__ or from registry
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
        
        # Extract response text (provider-specific)
        response_text = data["choices"][0]["message"]["content"]
        
        # Extract token usage (provider-specific, must have 'input' and 'output' keys)
        tokens = {
            "input": data.get("usage", {}).get("prompt_tokens", 0),
            "output": data.get("usage", {}).get("completion_tokens", 0),
        }
        
        return response_text, tokens
```

**Critical requirements for `complete()` method:**
1. **Must be async** (async def)
2. **Signature:** `async def complete(self, prompt: str, system: str, temperature: float, max_tokens: int) -> tuple[str, dict]:`
3. **Return type:** tuple of (response_text: str, tokens: dict)
4. **Tokens dict MUST have keys: `"input"` and `"output"`** (token counts)
5. **Raise `AuthenticationError` if API key missing** (fail-fast, not silent)
6. **Handle timeouts** (set reasonable timeout, e.g., 60 seconds)

### Step 2: Register in `_REGISTRY`

Find `_REGISTRY` dict (around line 250-350 in `llm.py`):

```python
_REGISTRY = {
    "claude-3-5-sonnet": {
        "cls": AnthropicProvider,
        "model": "claude-3-5-sonnet-20241022",
        "env": "ANTHROPIC_API_KEY",
    },
    "gpt-4": {
        "cls": OpenAICompatibleProvider,
        "model": "gpt-4",
        "env": "OPENAI_API_KEY",
        "base": "https://api.openai.com/v1",
    },
    # ... other models
}
```

**Add your provider's models:**

```python
_REGISTRY = {
    # ... existing entries ...
    
    "mynewprovider-model-1": {
        "cls": MyNewProvider,
        "model": "mynewprovider-model-1",
        "env": "MYNEWPROVIDER_API_KEY",
    },
    "mynewprovider-model-2": {
        "cls": MyNewProvider,
        "model": "mynewprovider-model-2",
        "env": "MYNEWPROVIDER_API_KEY",
    },
}
```

**Required fields:**
- `"cls"`: Your provider class (e.g., `MyNewProvider`)
- `"model"`: Model ID string (used by provider, e.g., "gpt-4", "claude-3.5-sonnet")
- `"env"`: Environment variable name for API key (e.g., `"OPENAI_API_KEY"`)
- `"base"` (optional): Base URL if OpenAI-compatible provider

**Naming convention:**
- Key: lowercase, hyphenated, descriptive (e.g., `"cohere-command-r"`, `"together-llama-70b"`)
- Model: exact string from provider's API docs (e.g., `"command-r"`, `"meta-llama/Llama-2-70b"`)

### Step 3: Add Provider Builder

Find `build_provider()` function (around line 400-500 in `llm.py`):

```python
def build_provider(provider_cls: str, model_id: str) -> BaseLLMProvider:
    """Factory function to instantiate providers"""
    config = _REGISTRY.get(model_id)
    if not config:
        raise ValueError(f"Model {model_id} not in registry")
    
    api_key = os.environ.get(config["env"], "")
    
    if config["cls"] == AnthropicProvider:
        return AnthropicProvider(api_key=api_key)
    elif config["cls"] == OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=config["model"],
            base_url=config.get("base", "https://api.openai.com/v1")
        )
    # ... other providers
```

**Add your provider case:**

```python
    elif config["cls"] == MyNewProvider:
        return MyNewProvider(api_key=api_key)
```

Or, if your provider is OpenAI-compatible (recommended), extend `OpenAICompatibleProvider` instead of creating a new class:

```python
# In _REGISTRY:
"mynewprovider-model": {
    "cls": OpenAICompatibleProvider,
    "model": "mynewprovider-model",
    "env": "MYNEWPROVIDER_API_KEY",
    "base": "https://api.mynewprovider.com/v1",
},
```

### Step 4: Add Environment Variable to Presets

Open `presets.py` and update any preset that uses your new provider:

```python
"your-preset": PipelinePreset(
    # ... other fields ...
    required_env_vars=["ANTHROPIC_API_KEY", "MYNEWPROVIDER_API_KEY"],  # ADD
),
```

This ensures users know which env vars must be set.

### Step 5: Test Discovery

Verify the provider is registered:

```bash
python main.py --list-models
```

Expected: Your model IDs appear in output.

If ERROR: `ValueError: Model ... not in registry`
→ Check spelling in `_REGISTRY`, verify key matches model_id used

### Step 6: Test with --sequential

Create a simple test preset or use existing one, then test:

```bash
# Set API key
export MYNEWPROVIDER_API_KEY="your-api-key"

# Run with --sequential to isolate phase failures
python main.py --problem "2+2=?" --preset claude-only --sequential
```

**Expected behavior:**
- Phase 0 (classification) completes or fails with clear error
- If JSON parsing error: see raw output with `DEBUG=1`
- If auth error: check API key
- If timeout: provider is very slow (increase timeout in provider class)

### Step 7: Debug JSON Extraction (Expected to Fail First Time)

Run with debug to see raw LLM output:

```bash
DEBUG=1 python main.py --problem "test" --preset your-preset --sequential
```

If JSON parsing fails:
1. Copy raw output from debug log
2. Examine how provider wraps JSON:
   - Markdown fences: ```json { } ```
   - Prose preamble before JSON
   - Citations after JSON
   - Non-standard indentation

3. Update `parsing.py:extract_json()` to handle provider's format:

```python
def extract_json(text: str) -> dict:
    # Existing fallbacks...
    
    # ADD PROVIDER-SPECIFIC HANDLING
    if "```mynewprovider" in text:  # Example
        # Extract content between ```mynewprovider ... ```
        pattern = r"```mynewprovider\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    
    # Fall back to existing logic
    ...
```

## Critical Files

| File | Line Range | Purpose |
|------|-----------|---------|
| `llm.py` | ~100-200 | Provider class definitions; add subclass here |
| `llm.py` | ~250-350 | `_REGISTRY` dict; register models here |
| `llm.py` | ~400-500 | `build_provider()` factory; add provider case here |
| `parsing.py` | ~50-120 | `extract_json()` function; adjust for provider wrapping |
| `presets.py` | ~100-400 | Update `required_env_vars` in presets |

## Verification Checklist

- [ ] Provider class defined with `async complete()` method
- [ ] `complete()` returns `(str, dict)` with tokens dict having 'input' and 'output' keys
- [ ] Provider registered in `_REGISTRY` with all required fields (cls, model, env)
- [ ] `build_provider()` has case for new provider class
- [ ] `python main.py --list-models` shows your models
- [ ] `python main.py --list-presets` validates without error
- [ ] ENV var set: `export YOUR_API_KEY="..."`
- [ ] `python main.py --problem "test" --preset some-preset --sequential` runs Phase 0
- [ ] If JSON parsing fails, `DEBUG=1` shows raw output
- [ ] `parsing.py:extract_json()` updated to handle provider's format (if needed)
- [ ] All 6 phases complete without error
- [ ] Output appears in terminal

## Common Mistakes & Gotchas

1. **`complete()` not async** → `TypeError: object is not awaitable`
   Fix: Use `async def`, not `def`

2. **Tokens dict missing keys** → Phase 2 fails silently when trying to access `tokens["input"]`
   Fix: Ensure tokens dict has `"input"` and `"output"` keys (exact names)

3. **Forgetting `AuthenticationError` on missing API key** → Silent failure, confusing error later
   Fix: `if not api_key: raise AuthenticationError("API_KEY not set")`

4. **Wrong environment variable name** → API key not found at runtime
   Fix: Check `_REGISTRY` env field matches actual env var name user sets

5. **Not handling response format** → JSON extraction fails
   Example: Provider returns `{"result": { "choices": [...] }}` instead of `{"choices": [...]}`
   Fix: Adjust `complete()` method to extract correct path before returning

6. **JSON wrapped in markdown fences** → `extract_json()` fails
   Example: Provider returns ```json { "choices": ... } ```
   Fix: Add case to `extract_json()` to strip markdown fences

7. **Timeout too short** → Timeouts on slow providers
   Fix: Increase timeout in provider class (e.g., `timeout=120.0`)

8. **Chinese providers with unverified endpoints** → Connection refused or wrong format
   Current status: Kimi, GLM, MiniMax, Qwen registered but never live-tested
   Endpoint paths and auth headers change frequently
   Fix: Test with provider docs open, update frequently

9. **OpenAI-compatible provider with wrong base URL** → 404 Not Found
   Fix: Verify `base_url` matches provider's actual endpoint (e.g., `https://api.mynewprovider.com/v1`, NOT `https://api.mynewprovider.com`)

10. **Forgetting to add to required_env_vars** → User runs preset, auth fails with confusing error
    Fix: Add env var to `required_env_vars` list in any preset using the provider

## Example: Adding Cohere Provider

```python
# In llm.py (around line 150)
class CohereProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key or ""
        self.base_url = "https://api.cohere.com"
    
    async def complete(self, prompt: str, system: str, temperature: float, max_tokens: int) -> tuple[str, dict]:
        import httpx
        
        if not self.api_key:
            raise AuthenticationError("COHERE_API_KEY not set")
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "command-r-plus",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
        
        response_text = data["choices"][0]["message"]["content"]
        tokens = {
            "input": data.get("usage", {}).get("prompt_tokens", 0),
            "output": data.get("usage", {}).get("completion_tokens", 0),
        }
        
        return response_text, tokens

# In _REGISTRY (around line 300)
"cohere-command-r": {
    "cls": CohereProvider,
    "model": "command-r-plus",
    "env": "COHERE_API_KEY",
},

# In build_provider() (around line 450)
elif config["cls"] == CohereProvider:
    return CohereProvider(api_key=api_key)

# In presets.py
"cohere-only": PipelinePreset(
    name="cohere-only",
    description="Uses Cohere for all phases",
    # ... other fields ...
    required_env_vars=["COHERE_API_KEY"],
),
```

**Test:**
```bash
export COHERE_API_KEY="your-key"
python main.py --list-models  # Should show cohere-command-r
python main.py --problem "test" --preset claude-only --sequential  # Test phase 0
```
