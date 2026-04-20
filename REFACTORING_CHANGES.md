# Refactoring Changes Report

> **Generated:** 2026-04-19  
> **Scope:** Strategy A (Phases A–C) + Strategy B (Phases 0–2) + Autonomous Debugging Fixes  
> **Test Gate:** 521 passed, 303 skipped, 0 failed

---

## Executive Summary

This document records all code changes made during the two-phase refactoring initiative. The goal was to reduce cognitive load, eliminate dead code, and split monolithic modules into focused, maintainable units while preserving 100% backward compatibility and passing all 521 tests.

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| `pipeline.py` | 1,789 lines | 597 lines | **-1,192** |
| `phases.py` | 1,394 lines | 30 lines (shim) | **-1,364** |
| `presets.py` | 1,195 lines | 103 lines (shim) | **-1,092** |
| `llm.py` | 687 lines | 38 lines (shim) | **-649** |
| **Total monolith lines removed** | — | — | **~4,300** |
| **New focused modules created** | — | **39** | — |
| **Tests passing** | 521 | 521 | **0 regressions** |

---

## Strategy A — Preliminary Clean-up

### Phase A: Import Cleanup

**File:** `src/reasoner/api/__init__.py`

- Removed ~30 unused imports (leftover from earlier iterations).
- Result: **-1 line** (522 → 521).

### Phase B: Dead Code Removal

**File:** `src/reasoner/pipeline.py`

- Deleted 16 dead `_run_*_pipeline()` methods that were orphaned after the method-dispatch refactor.
- These methods had no callers and duplicated logic already present in the active pipeline.

### Phase C: SearchMixin Extraction

**New file:** `src/reasoner/application/mixins/search_mixin.py` (486 lines)

Extracted 6 search/vetting methods from `pipeline.py`:

- `_phase_context_vetting`
- `_phase_deep_read`
- `_vet_results`
- `_vet_single`
- `_enrich_query`
- `_validate_evidence_coverage`

`pipeline.py`: 2,200 → 1,789 lines

---

## Strategy B — Structural Refactoring

### Phase 0: Fix Broken Runtime

**Deleted:** `src/reasoner/infrastructure/llm/new_pipeline.py` (1,024 lines)

- Contained a broken `NewARAPipeline` class that raised `AttributeError` on `get_provider_for_role`.
- Reverted API handlers to use the legacy `ARAPipeline`.
- Removed the broken import from `api/__init__.py`.

### Phase 1a: Split `phases.py` Monolith

**Before:** `src/reasoner/phases.py` — 1,394 lines  
**After:** `src/reasoner/phases/` package — 19 modules + shim

| New Module | Lines | Responsibility |
|------------|-------|----------------|
| `_shared.py` | 93 | Language detection, user-input wrapping |
| `_universal.py` | 209 | classify, decompose, synthesis, recovery prompts |
| `multi_perspective.py` | 47 | Multi-perspective phase prompts |
| `debate.py` | 32 | Debate phase prompts |
| `jury.py` | 26 | Jury phase prompts |
| `research.py` | 10 | Research phase prompts |
| `scientific.py` | 14 | Scientific method prompts |
| `socratic.py` | 14 | Socratic method prompts |
| `pre_mortem.py` | 67 | Pre-mortem analysis prompts |
| `bayesian.py` | 71 | Bayesian reasoning prompts |
| `dialectical.py` | 72 | Dialectical reasoning prompts |
| `analogical.py` | 118 | Analogical reasoning prompts |
| `delphi.py` | 116 | Delphi method prompts |
| `cove.py` | 93 | Chain-of-Verification prompts |
| `sot.py` | 72 | Skeleton-of-Thought prompts |
| `tot.py` | 97 | Tree-of-Thought prompts |
| `pot.py` | 68 | Program-of-Thought prompts |
| `self_discover.py` | 78 | Self-Discover prompts |
| `__init__.py` | 29 | Package re-exports |

**Shim:** Original `phases.py` (30 lines) re-exports all names for backward compatibility.

### Phase 1b: Split `llm.py` Monolith

**Before:** `src/reasoner/llm.py` — 687 lines  
**After:** `src/reasoner/infrastructure/llm/` package — 6 modules + shim

