# Phase 4 — VS Integration

> **Duration:** Weeks 3–6 (Days 18–38)  
> **Risk:** High — touches core pipeline stages, potential for regression  
> **Goal:** Wire VS primitives into all pipeline stages behind feature flags.

**Prerequisite:** Phase 3 merged and green. All constants, primitives, and config models must be frozen.

---

## Architecture Rule

Every VS integration point MUST:
1. Check the corresponding `VSFeatureFlags` flag before executing VS logic.
2. If flag is `False`, fall back to pre-VS behavior exactly.
3. Propagate `TaintRecord.vs_metadata` on every output.
4. Use `asyncio.gather` for independent LLM/NLI calls.

---

## 4.1 Track 5A — Probes + Decomposition + Coverage (Week 4)

### 5A-P: Probe Generation (`IntentConsistencyStage`)
**File:** `src/reasoner/phases/vs_probe_generation.py` (new)  
**Integration:** `src/reasoner/application/mixins/perspective_mixin.py` or `phases/multi_perspective.py`

```python
from reasoner.ara_vs_constants import VS_K_PROBES, VS_TAIL_THRESHOLD_RADIOLOGY, VS_PROBE_MIN_SEMANTIC_DISTANCE, LOG_VS_PROBE_COUNT, LOG_VS_PROBE_DOMAIN
from reasoner.ara_verbalized_sampling import VSMode, build_vs_prompt, parse_vs_response, sample_from_vs
from reasoner.vs_config import VSFeatureFlags

DOMAIN_PROBE_TEMPLATES = {
    "radiology": "Generate {k} distinct clinical questions a radiologist would ask about: {query}",
    "legal": "Generate {k} angles a legal analyst would investigate for: {query}",
    "aerospace": "Generate {k} failure-mode probes an aerospace engineer would consider for: {query}",
    "default": "Generate {k} diverse perspectives on: {query}",
}

class ProbeGenerationConfig(BaseModel):
    domain: str = "default"
    k: int = VS_K_PROBES
    tail_threshold: float = VS_TAIL_THRESHOLD_RADIOLOGY

class ProbeSet(BaseModel):
    probes: list[str]
    source: str = "vs_tail"

async def generate_probes_with_vs(
    query: str,
    config: ProbeGenerationConfig,
    llm_client,
    flags: VSFeatureFlags,
) -> ProbeSet:
    if not flags.probe_generation:
        return ProbeSet(probes=[query], source="direct")

    system, user = build_vs_prompt(query, VSMode.TAIL, config.k)
    raw = await llm_client.generate(system=system, user=user)
    result = parse_vs_response(raw)

    # Identity filter: remove probes identical to query
    probes = [c.text for c in result.candidates if c.text.lower() != query.lower()]

    # Semantic distance filter: keep probes sufficiently different
    # (simplified — use embedding cosine distance in production)
    probes = [p for p in probes if _semantic_distance(p, query) >= VS_PROBE_MIN_SEMANTIC_DISTANCE]

    if len(probes) < 2:
        # Fallback to STANDARD mode
        system, user = build_vs_prompt(query, VSMode.STANDARD, config.k)
        raw = await llm_client.generate(system=system, user=user)
        result = parse_vs_response(raw)
        probes = [c.text for c in result.candidates if c.text.lower() != query.lower()]

    return ProbeSet(probes=probes[:config.k], source="vs_tail")
```

**AC:** `test_vs_probe_generation.py` (8 tests):
- Template rendering per domain
- Tail threshold filtering
- Identity filter removes duplicates
- Fallback to STANDARD when <2 probes
- TaintRecord propagation
- Feature flag bypass
- Regression: flag disabled → direct fallback

---

### 5A-D: Decomposition (`QueryDecompositionStage`)
**File:** `src/reasoner/phases/vs_decomposition.py` (new)

