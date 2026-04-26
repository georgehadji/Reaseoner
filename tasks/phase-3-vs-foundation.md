# Phase 3 — VS Foundation

> **Duration:** Weeks 2–3 (Days 11–17)  
> **Risk:** Medium — new module, but isolated from existing pipeline  
> **Goal:** Establish the Verbalized Sampling primitive layer. All downstream VS tracks depend on this.

**Prerequisite:** Phase 2 merged and green.

---

## 3.0 Decisions (Day 11 — BLOCKER)

Before writing any code, resolve these in `docs/decisions/vs-constants.md`:

| Decision | Default | Rationale |
|---|---|---|
| k defaults per stage | Decomp=5, Gen=5, Probes=5, Coverage=3, Claims=5, Radiology Gen=7 | Sufficient diversity without latency explosion |
| `VSDeploymentProfile` | LATENCY_SENSITIVE (nli=1), BALANCED (nli=3), MAX_ACCURACY (nli=5) | Trade latency vs verification depth |
| `GenerationStrategy` default | `BEST_VERIFIABLE` for regulated verticals | Safety-first default |
| Tail thresholds | radiology=0.10, legal=0.08, aerospace=0.06 | Calibrated per vertical risk tolerance |
| JSON parse error strategy | 2 retry + direct fallback | Balanced resilience vs latency |

**AC:** Decision doc approved (even if self-approved with rationale); all constants frozen in `ara_vs_constants.py`.

---

## 3.1 `ara_vs_constants.py` — First File Written

**Effort:** 2 hours  
**New file:** `src/reasoner/ara_vs_constants.py`

```python
"""Verbalized Sampling constants — zero magic numbers outside this file."""
from __future__ import annotations

# Stage k defaults
VS_K_DECOMPOSITION = 5
VS_K_GENERATION = 5
VS_K_PROBES = 5
VS_K_COVERAGE = 3
VS_K_CLAIMS = 5
VS_K_RADIOLOGY_GENERATION = 7

# Tail thresholds per vertical
VS_TAIL_THRESHOLD_RADIOLOGY = 0.10
VS_TAIL_THRESHOLD_LEGAL = 0.08
VS_TAIL_THRESHOLD_AEROSPACE = 0.06

# Routing thresholds
VS_ROUTING_HIGH_PROB = 0.70
VS_ROUTING_MEDIUM_PROB = 0.30

# Calibration weights (must sum to 1.0)
W_ENTROPY = 0.30
W_SUPPORT = 0.25
W_NLI = 0.35
W_RANK = 0.10

# Operational
VS_PARSE_MAX_RETRIES = 2
VS_CONSENSUS_MIN_SUPPORT = 2
VS_PROBE_MIN_SEMANTIC_DISTANCE = 0.15

# Feature flags (all default True)
VS_PROBE_GENERATION_ENABLED = True
VS_DECOMPOSITION_ENABLED = True
VS_COVERAGE_AUDIT_ENABLED = True
VS_GENERATION_ENABLED = True
VS_CALIBRATION_ENABLED = True
VS_CLAIM_EXTRACTION_ENABLED = True
VS_VERIFICATION_ROUTING_ENABLED = True
VS_CONFLICT_SURFACING_ENABLED = True
VS_BEHAVIORAL_AUDIT_ENABLED = True

# Structured log keys
LOG_VS_ENTROPY = "vs_entropy"
LOG_VS_STRATEGY = "vs_strategy"
LOG_VS_CANDIDATE_RANK = "vs_candidate_rank"
LOG_VS_PROBE_DOMAIN = "vs_probe_domain"
LOG_VS_PROBE_COUNT = "vs_probe_count"
LOG_VS_NLI_SCORES = "vs_nli_scores"
LOG_VS_K = "vs_k"

# Deployment profiles
class VSDeploymentProfile:
    LATENCY_SENSITIVE = "latency_sensitive"
    BALANCED = "balanced"
    MAX_ACCURACY = "max_accuracy"

PROFILE_NLI_BUDGET = {
    VSDeploymentProfile.LATENCY_SENSITIVE: 1,
    VSDeploymentProfile.BALANCED: 3,
    VSDeploymentProfile.MAX_ACCURACY: 5,
}
```

**AC:** `test_vs_constants.py` — weights sum=1.0; thresholds in (0,1); k≥2; all flags default True.

---

## 3.2 `ara_verbalized_sampling.py` — Primitives

**Effort:** 1 day  
**New file:** `src/reasoner/ara_verbalized_sampling.py`

### Models
```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class VSMode(str, Enum):
    STANDARD = "standard"
    TAIL = "tail"
    COT = "cot"

class VSCandidate(BaseModel):
    text: str = Field(..., min_length=1)
    probability: float = Field(..., ge=0.0, le=1.0)

class VSResult(BaseModel):
    candidates: list[VSCandidate]
    mode: VSMode

    @field_validator("candidates")
    @classmethod
    def normalize_and_check(cls, v: list[VSCandidate]) -> list[VSCandidate]:
        total = sum(c.probability for c in v)
        if total == 0:
            # Uniform fallback
            n = len(v)
            return [VSCandidate(text=c.text, probability=1.0 / n) for c in v]
        if abs(total - 1.0) > 0.01:
            # Renormalize
            return [VSCandidate(text=c.text, probability=c.probability / total) for c in v]
        return v
```