| New Module | Lines | Responsibility |
|------------|-------|----------------|
| `base.py` | 64 | Old string-prompt `BaseLLMProvider`, `LLMError` |
| `providers/openai_compat.py` | 258 | `OpenAICompatibleProvider`, `OpenRouterProvider` |
| `registry.py` | 164 | `_MODEL_WHITELIST`, `_REGISTRY`, `build_provider()` |
| `router.py` | 144 | `ProviderRouter` with fallback logic |
| `utils.py` | 70 | `_patch_openai_platform_detection`, `_requests_strict_json` |
| `exceptions.py` | 66 | Exception hierarchy |
| `__init__.py` | 12 | Package re-exports (new Message-based provider from `ports.py`) |

**Shim:** Original `llm.py` (38 lines) re-exports all public names for backward compatibility.

**Test fix:** Updated patch target from `reasoner.llm.openai.AsyncOpenAI` to `reasoner.infrastructure.llm.providers.openai_compat.openai.AsyncOpenAI`.

### Phase 1c: Split `presets.py` Monolith

**Before:** `src/reasoner/presets.py` — 1,195 lines  
**After:** `src/reasoner/domain/` submodules + shim

| New Module | Lines | Responsibility |
|------------|-------|----------------|
| `preset_core.py` | 221 | `PipelinePreset` dataclass, `get_method_from_preset()`, `get_preset_tier()`, helpers |
| `preset_registry.py` | 1,276 | `_PRESET_CONFIGS` (28 presets), `PRESETS` dict |

**Dead code pruned:**
- Removed `phase_overrides` field from `PipelinePreset` (never populated).
- Removed `post_synthesis_verify` from `_KNOWN_ROUTING_ROLES` (never used).
- Fixed `get_method_from_preset()` to return `"multi_perspective"` for unknown/empty/iterative inputs.
- Fixed `get_preset_tier()` for edge cases.

**Shim:** Original `presets.py` (103 lines) re-exports + helper functions (`print_presets_summary()`, `get_preset()`, etc.).

### Phase 2: Method Mixins Extraction

**Before:** `pipeline.py` — 1,789 lines  
**After:** `pipeline.py` — 597 lines + 8 mixin modules

`ARAPipeline` now inherits from:

```python
class ARAPipeline(
    SearchMixin, PerspectiveMixin, DebateMixin, JuryMixin,
    DelphiMixin, ResearchMixin, CognitiveMixin, DialecticalMixin, RecoveryMixin,
):
```

| New Mixin | Lines | Methods Extracted |
|-----------|-------|-------------------|
| `search_mixin.py` | 486 | `_phase_context_vetting`, `_phase_deep_read`, `_vet_results`, `_vet_single`, `_enrich_query`, `_validate_evidence_coverage` |
| `perspective_mixin.py` | 198 | `_phase_2_perspectives`, `_phase_3_critique`, `_phase_4_stress_test` |
| `debate_mixin.py` | 104 | `_phase_debate_opening`, `_phase_debate_rebuttal`, `_phase_debate_judge`, `_phase_debate_cross_examine` |
| `jury_mixin.py` | 169 | `_phase_jury_generate`, `_phase_jury_critique`, `_phase_jury_verify_and_meta_eval`, `_phase_jury_weighted_ranking` |
| `dialectical_mixin.py` | 240 | scientific, socratic, pre-mortem, bayesian, dialectical, analogical phases |
| `delphi_mixin.py` | 168 | `_phase_delphi_round1`, `_phase_delphi_aggregation`, `_phase_delphi_round2`, `_phase_delphi_convergence`, `_phase_delphi_dissent` |
| `cognitive_mixin.py` | 265 | CoVe, SoT, ToT, PoT, Self-Discover phases |
| `recovery_mixin.py` | 44 | `_run_recovery_path` |
| `research_mixin.py` | 88 | `_phase_research_web_search` |

**Circular import fix:** Mixins import `TOKEN_OPTIMIZATION` and `USE_PHASE_SUBAGENTS` from `reasoner.pipeline` at function scope (not module level).

**Helper moved:** `_parse_critique_scores()` moved from `pipeline.py` to `reasoner.parsing` to break circular import.

---

## Autonomous Debugging Fixes

### Generated Test Syntax Fixes

**Files:** `tests/healing/generated_tests/` (19 files)

- Fixed invalid Python syntax in auto-generated tests:
  - Bad imports using `/` instead of `.`
  - Escaped newline characters (`\n`) in string literals