```python
class DecompositionVSConfig(BaseModel):
    top_n: int = Field(default=VS_K_DECOMPOSITION, le=VS_K_DECOMPOSITION)

class VSDecompositionResult(BaseModel):
    sub_queries: list[str]
    source: str = "vs"

async def decompose_with_vs(
    query: str,
    config: DecompositionVSConfig,
    llm_client,
    flags: VSFeatureFlags,
) -> VSDecompositionResult:
    if not flags.decomposition:
        return VSDecompositionResult(sub_queries=[query], source="direct")

    system, user = build_vs_prompt(query, VSMode.STANDARD, VS_K_DECOMPOSITION)

    for attempt in range(VS_PARSE_MAX_RETRIES + 1):
        raw = await llm_client.generate(system=system, user=user)
        try:
            result = parse_vs_response(raw)
            # Sort by probability descending
            sorted_candidates = sorted(result.candidates, key=lambda c: c.probability, reverse=True)
            return VSDecompositionResult(
                sub_queries=[c.text for c in sorted_candidates[:config.top_n]],
                source="vs",
            )
        except ValueError:
            if attempt == VS_PARSE_MAX_RETRIES:
                break
            continue

    # Final fallback: direct
    return VSDecompositionResult(sub_queries=[query], source="direct")
```

**AC:** `test_vs_decomposition.py` (6 tests):
- Sort by probability
- Validation: top_n ≤ k
- Retry on parse failure
- Final fallback to direct
- Taint propagation
- Feature flag bypass

---

### 5A-C: Coverage Audit (`CoverageAuditStage`)
**File:** `src/reasoner/phases/vs_coverage_audit.py` (new)

```python
class GapType(str, Enum):
    GENUINE = "genuine"
    PHRASING_MISMATCH = "phrasing_mismatch"
    COVERED = "covered"

class CoverageAuditResult(BaseModel):
    gaps: list[tuple[str, GapType]]
    coverage_ratio: float

async def audit_claim_coverage_vs(
    claims: list[str],
    evidence: list[str],
    llm_client,
    flags: VSFeatureFlags,
) -> CoverageAuditResult:
    if not flags.coverage_audit:
        return CoverageAuditResult(gaps=[], coverage_ratio=1.0)

    # Use VS to generate paraphrases of each claim
    # Then check overlap with evidence using NLI
    gaps = []
    for claim in claims:
        paraphrases = await _generate_paraphrases_vs(claim, llm_client)
        overlap = await _check_overlap_with_evidence(paraphrases, evidence)
        if overlap < 0.5:
            gaps.append((claim, GapType.GENUINE))
        elif overlap < 0.9:
            gaps.append((claim, GapType.PH RASING_MISMATCH))

    coverage = 1.0 - (len([g for g in gaps if g[1] == GapType.GENUINE]) / max(len(claims), 1))
    return CoverageAuditResult(gaps=gaps, coverage_ratio=coverage)
```

**AC:** `test_vs_coverage_audit.py` (6 tests):
- All 3 gap types detected
- Coverage ratio calculation
- Taint severity assignment
- Feature flag bypass
- Zero LLM calls when disabled
- Regression: disabled → coverage_ratio=1.0

---

## 4.2 Track 5B — VS Generation Stage (Week 5 — CRITICAL PATH)

**File:** `src/reasoner/phases/vs_generation.py` (new)