### Functions
```python
def build_vs_prompt(query: str, mode: VSMode, k: int) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt). No string literals — all from constants."""
    system = f"Generate exactly {k} diverse candidate answers for the query."
    if mode == VSMode.TAIL:
        system += " Include unconventional or tail-distribution candidates."
    # ... etc
    return system, f"Query: {query}\nRespond as JSON: {{\"candidates\": [{{\"text\": \"...\", \"probability\": 0.1}}]}}"

def parse_vs_response(raw: str) -> VSResult:
    """Strip fences, regex-extract JSON, validate structure."""
    # 1. Strip markdown fences
    text = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    # 2. Find JSON object
    match = re.search(r"\{[\s\S]*?\"candidates\"[\s\S]*?\}", text)
    if not match:
        raise ValueError("No JSON candidate block found in VS response")
    data = json.loads(match.group())
    return VSResult(candidates=data["candidates"], mode=data.get("mode", VSMode.STANDARD))

def sample_from_vs(candidates: list[VSCandidate]) -> VSCandidate:
    """Probability-weighted sample."""
    texts = [c.text for c in candidates]
    probs = [c.probability for c in candidates]
    idx = random.choices(range(len(texts)), weights=probs, k=1)[0]
    return candidates[idx]

def top_candidate(candidates: list[VSCandidate]) -> VSCandidate:
    """Deterministic; tie → first."""
    return max(candidates, key=lambda c: (c.probability, -candidates.index(c)))
```

**AC:** `test_vs_primitives.py` ~25 tests:
- Normalize all-zero → uniform
- Renormalize off-by-5%
- JSON fence stripping (7 cases)
- Probability-weighted sample (KL < 0.05 statistical test)
- Top candidate tie-breaking

---

## 3.3 Config Models

**Effort:** 4 hours  
**New file:** `src/reasoner/vs_config.py`

```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class VSDeploymentProfile(str, Enum):
    LATENCY_SENSITIVE = "latency_sensitive"
    BALANCED = "balanced"
    MAX_ACCURACY = "max_accuracy"

class VSFeatureFlags(BaseModel):
    probe_generation: bool = True
    decomposition: bool = True
    coverage_audit: bool = True
    generation: bool = True
    calibration: bool = True
    claim_extraction: bool = True
    verification_routing: bool = True
    conflict_surfacing: bool = True
    behavioral_audit: bool = True

    @classmethod
    def all_disabled(cls) -> "VSFeatureFlags":
        return cls(**{k: False for k in cls.model_fields})

class VSVerticalConfig(BaseModel):
    domain: str = Field(..., min_length=1)
    k: int = Field(..., ge=2)
    tail_threshold: float = Field(..., gt=0.0, lt=1.0)
    generation_strategy: str = "best_verifiable"
    probe_template: str = ""
    compliance_flags: list[str] = Field(default_factory=list)

    @field_validator("k")
    @classmethod
    def k_reasonable(cls, v: int) -> int:
        if v > 20:
            raise ValueError("k > 20 is excessive")
        return v

class VSVerticalRegistry:
    _configs: dict[str, VSVerticalConfig] = {}

    @classmethod
    def register(cls, config: VSVerticalConfig) -> None:
        cls._configs[config.domain] = config

    @classmethod
    def get(cls, domain: str) -> VSVerticalConfig:
        return cls._configs.get(domain, VSVerticalConfig(
            domain="default", k=VS_K_GENERATION, tail_threshold=VS_TAIL_THRESHOLD_RADIOLOGY
        ))
```

**AC:** `test_vs_config_models.py` ~10 tests:
- `all_disabled()` sets all flags to False
- Invalid k (>20) raises ValueError
- Missing domain returns default config
- Weight sum validation

---

## Testing Strategy

| Test File | Tests | Coverage |
|---|---|---|
| `test_vs_constants.py` | ~5 | Weight sums, threshold bounds, flag defaults |
| `test_vs_primitives.py` | ~25 | Parse, normalize, sample, top |
| `test_vs_config_models.py` | ~10 | Validation, registry, defaults |
| `test_vs_all_flags_disabled.py` | ~3 | Golden regression — no VS code path changes when disabled |

---

## Definition of Done

- [ ] `ara_vs_constants.py` frozen — no numeric literals outside it.
- [ ] `ara_verbalized_sampling.py` passes ~25 primitive tests.
- [ ] `vs_config.py` passes ~10 config tests.
- [ ] `VSFeatureFlags.all_disabled()` verified.
- [ ] pytest coverage ≥ 85% for new modules.
- [ ] All functions have type hints; zero `Any` without justification.
