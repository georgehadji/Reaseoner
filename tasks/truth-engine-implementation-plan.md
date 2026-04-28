# Implementation Plan: Vision Truth Engine

This plan outlines the staged rollout of the forensic auditing and hallucination suppression features described in `VISION_TRUTH.md`.

## Staging & Safety Strategy
- **Feature Flags:** All forensic stages will be gated by `FORENSIC_ENABLED` in `settings.py`.
- **Method-Specific Rollout:** Initially enable forensic checks for `Research` and `Scientific` methods only.
- **Shadow Mode:** Run forensic stages in "shadow mode" (log results without affecting final output) for the first iteration.
- **Fail-Safe Synthesis:** If a forensic check fails due to infrastructure (e.g., NLI model timeout), fall back to standard synthesis with an "Unverified" warning.

---

## Phase 1: Foundation & Taint Tracking (Weeks 1-2)
**Goal:** Establish the data models for provenance and basic claim-to-source mapping.

- [ ] **Model Definition:**
    - Define `TaintRecord` and `ClaimMetadata` in `src/reasoner/models.py`.
    - `ClaimMetadata` should include `source_id`, `offset_start`, `offset_end`, and `confidence`.
- [ ] **Source Metadata Enhancement:**
    - Update `SearchMixin` in `src/reasoner/application/mixins/search_mixin.py` to preserve source-offset metadata during retrieval.
- [ ] **Claim Extraction Phase:**
    - Implement a `ClaimExtractor` stage to identify atomic facts within generated content.
- [ ] **Provenance Linking:**
    - Implement a `ProvenanceLinker` utility to map extracted claims back to retrieved context using fuzzy matching or embedding-based lookup.

---

## Phase 2: Source Reliability & NLI Logic Gates (Weeks 3-4)
**Goal:** Rate the reliability of evidence and verify claims with formal logic.

- [ ] **Authority Matrix:**
    - Define `SourceReliabilityRegistry` in `src/reasoner/core/constants.py` with reliability scores for common domains (.gov, .edu, arxiv.org, etc.).
- [ ] **Reliability Scorer:**
    - Implement `ReliabilityScorer` to evaluate retrieved context in `Context Vetting`.
- [ ] **NLI Integration:**
    - Integrate a Natural Language Inference (NLI) model (e.g., DeBERTa-v3 or LLM-as-a-judge) for formal entailment checks.
- [ ] **NLIVerificationStage:**
    - Add the `NLIVerificationStage` to the pipeline to purge claims that are not logically entailed by the context.

---

## Phase 3: Adversarial Red-Teaming (Weeks 5-6)
**Goal:** Transition from helpful critique to destructive auditing.

- [ ] **AdversarialCritiqueStage:**
    - Implement the `AdversarialCritiqueStage` in `src/reasoner/phases/`.
- [ ] **Destructive Prompting:**
    - Develop "Destructive" prompt templates that reward the model for debunking claims.
- [ ] **Critique Mixin Update:**
    - Update `CritiqueMixin` to support `adversarial` mode behind a feature flag.

---

## Phase 4: Compute Scaling & Forensic Audit (Weeks 7-8)
**Goal:** Use more compute to resolve conflicts and scale reasoning.

- [ ] **ForensicSearchStage:**
    - Implement the `ForensicSearchStage` triggered when different models disagree on a key fact.
- [ ] **Inference-Time Scaling:**
    - Add support for multi-path sampling and majority voting in `LLMExecutor`.
- [ ] **Distribution-Aware Synthesis:**
    - Update `SynthesisStage` to handle distribution-aware merging (presenting variance instead of just the mean).

---

## Phase 5: UI & Epistemic UX (Weeks 9-10)
**Goal:** Transparently communicate certainty to the user.

- [ ] **Knowledge Map Component:**
    - Build a "Knowledge Map" UI component for the frontend (`ui-next/`).
- [ ] **Synthesis Card Update:**
    - Update `SynthesisCard` to display `VERIFIED`, `PROBABLE`, and `UNKNOWN` labels with clickable provenance links.
- [ ] **The "Unknown" Victory:**
    - Update the `Synthesis` system prompt to prioritize accurate ignorance over guessing.

---

## Success Metrics
1. **Hallucination Rate:** reduction in "False" claims on internal benchmarks.
2. **Provenance Coverage:** % of synthesized facts with valid source links.
3. **Epistemic Accuracy:** Correlation between `confidence` score and factual truth.