```python
class GenerationStrategy(str, Enum):
    BEST_VERIFIABLE = "best_verifiable"
    ENSEMBLE = "ensemble"
    TOP_PROBABILITY = "top_probability"

class VSGenerationConfig(BaseModel):
    strategy: GenerationStrategy = GenerationStrategy.BEST_VERIFIABLE
    k: int = VS_K_GENERATION
    max_parallel_nli: int = Field(default=3, le=VS_K_GENERATION)
    profile: VSDeploymentProfile = VSDeploymentProfile.BALANCED

class GenerationCandidate(BaseModel):
    text: str
    probability: float
    nli_score: float | None = None
    selected: bool = False

class VSGenerationResult(BaseModel):
    candidates: list[GenerationCandidate]
    selected: GenerationCandidate

    @field_validator("candidates")
    @classmethod
    def exactly_one_selected(cls, v: list[GenerationCandidate]) -> list[GenerationCandidate]:
        selected = [c for c in v if c.selected]
        if len(selected) != 1:
            raise ValueError(f"Exactly one candidate must be selected, got {len(selected)}")
        return v

async def generate_with_vs(
    query: str,
    config: VSGenerationConfig,
    llm_client,
    nli_gate,
    flags: VSFeatureFlags,
) -> VSGenerationResult:
    if not flags.generation:
        # Direct fallback — single LLM call, no VS
        text = await llm_client.generate(user=query)
        cand = GenerationCandidate(text=text, probability=1.0, nli_score=None, selected=True)
        return VSGenerationResult(candidates=[cand], selected=cand)

    # 1. Single LLM call to generate k candidates
    system, user = build_vs_prompt(query, VSMode.STANDARD, config.k)
    raw = await llm_client.generate(system=system, user=user)
    vs_result = parse_vs_response(raw)

    candidates = [
        GenerationCandidate(text=c.text, probability=c.probability, nli_score=None, selected=False)
        for c in vs_result.candidates
    ]

    # 2. Strategy routing
    if config.strategy == GenerationStrategy.TOP_PROBABILITY:
        selected = max(candidates, key=lambda c: c.probability)
        selected.selected = True
        return VSGenerationResult(candidates=candidates, selected=selected)

    if config.strategy == GenerationStrategy.ENSEMBLE:
        # Pick highest probability (deterministic ensemble)
        selected = max(candidates, key=lambda c: c.probability)
        selected.selected = True
        return VSGenerationResult(candidates=candidates, selected=selected)

    # BEST_VERIFIABLE: pre-commit NLI budget
    nli_budget = PROFILE_NLI_BUDGET[config.profile]
    # Score top candidates with NLI in parallel
    nli_tasks = [
        asyncio.create_task(nli_gate.score_entailment(query, c.text))
        for c in candidates[:nli_budget]
    ]
    nli_scores = await asyncio.gather(*nli_tasks)

    for i, score in enumerate(nli_scores):
        candidates[i].nli_score = score

    # Select candidate with max NLI score
    scored = [c for c in candidates if c.nli_score is not None]
    if scored:
        selected = max(scored, key=lambda c: c.nli_score or 0.0)
    else:
        selected = candidates[0]
    selected.selected = True

    return VSGenerationResult(candidates=candidates, selected=selected)
```

**Error fallback (3-level):**
```python
    try:
        return await _generate_with_vs_inner(...)
    except LLMError as e:
        logger.warning("VS Generation L1 retry: %s", e)
        # L1: retry with same prompt
        try:
            return await _generate_with_vs_inner(...)
        except LLMError as e2:
            logger.warning("VS Generation L2 simplified prompt: %s", e2)
            # L2: simplified prompt
            try:
                return await _generate_with_vs_inner(simplified=True)
            except LLMError as e3:
                logger.error("VS Generation L3 direct fallback: %s", e3)
                # L3: direct generation
                text = await llm_client.generate(user=query)
                cand = GenerationCandidate(text=text, probability=1.0, selected=True)
                return VSGenerationResult(candidates=[cand], selected=cand)
```

**TaintRecord:**
```python
vs_metadata = {
    "strategy": config.strategy,
    "k": config.k,
    "nli_scores": [c.nli_score for c in candidates],
    "selected_rank": candidates.index(selected),
}
```

**AC:** `test_vs_generation_strategies.py` (10 tests) + `test_vs_generation_invariants.py` (4 tests):
- BEST_VERIFIABLE: NLI ordering correct
- ENSEMBLE: max probability wins
- TOP_PROBABILITY: first candidate wins
- 3-level fallback triggers correctly
- Pre-commit NLI budget respected (LLM counter = 1)
- Exactly one selected=True
- `all_disabled()` → identical output to pre-VS pipeline
- Race condition: concurrent generation preserves invariant

---

## 4.3 Track 5C — Post-Generation Integration (Week 6, Parallel)

### 5C-A: OutputCalibrationStage
**File:** `src/reasoner/phases/vs_calibration.py` (new)

