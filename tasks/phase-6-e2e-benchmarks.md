# Phase 6 — E2E Tests & Benchmarks

> **Duration:** Week 7 (Days 43–49)  
> **Risk:** Low — tests and docs only, no production code changes  
> **Goal:** Prove correctness, measure performance, and document everything.

**Prerequisite:** Phase 5 merged and green. All VS integration code must be in `main`.

---

## 6.1 VS Pipeline E2E Tests (TRACK 9)

### 6.1.1 Radiology Pipeline
**File:** `tests/test_vs_pipeline_radiology.py`

```python
@pytest.mark.integration
@pytest.mark.slow
async def test_radiology_pipeline_vs():
    """End-to-end radiology case with VS enabled."""
    result = await run_pipeline(
        problem="Identify lesions in this chest CT",
        preset="radiology-premium",
        vs_flags=VSFeatureFlags.all_enabled(),
    )
    
    # 7 assertions
    assert len(result.decomposition_angles) >= 3, "Decomposition produced multiple angles"
    assert result.generation_strategy == "best_verifiable", "Radiology uses BEST_VERIFIABLE"
    assert result.nli_scores, "NLI scoring ran"
    assert result.selected_candidate.nli_score == max(c.nli_score for c in result.candidates), "Max NLI selected"
    assert result.claims, "Claims extracted"
    assert result.conflicts is not None, "Conflict surfacing ran"
    assert result.taint_record.vs_metadata is not None, "Taint propagated"
```

**AC:** All 7 assertions pass; LLM call counter = 1 for generation.

---

### 6.1.2 Legal Pipeline
**File:** `tests/test_vs_pipeline_legal.py`

```python
async def test_legal_pipeline_conservative_routing():
    result = await run_pipeline(
        problem="Draft a liability clause for SaaS terms",
        preset="legal-premium",
        vs_flags=VSFeatureFlags.all_enabled(),
    )
    assert result.verification_route == VerificationRoute.CONSERVATIVE
    assert result.human_review_flag is True
```

**AC:** CONSERVATIVE routing enforced; human_review_flag set.

---

### 6.1.3 Aerospace Pipeline
**File:** `tests/test_vs_pipeline_aerospace.py`

```python
async def test_aerospace_failure_mode_probes():
    result = await run_pipeline(
        problem="Analyze failure modes for landing gear hydraulics",
        preset="aerospace-premium",
        vs_flags=VSFeatureFlags.all_enabled(),
    )
    assert any("failure" in p.lower() for p in result.probes), "Failure-mode probes generated"
    assert result.human_review_flag is True
```

**AC:** Tail threshold 0.06 produces aggressive probes; human review flagged.

---

### 6.1.4 Golden Regression Test
**File:** `tests/test_vs_all_flags_disabled.py` — **MOST IMPORTANT TEST**

```python
async def test_vs_all_flags_disabled_identical_to_baseline():
    """With all VS flags disabled, output must be identical to pre-VS pipeline."""
    baseline = await run_pipeline(
        problem="Explain quantum computing",
        preset="balanced",
        vs_flags=VSFeatureFlags.all_disabled(),
    )
    # Compare against stored baseline snapshot
    assert baseline.output == load_baseline_snapshot("quantum_computing_balanced")
```

**AC:** Output byte-for-byte identical to pre-VS snapshot (or semantic equivalence).

---

## 6.2 Global Invariant Tests (TRACK 9.2)

**File:** `tests/test_vs_invariants_global.py`

```python
def test_nli_before_llm_at_all_integration_points():
    """NLI scoring must happen before any secondary LLM call at VS integration points."""
    # Static analysis or runtime trace
    ...

def test_llm_call_counter_equals_one_per_vs_generation():
    """Each VS generation stage must make exactly 1 LLM call."""
    ...

def test_taint_record_vs_metadata_on_every_stage_output():
    """Every stage that touches VS must populate taint_record.vs_metadata."""
    ...

def test_zero_magic_numbers():
    """No numeric literals in VS files outside ara_vs_constants.py."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "[0-9]", "src/reasoner/phases/vs_*.py"],
        capture_output=True, text=True
    )
    # Filter out constants imports and obvious false positives
    ...
```

**AC:** All 4 invariant tests pass.

---

## 6.3 SaaS E2E Tests (TRACK 9.3)

