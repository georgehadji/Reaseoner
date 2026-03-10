---
name: ara-add-perspective
description: Use when adding a new Phase 2 perspective type (e.g., empirical, financial, environmental). Requires changes to 4 files in strict order to avoid silent failures.
version: 1.0.0
tools: Read, Edit, Bash
---

## Overview

Adds a new perspective type to Phase 2 (parallel perspective generation). Requires coordinated changes across 4 critical files. Missing any file causes silent failure or ValueError at import time. **MUST follow exact file order.**

## When to Use

- Adding a new analysis angle (e.g., "empirical", "financial", "environmental", "legal")
- Extending Phase 2 beyond default 4 perspectives (constructive/destructive/systemic/minimalist)
- Creating domain-specific perspectives for specialized reasoning

## When NOT to Use

- Modifying existing perspectives (just edit the system prompt in `core/perspectives.py`)
- Changing perspective labels/names (affects ALL files, not recommended)
- Adding presets (use ara-add-preset instead)
- Adding providers (use ara-add-provider instead)

## Critical: File Order & Interdependencies

**You MUST edit files in this exact order. Doing them out of order causes imports to fail or silent runtime errors:**

1. **`core/perspectives.py`** — Define the perspective (system_prompt, name, label)
2. **`presets.py`** — Add routing key to `_KNOWN_ROUTING_ROLES` frozenset
3. **`models.py`** — Add enum value to `PerspectiveType`
4. **Any target preset's routing dict** — Add routing key → model mapping

Failure to follow order → `ValueError` at import time or silent phase failures.

## Step-by-Step Procedure

### Step 1: Edit `core/perspectives.py`

Open `E:\Documents\Vibe-Coding\Reasoner\core\perspectives.py`

Find `DEFAULT_PERSPECTIVES` list (around line 30-80):

```python
DEFAULT_PERSPECTIVES = [
    PerspectiveDefinition(
        name="constructive",
        label="Constructive Analysis",
        system_prompt="...",
        routing_key="constructive"
    ),
    PerspectiveDefinition(
        name="destructive",
        label="Destructive Analysis",
        system_prompt="...",
        routing_key="destructive"
    ),
    # ... others
]
```

**Add your perspective at the end of the list:**

```python
    PerspectiveDefinition(
        name="empirical",  # Internal identifier (lowercase, no spaces)
        label="Empirical Analysis",  # Display name
        system_prompt="You are an empirical analyst. Focus on data-driven evidence, statistical rigor, measurable outcomes, and observable facts. Critically evaluate claims against empirical evidence. Identify what can be measured and what requires further data.",
        routing_key="empirical"  # Must match enum value in models.py step
    ),
```

**Fields:**
- `name`: Internal identifier (lowercase, hyphen-separated, no spaces)
- `label`: Display name in terminal output
- `system_prompt`: The LLM system message for this perspective (150-300 words typical)
- `routing_key`: MUST match the enum value you'll add to models.py (exact case-sensitive match)

Save the file.

### Step 2: Edit `presets.py` — Add to `_KNOWN_ROUTING_ROLES`

Open `E:\Documents\Vibe-Coding\Reasoner\presets.py`

Find `_KNOWN_ROUTING_ROLES` frozenset (around line 35-45):

```python
_KNOWN_ROUTING_ROLES = frozenset({
    "constructive",
    "destructive",
    "systemic",
    "minimalist",
    # ADD NEW KEY HERE
})
```

**Add your routing key:**

```python
_KNOWN_ROUTING_ROLES = frozenset({
    "constructive",
    "destructive",
    "systemic",
    "minimalist",
    "empirical",  # NEW
})
```

**CRITICAL:** This must exactly match the `routing_key` value from step 1.

Save the file. Do NOT yet test — `models.py` enum is still missing.

### Step 3: Edit `models.py` — Add to `PerspectiveType` Enum

Open `E:\Documents\Vibe-Coding\Reasoner\models.py`

Find `PerspectiveType` enum (around line 75-85):

```python
class PerspectiveType(str, Enum):
    CONSTRUCTIVE = "constructive"
    DESTRUCTIVE = "destructive"
    SYSTEMIC = "systemic"
    MINIMALIST = "minimalist"
    # ADD NEW ENUM VALUE HERE
```

**Add your enum value:**

```python
class PerspectiveType(str, Enum):
    CONSTRUCTIVE = "constructive"
    DESTRUCTIVE = "destructive"
    SYSTEMIC = "systemic"
    MINIMALIST = "minimalist"
    EMPIRICAL = "empirical"  # NEW (enum name UPPERCASE, value lowercase)
```

**Rules:**
- Enum name: UPPERCASE (e.g., `EMPIRICAL`)
- Enum value: lowercase string, matches routing_key from step 1 (e.g., `"empirical"`)

Save the file.

### Step 4: Update Preset Routing Dicts

Open `presets.py` again and find each preset's `routing` dict.

Example (from `claude-only` preset, around line 120):

```python
"claude-only": PipelinePreset(
    # ... other fields ...
    routing={
        "constructive": "claude-3-5-sonnet",
        "destructive": "claude-3-5-sonnet",
        "systemic": "claude-3-5-sonnet",
        "minimalist": "claude-3-5-sonnet",
        # ADD NEW ROUTING HERE
    },
    # ...
),
```

**For each preset that should use the new perspective, add:**

```python
routing={
    "constructive": "claude-3-5-sonnet",
    "destructive": "claude-3-5-sonnet",
    "systemic": "claude-3-5-sonnet",
    "minimalist": "claude-3-5-sonnet",
    "empirical": "claude-3-5-sonnet",  # NEW (same model as others, or different)
},
```