```python
class VSCalibrationSignals(BaseModel):
    entropy: float
    support_ratio: float
    nli_mean: float
    rank_stability: float

def compute_verbalized_entropy(candidates: list[VSCandidate]) -> float:
    probs = [c.probability for c in candidates]
    return -sum(p * math.log(p) for p in probs if p > 0)

def compute_vs_calibrated_confidence(signals: VSCalibrationSignals) -> float:
    return (
        W_ENTROPY * (1.0 - signals.entropy) +
        W_SUPPORT * signals.support_ratio +
        W_NLI * signals.nli_mean +
        W_RANK * signals.rank_stability
    )

async def extract_calibration_signals(
    generation_result: VSGenerationResult,
    nli_gate,
    flags: VSFeatureFlags,
) -> VSCalibrationSignals:
    if not flags.calibration:
        return VSCalibrationSignals(entropy=0.0, support_ratio=1.0, nli_mean=1.0, rank_stability=1.0)

    entropy = compute_verbalized_entropy([
        VSCandidate(text=c.text, probability=c.probability)
        for c in generation_result.candidates
    ])
    nli_mean = sum(c.nli_score or 0.0 for c in generation_result.candidates) / len(generation_result.candidates)
    # ... etc
    return VSCalibrationSignals(entropy=entropy, support_ratio=1.0, nli_mean=nli_mean, rank_stability=1.0)
```

**AC:** `test_vs_calibration.py` (7 tests):
- Entropy known values (uniform vs peaked)
- Perfect signals → confidence ≈ 1.0
- Worst signals → confidence ≈ 0.0
- Unit interval [0, 1]
- Weights sum to 1.0
- Feature flag bypass
- Regression: disabled → default perfect signals

---

### 5C-B: ClaimExtractionStage
**File:** `src/reasoner/phases/vs_claim_extraction.py` (new)

```python
class ClaimExtractionMode(str, Enum):
    SINGLE = "single"
    UNION = "union"
    CONSENSUS = "consensus"

class VSClaimExtractionConfig(BaseModel):
    mode: ClaimExtractionMode = ClaimExtractionMode.SINGLE

class ExtractedClaimSet(BaseModel):
    claims: list[str]
    source: str

async def extract_claims_from_vs_candidates(
    candidates: list[GenerationCandidate],
    config: VSClaimExtractionConfig,
    llm_client,
    flags: VSFeatureFlags,
) -> ExtractedClaimSet:
    if not flags.claim_extraction:
        return ExtractedClaimSet(claims=[c.text for c in candidates], source="direct")

    if config.mode == ClaimExtractionMode.SINGLE:
        return ExtractedClaimSet(claims=[candidates[0].text], source="single")

    if config.mode == ClaimExtractionMode.UNION:
        # Parallel extraction from all candidates
        tasks = [asyncio.create_task(_extract_claims(c.text, llm_client)) for c in candidates]
        results = await asyncio.gather(*tasks)
        all_claims = list(set().union(*results))
        return ExtractedClaimSet(claims=all_claims, source="union")

    # CONSENSUS
    tasks = [asyncio.create_task(_extract_claims(c.text, llm_client)) for c in candidates]
    results = await asyncio.gather(*tasks)
    # Keep claims appearing in >50% of candidates
    claim_counts = Counter([claim for sublist in results for claim in sublist])
    consensus = [claim for claim, count in claim_counts.items() if count > len(candidates) / 2]
    return ExtractedClaimSet(claims=consensus, source="consensus")
```

**AC:** `test_vs_claim_extraction.py` (7 tests):
- SINGLE mode: one candidate
- UNION mode: all unique claims
- CONSENSUS mode: majority claims only
- Parallel extraction
- Feature flag bypass
- Regression: disabled → direct pass-through
- Empty candidates → empty claims

---

### 5C-C: TwoTierVerificationRouting
**File:** `src/reasoner/phases/vs_verification_routing.py` (new)

```python
class VerificationRoute(str, Enum):
    NLI_ONLY = "nli_only"
    NLI_THEN_LLM = "nli_then_llm"
    CONSERVATIVE = "conservative"

async def route_claim_by_vs_probability(
    claim: str,
    probability: float,
    nli_gate,
    flags: VSFeatureFlags,
) -> tuple[VerificationRoute, dict]:
    if not flags.verification_routing:
        return VerificationRoute.NLI_ONLY, {}

    if probability >= VS_ROUTING_HIGH_PROB:
        return VerificationRoute.NLI_ONLY, {"confidence": "high"}

    if probability >= VS_ROUTING_MEDIUM_PROB:
        return VerificationRoute.NLI_THEN_LLM, {"confidence": "medium"}

    # CONSERVATIVE: always UNKNOWN, never LLM
    return VerificationRoute.CONSERVATIVE, {"confidence": "low", "human_review_flag": True}
```