### L2Index Async Test Fix

**File:** `tests/test_codebase_audit.py`

- `TestL2IndexBoundedGrowth::test_l2index_evicts_when_max_entries_exceeded`
- `L2Index.add()` is async but was called synchronously.
- Fix: Added `@pytest.mark.asyncio` + `await index.add(...)`.

### Pre-existing Bugs (Already Fixed During Refactoring)

The `autonomous_bug_fix_report.json` identified 3 confirmed bugs. All were already resolved:

| Bug | Description | Status |
|-----|-------------|--------|
| **BUG-001** | `run_followup_stream` sent stale `previous_synthesis` to neuro/learn | ✅ Already fixed in `streaming.py:426-430` |
| **BUG-002** | `clear_cache()` didn't clear `_MEMORY_CACHE` | ✅ Already fixed in `api/__init__.py:298` |
| **BUG-003** | `AuthManager.generate_key()` mutated `self._keys` without lock | ✅ Already fixed in `auth.py:142-143` |

---

## File Change Matrix

### Modified Files (Tracked)

| File | Before | After | Change |
|------|--------|-------|--------|
| `src/reasoner/pipeline.py` | 1,789 | 597 | **-1,192** |
| `src/reasoner/phases.py` | 1,394 | 30 | **-1,364** |
| `src/reasoner/presets.py` | 1,195 | 103 | **-1,092** |
| `src/reasoner/llm.py` | 687 | 38 | **-649** |
| `src/reasoner/parsing.py` | 254 | 283 | **+29** |
| `src/reasoner/api/__init__.py` | 522 | 521 | **-1** |
| `src/reasoner/application/handlers/handlers.py` | 442 | 430 | **-12** |

### Deleted Files

| File | Lines | Reason |
|------|-------|--------|
| `src/reasoner/infrastructure/llm/new_pipeline.py` | 1,024 | Broken runtime — `AttributeError` on `get_provider_for_role` |

### New Files (Untracked)

#### Mixins (`src/reasoner/application/mixins/`)
- `__init__.py` (23 lines)
- `search_mixin.py` (486 lines)
- `perspective_mixin.py` (198 lines)
- `debate_mixin.py` (104 lines)
- `jury_mixin.py` (169 lines)
- `dialectical_mixin.py` (240 lines)
- `delphi_mixin.py` (168 lines)
- `cognitive_mixin.py` (265 lines)
- `recovery_mixin.py` (44 lines)
- `research_mixin.py` (88 lines)

#### Domain (`src/reasoner/domain/`)
- `preset_core.py` (221 lines)
- `preset_registry.py` (1,276 lines)

#### LLM Infrastructure (`src/reasoner/infrastructure/llm/`)
- `__init__.py` (12 lines)
- `base.py` (64 lines)
- `router.py` (144 lines)
- `registry.py` (164 lines)
- `utils.py` (70 lines)
- `exceptions.py` (66 lines)
- `ports.py` (421 lines) — *pre-existing, not created in this refactor*
- `providers/__init__.py` (8 lines)
- `providers/openai_compat.py` (258 lines)

#### Phases (`src/reasoner/phases/`)
- `__init__.py` (29 lines)
- `_shared.py` (93 lines)
- `_universal.py` (209 lines)
- `multi_perspective.py` (47 lines)
- `debate.py` (32 lines)
- `jury.py` (26 lines)
- `research.py` (10 lines)
- `scientific.py` (14 lines)
- `socratic.py` (14 lines)
- `pre_mortem.py` (67 lines)
- `bayesian.py` (71 lines)
- `dialectical.py` (72 lines)
- `analogical.py` (118 lines)
- `delphi.py` (116 lines)
- `cove.py` (93 lines)
- `sot.py` (72 lines)
- `tot.py` (97 lines)
- `pot.py` (68 lines)
- `self_discover.py` (78 lines)

---

## Backward Compatibility

All original import paths remain functional via shim files:

```python
from reasoner.phases import classification_prompt        # ✅ works via shim
from reasoner.presets import PRESETS                      # ✅ works via shim
from reasoner.llm import BaseLLMProvider, LLMError        # ✅ works via shim
```

---

## Raw Diff

The complete `git diff` (modified tracked files only) is saved alongside this report as:

```
REFACTORING_CHANGES.diff
```

Size: ~577 KB