**You do NOT need to update all presets.** Only update presets that should have this perspective. For example:
- `claude-only` should have it (general purpose)
- `budget-conscious` might skip it (save tokens)
- `research` should have it (empirical is valuable for research)

**Which presets to update (conservative approach):**
- `claude-only` ✓ (always add)
- `max-quality` ✓ (always add)
- `epistemic-diversity` ✓ (add to increase diversity)
- `debate` ✗ (debate needs exactly 2 sides; skip unless you rebuild debate logic)
- `evolutionary` ✗ (evolutionary uses fitness; skip unless fitness function updated)
- Any `*-budget` presets ✗ (skip to save tokens)

Save the file.

## Verification

### Test 1: Import Validation

Run to check for ValueError:
```bash
python main.py --list-presets
```

Expected: No error, all presets listed (including your updated ones).

If ERROR: `ValueError: Unknown routing key 'empirical'`
→ Mismatch between `routing_key` in step 1, `_KNOWN_ROUTING_ROLES` in step 2, or enum value in step 3
→ Check exact spelling (case-sensitive)

### Test 2: Perspective Discovery

Verify the perspective loads:
```bash
python -c "from core.perspectives import DEFAULT_PERSPECTIVES; print([p.name for p in DEFAULT_PERSPECTIVES])"
```

Expected output includes your perspective:
```
['constructive', 'destructive', 'systemic', 'minimalist', 'empirical']
```

### Test 3: Full Pipeline Run

Test with a preset you updated:
```bash
python main.py --problem "What are the empirical foundations of this theory?" --preset claude-only --sequential
```

Expected:
- All 6 phases complete
- Phase 2 output includes 5 perspectives (4 original + 1 new)
- No routing errors
- Synthesis appears without errors

### Test 4: Routing Verification

Inspect how the perspective routes to models:
```python
python -c "from presets import PRESETS; print(PRESETS['claude-only'].routing)"
```

Expected output:
```
{'constructive': 'claude-3-5-sonnet', 'destructive': 'claude-3-5-sonnet', 'systemic': 'claude-3-5-sonnet', 'minimalist': 'claude-3-5-sonnet', 'empirical': 'claude-3-5-sonnet'}
```

## Critical Files

| File | Line Range | What to Edit |
|------|-----------|--------------|
| `core/perspectives.py` | ~30-80 | Add `PerspectiveDefinition` to `DEFAULT_PERSPECTIVES` list |
| `presets.py` | ~35-45 | Add routing key to `_KNOWN_ROUTING_ROLES` frozenset |
| `models.py` | ~75-85 | Add enum value to `PerspectiveType` class |
| `presets.py` | ~100-400 | Update routing dicts in PRESETS (one per preset) |

## Common Mistakes

1. **Out-of-order edits** → TypeError or ValueError at import time. MUST follow: 1) perspectives.py → 2) presets.py (_KNOWN) → 3) models.py → 4) presets.py (routing)

2. **Routing key case mismatch** → `routing_key="Empirical"` in perspectives.py but `"empirical"` in models.py enum → ValueError: Unknown routing key

3. **Enum name/value confusion** → Enum name UPPERCASE (`EMPIRICAL`), enum value lowercase string (`"empirical"`) — get this backwards and routing fails

4. **Forgetting to update preset routing dicts** → Perspective defined but not in preset's routing → phase 2 fails silently (no error, just doesn't call the model)

5. **Updating presets that shouldn't have it** → Added empirical to `debate` preset but debate logic still assumes exactly 2 perspectives → synthesis breaks

6. **Weak system prompt** → Perspective generates low-quality analysis → phase 2 output poor. Invest time in prompt engineering (150-300 words, clear directives, example outputs).

7. **Generic system prompt** → All perspectives sound identical → diversification fails. Make each perspective voice distinct and opinionated.

## Example: Adding "Financial" Perspective

**Step 1: core/perspectives.py**
```python
PerspectiveDefinition(
    name="financial",
    label="Financial Analysis",
    system_prompt="You are a financial analyst. Evaluate decisions through the lens of financial impact: costs, revenues, ROI, cash flow, risk-adjusted returns, and long-term financial sustainability. Consider hidden costs and second-order financial effects. Highlight financial trade-offs and quantify where possible.",
    routing_key="financial"
),
```

**Step 2: presets.py (_KNOWN_ROUTING_ROLES)**
```python
_KNOWN_ROUTING_ROLES = frozenset({
    "constructive",
    "destructive",
    "systemic",
    "minimalist",
    "financial",
})
```

**Step 3: models.py (PerspectiveType)**
```python
class PerspectiveType(str, Enum):
    CONSTRUCTIVE = "constructive"
    DESTRUCTIVE = "destructive"
    SYSTEMIC = "systemic"
    MINIMALIST = "minimalist"
    FINANCIAL = "financial"
```

**Step 4: presets.py (routing dicts)**
```python
"claude-only": PipelinePreset(
    # ...
    routing={
        "constructive": "claude-3-5-sonnet",
        "destructive": "claude-3-5-sonnet",
        "systemic": "claude-3-5-sonnet",
        "minimalist": "claude-3-5-sonnet",
        "financial": "claude-3-5-sonnet",
    },
    # ...
),
```

**Verify:**
```bash
python main.py --list-presets
python main.py --problem "Should we invest in this acquisition?" --preset claude-only --sequential
```