**AC:** `test_vs_verification_routing.py` (6 tests):
- Truth table: high→NLI_ONLY, medium→NLI_THEN_LLM, low→CONSERVATIVE
- CONSERVATIVE never routes to LLM
- Backward compatibility: disabled → NLI_ONLY
- Feature flag bypass
- Boundary values (exactly 0.70, 0.30)
- Human review flag set on CONSERVATIVE

---

### 5C-D: ConflictSurfacingStage
**File:** `src/reasoner/phases/vs_conflict_surfacing.py` (new)

```python
class CrossCandidateConflict(BaseModel):
    claim: str
    support_ratio: float
    conflict_priority: int
    recommendation: str  # HUMAN_REVIEW, FLAG, MONITOR

async def surface_cross_candidate_conflicts(
    candidates: list[GenerationCandidate],
    nli_gate,
    flags: VSFeatureFlags,
) -> list[CrossCandidateConflict]:
    if not flags.conflict_surfacing:
        return []

    # Extract claims from all candidates
    all_claims = []
    for c in candidates:
        claims = await _extract_claims(c.text, None)  # or reuse from ClaimExtractionStage
        all_claims.extend([(claim, c.probability) for claim in claims])

    # Compute support ratio per claim
    claim_support = Counter()
    for claim, prob in all_claims:
        claim_support[claim] += prob

    conflicts = []
    for claim, total_prob in claim_support.items():
        support_ratio = total_prob / sum(c.probability for c in candidates)
        # Check for NLI contradictions between candidates
        contradictions = await _check_contradictions(claim, candidates, nli_gate)
        if contradictions:
            priority = len(contradictions)
            rec = "HUMAN_REVIEW" if support_ratio < 0.3 else "FLAG" if support_ratio < 0.7 else "MONITOR"
            conflicts.append(CrossCandidateConflict(
                claim=claim, support_ratio=support_ratio, conflict_priority=priority, recommendation=rec
            ))

    return sorted(conflicts, key=lambda c: (-c.conflict_priority, -c.support_ratio))
```

**AC:** `test_vs_conflict_surfacing.py` (6 tests):
- All 3 recommendation types (HUMAN_REVIEW, FLAG, MONITOR)
- Sorted by priority then support ratio
- Zero LLM calls (only NLI)
- Feature flag bypass
- Regression: disabled → empty list
- Empty candidates → empty conflicts

---

### 5C-E: BehavioralAudit Observability
**File:** `src/reasoner/phases/vs_behavioral_audit.py` (new)

```python
class VSEntropyStore(ABC):
    @abstractmethod
    async def push(self, entropy: float) -> None: ...
    @abstractmethod
    async def get_mean(self, window: int = 100) -> float: ...

class InMemoryVSEntropyStore(VSEntropyStore):
    def __init__(self):
        self._window: deque[float] = deque(maxlen=100)

    async def push(self, entropy: float) -> None:
        self._window.append(entropy)

    async def get_mean(self, window: int = 100) -> float:
        recent = list(self._window)[-window:]
        return sum(recent) / len(recent) if recent else 0.0

class RedisVSEntropyStore(VSEntropyStore):
    # Implementation using Redis sorted set or list
    ...

async def log_vs_behavioral_audit(
    generation_result: VSGenerationResult,
    entropy_store: VSEntropyStore,
    flags: VSFeatureFlags,
) -> None:
    if not flags.behavioral_audit:
        return

    entropy = compute_verbalized_entropy([
        VSCandidate(text=c.text, probability=c.probability)
        for c in generation_result.candidates
    ])
    await entropy_store.push(entropy)
    mean_entropy = await entropy_store.get_mean()

    # Alert on >30% entropy drop
    if len(entropy_store._window) >= 10:
        recent_mean = await entropy_store.get_mean(window=10)
        if recent_mean < mean_entropy * 0.7:
            logger.warning("VS mode collapse detected: entropy dropped >30%%", extra={
                LOG_VS_ENTROPY: entropy,
                LOG_VS_MODE_COLLAPSE: True,
            })
```