| Test | File | AC |
|---|---|---|
| All `reproduce_*.py` pass | Root level | Discovery client, HyperGate regex, search filter, URL norm |
| `pytest -v` ≥ baseline | CI | No regression in existing tests |
| `npm run build` — 0 errors | `ui-next/` | Production build succeeds |
| `npm run lint` — passes | `ui-next/` | No new lint errors |
| Synthesis latency <2s | `tests/test_synthesis_latency.py` | 500-word response |
| Rate limiter 503 | `tests/test_rate_limiter_fail_closed.py` | RuntimeError → 503 |
| Prompt injection sanitized | `tests/test_sanitize_for_prompt.py` | Injection string neutralized |
| Auth key LRU | `tests/test_auth_manager_lru.py` | 10,001 keys → eviction |
| Error Boundary | Manual test | Synthetic throw caught |

---

## 6.4 Benchmarks (TRACK 10.1)

### 6.4.1 Latency Benchmark
**File:** `benchmarks/benchmark_vs_latency.py`

```python
async def benchmark_vs_latency():
    """Measure wall-clock per stage, VS vs baseline, per deployment profile."""
    profiles = [VSDeploymentProfile.LATENCY_SENSITIVE, VSDeploymentProfile.BALANCED, VSDeploymentProfile.MAX_ACCURACY]
    queries = load_benchmark_queries(n=50)
    
    results = []
    for profile in profiles:
        for query in queries:
            baseline_time = await measure_pipeline(query, vs_disabled=True)
            vs_time = await measure_pipeline(query, vs_disabled=False, profile=profile)
            results.append({
                "profile": profile,
                "query": query,
                "baseline_ms": baseline_time,
                "vs_ms": vs_time,
                "overhead_pct": (vs_time - baseline_time) / baseline_time * 100,
            })
    
    # Commit overhead table to benchmarks/vs_latency_overhead.md
    write_overhead_table(results)
```

**AC:** Overhead table committed; overhead < 50% for LATENCY_SENSITIVE.

---

### 6.4.2 Diversity Benchmark
**File:** `benchmarks/benchmark_vs_diversity.py`

```python
async def benchmark_vs_diversity():
    """50 queries × 3 verticals × (direct vs VS-Standard)."""
    # Use semantic embedding distance as diversity proxy
    # VS ≥ 1.3× diversity for ≥ 2/3 verticals
```

**AC:** Diversity improvement ≥ 1.3× for ≥ 2/3 verticals.

---

### 6.4.3 Calibration Benchmark
**File:** `benchmarks/benchmark_vs_calibration.py`

```python
async def benchmark_vs_calibration():
    """Verbalized entropy vs model uncertainty correlation."""
    # Pearson r ≥ 0.6
```

**AC:** Pearson r ≥ 0.6 between entropy and uncertainty.

---

## 6.5 Documentation (TRACK 10.2)

| Document | Content | Owner |
|---|---|---|
| `docs/VS.md` | VS architecture, integration points, flag reference | Tech Lead |
| `docs/ENVIRONMENT.md` | All env vars (Supabase, Stripe, Redis, VS, port, debug) | DevOps |
| `CHANGELOG.md` | All phases documented with PR links | Release Manager |
| `README.md` | Quickstart with Docker Compose, VS features, vertical configs | Tech Lead |

**AC:** Every public VS function has docstring with explicit trade-offs.

---

## 6.6 Final PR Checklist (TRACK 10.3)

- [ ] `test_vs_all_flags_disabled.py` (golden regression) passes
- [ ] `test_vs_invariants_global.py` (zero magic numbers) passes
- [ ] All `reproduce_*.py` pass
- [ ] `VSFeatureFlags.all_disabled()` verified against baseline snapshots
- [ ] Benchmark tables reviewed and committed
- [ ] Open Issues table updated (see TODO_1.md)
- [ ] Security scan: `pip-audit` zero high-severity
- [ ] `npm audit --audit-level high` zero vulnerabilities

---

## Definition of Done

- [ ] All E2E tests pass (radiology, legal, aerospace, regression, invariants).
- [ ] Benchmark overhead table committed.
- [ ] Diversity ≥ 1.3× for ≥ 2/3 verticals.
- [ ] Calibration Pearson r ≥ 0.6.
- [ ] Documentation complete and reviewed.
- [ ] CI green on `main`.