**AC:** `test_vs_observability.py` (5 tests):
- Log keys present
- Non-blocking (fire-and-forget)
- Rolling mean calculation
- Alert on >30% drop
- InMemory store works without Redis

---

## 4.4 Track 5D — Vertical Domain Configs (Week 6, Parallel)

**Files:**
- `src/reasoner/vs_vertical_configs/radiology_config.py`
- `src/reasoner/vs_vertical_configs/legal_config.py`
- `src/reasoner/vs_vertical_configs/aerospace_config.py`
- `src/reasoner/vs_vertical_configs/__init__.py`

```python
# radiology_config.py
from reasoner.vs_config import VSVerticalConfig, VSVerticalRegistry
from reasoner.ara_vs_constants import VS_K_RADIOLOGY_GENERATION, VS_TAIL_THRESHOLD_RADIOLOGY

RADIOLOGY_CONFIG = VSVerticalConfig(
    domain="radiology",
    k=VS_K_RADIOLOGY_GENERATION,
    tail_threshold=VS_TAIL_THRESHOLD_RADIOLOGY,
    generation_strategy="best_verifiable",
    probe_template="Generate {k} distinct clinical questions a radiologist would ask about: {query}",
    compliance_flags=["fda_510k", "hipaa_minimal"],
)

VSVerticalRegistry.register(RADIOLOGY_CONFIG)
```

Similar for legal (tail=0.08, human_review_on_low_prob) and aerospace (tail=0.06, CMMC flags).

**VS + SaaS tier integration:**
```python
# In vs_config.py
class VSVerticalConfig(BaseModel):
    ...
    min_subscription_tier: SubscriptionTier = SubscriptionTier.FREE

# In api/dependencies.py — extend require_tier
def require_tier_for_vertical(vertical: str):
    config = VSVerticalRegistry.get(vertical)
    return require_tier(config.min_subscription_tier)
```

**AC:** `test_vertical_configs.py` (6 tests):
- Auto-register on import
- Get by domain returns correct config
- Default fallback works
- Tier enforcement: radiology/aerospace require PRO
- Legal requires PRO
- Free user blocked from PRO vertical → 403

---

## Testing Strategy

| Test File | Tests | Coverage |
|---|---|---|
| `test_vs_probe_generation.py` | 8 | Templates, filters, fallback, taint, regression |
| `test_vs_decomposition.py` | 6 | Sort, validation, retry, fallback, taint, flag |
| `test_vs_coverage_audit.py` | 6 | Gap types, ratio, taint, flag, disabled |
| `test_vs_generation_strategies.py` | 10 | BEST_VERIFIABLE, ENSEMBLE, TOP_PROB, fallback |
| `test_vs_generation_invariants.py` | 4 | NLI ordering, budget, counter=1, race |
| `test_vs_calibration.py` | 7 | Entropy, perfect/worst signals, unit interval |
| `test_vs_claim_extraction.py` | 7 | SINGLE, UNION, CONSENSUS, parallel, flag |
| `test_vs_verification_routing.py` | 6 | Truth table, no LLM in CONSERVATIVE, flag |
| `test_vs_conflict_surfacing.py` | 6 | 3 rec types, sorted, zero LLM, flag |
| `test_vs_observability.py` | 5 | Log keys, non-blocking, mean, alert, in-memory |
| `test_vertical_configs.py` | 6 | Register, get, tier enforcement |

---

## Definition of Done

- [ ] All VS stages have feature flag gates.
- [ ] `VSFeatureFlags.all_disabled()` → output identical to pre-VS pipeline.
- [ ] `TaintRecord.vs_metadata` on every pipeline output.
- [ ] Zero magic numbers — all in `ara_vs_constants.py`.
- [ ] `asyncio.gather` for independent LLM/NLI calls.
- [ ] pytest coverage ≥ 85% per new module.
- [ ] All inter-stage interfaces are Pydantic BaseModel.
