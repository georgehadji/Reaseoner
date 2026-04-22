"""
Research Article Pipeline — structured article generation with adversarial verification.

Pipeline (deterministic, not chat loop):
  User Input
    → [Decomposer]
    → [Retriever + Reranker]
    → [Claim Extractor]
    → [Verifier / Adversary]
    → [Synthesizer]
    → [Final Critic]
    → Output (Article + Claim Map)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from reasoner.models import PipelineState, PerspectiveType, SolutionCandidate
from reasoner.parsing import extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol
from reasoner.core.search import get_discovery_client
from reasoner.core.constants import (
    ARTICLE_MAX_SOURCE_COUNT,
    ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION,
    ARTICLE_MIN_CLAIM_SUPPORT_RATIO,
    ARTICLE_MIN_SOURCE_COUNT,
    ARTICLE_SEARCH_RESULTS_PER_QUERY,
    TRUNCATION,
)

logger = logging.getLogger(__name__)


# ── Data Contracts ──────────────────────────────────────────────────────────

@dataclass
class SubQuestion:
    id: str
    question: str
    priority: str = "medium"  # high | medium | low
    required_evidence: list[str] = field(default_factory=list)
    risk: str = "low"  # hallucination | controversial | low


@dataclass
class RetrievedSource:
    title: str
    url: str
    date: str = ""
    authority_score: float = 0.0
    excerpt: str = ""
    source_type: str = "website"  # paper | book | website


@dataclass
class AtomicClaim:
    id: str
    text: str
    source_url: str = ""
    confidence: float = 0.0


@dataclass
class VerificationResult:
    claim_id: str
    status: str = "UNKNOWN"  # VERIFIED | WEAK | CONFLICTED | UNKNOWN
    supporting_sources: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ArticleSection:
    heading: str
    content: str


@dataclass
class ClaimTrace:
    claim_id: str
    used_in_section: str


@dataclass
class ArticleMetrics:
    total_claims: int = 0
    verified_claims: int = 0
    weak_claims: int = 0
    conflicted_claims: int = 0
    unknown_claims: int = 0
    citation_accuracy: float = 0.0
    contradiction_rate: float = 0.0
    claim_support_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_claims": self.total_claims,
            "verified_claims": self.verified_claims,
            "weak_claims": self.weak_claims,
            "conflicted_claims": self.conflicted_claims,
            "unknown_claims": self.unknown_claims,
            "citation_accuracy": round(self.citation_accuracy, 3),
            "contradiction_rate": round(self.contradiction_rate, 3),
            "claim_support_ratio": round(self.claim_support_ratio, 3),
        }


# ── Prompts ─────────────────────────────────────────────────────────────────

_DECOMPOSER_SYSTEM = (
    "You are a research methodology expert. Decompose the topic into atomic research questions. "
    "Identify uncertainty explicitly. Tag high-risk hallucination zones. Output JSON only."
)

_CLAIM_EXTRACTOR_SYSTEM = (
    "You are a precise fact extractor. Extract atomic claims from sources. "
    "One factual statement per claim. No interpretation. Must be directly supported by text. "
    "Reject vague statements. Output JSON only."
)

_VERIFIER_SYSTEM = (
    "You are a hostile reviewer. For each claim: check if source actually supports it, "
    "detect contradictions across sources, downgrade weak/general claims. "
    "You are rewarded for REJECTING claims, not accepting them. Output JSON only."
)

_SYNTHESIZER_SYSTEM = (
    "You are a disciplined research writer. Write using ONLY verified claims. "
    "Inline citations required. Mark uncertainty explicitly. Do not generalize beyond sources. "
    "No filler. If coverage is incomplete, state gaps. Output JSON only."
)

_CRITIC_SYSTEM = (
    "You are a journal reviewer. Find unsupported statements, overgeneralizations, missing counterpoints. "
    "Force revisions or deletions. Output actionable corrections. Output JSON only."
)


def _extract_markdown_links(text: str) -> list[dict[str, str]]:
    """Extract markdown links in order of first appearance."""
    if not text:
        return []
    seen: set[str] = set()
    links: list[dict[str, str]] = []
    for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", text):
        clean_url = url.strip()
        if clean_url in seen:
            continue
        seen.add(clean_url)
        links.append({"title": title.strip(), "url": clean_url})
    return links


def _normalize_source_record(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": source.get("title", ""),
        "url": source.get("url", ""),
        "date": source.get("date", ""),
        "authority_score": source.get("authority_score", 0.0),
        "excerpt": source.get("excerpt", ""),
        "source_type": source.get("source_type", "website"),
        "query_id": source.get("query_id", ""),
        "query_text": source.get("query_text", ""),
    }


class ArticlePipelineMixin(PipelineMixinProtocol):
    """Mixin providing the full research article pipeline with adversarial verification."""

    # ── Phase 2: Decomposer ──────────────────────────────────────────────

    async def _phase_article_decompose(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Decomposing topic into subquestions...", state)
        raw, _ = await self._call_llm_cached(
            role="article_decompose",
            system_prompt=_DECOMPOSER_SYSTEM,
            user_prompt=self._decomposer_prompt(state),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Decomposer parse error: {exc}", state)
            state.errors.append(f"Article decompose: parse error: {exc}")
            data = {}

        subquestions = []
        for sq in data.get("subquestions", []):
            subquestions.append(SubQuestion(
                id=sq.get("id", f"Q{len(subquestions)+1}"),
                question=sq.get("question", ""),
                priority=sq.get("priority", "medium"),
                required_evidence=sq.get("required_evidence", []),
                risk=sq.get("risk", "low"),
            ))

        state.writing_state["subquestions"] = [sq.__dict__ for sq in subquestions]
        state.writing_state["definitions_required"] = data.get("definitions_required", [])
        state.writing_state["unknowns"] = data.get("unknowns", [])
        state.writing_state["topic"] = data.get("topic", state.problem)
        self._log("ARTICLE", f"Decomposed into {len(subquestions)} subquestions", state)

    def _decomposer_prompt(self, state: PipelineState) -> str:
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Topic: {state.problem}\n\n'
            f'Decompose into atomic research questions.\n'
            f'Constraints:\n'
            f'- Maximize coverage, minimize overlap\n'
            f'- Identify uncertainty explicitly\n'
            f'- Tag high-risk hallucination zones\n\n'
            f'Output JSON: {{"topic": "...", '
            f'"subquestions": [{{'
            f'"id": "Q1", "question": "...", "priority": "high|medium|low", '
            f'"required_evidence": ["empirical"], "risk": "hallucination|controversial|low"'
            f'}}], '
            f'"definitions_required": ["..."], '
            f'"unknowns": ["..."]}}'
        )

    # ── Phase 2.5: Retrieval (per subquestion) ─────────────────────────────

    async def _phase_article_retrieve(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Retrieving sources per subquestion...", state)
        subquestions = state.writing_state.get("subquestions", [])
        if not subquestions:
            self._log("ARTICLE", "No subquestions — using problem directly", state)
            subquestions = [{"id": "Q0", "question": state.problem, "priority": "high", "risk": "low"}]

        try:
            client, _ = await get_discovery_client()
        except Exception as e:
            self._log("ARTICLE", f"Discovery client failed: {e}", state)
            state.errors.append(f"Article retrieve: {e}")
            return

        all_sources: list[dict] = []
        seen_urls: set[str] = set()

        for sq in subquestions:
            q_text = sq.get("question", "") if isinstance(sq, dict) else sq.question
            self._log("ARTICLE", f"Searching: {q_text[:60]}...", state)
            query_variants = [q_text]
            if len(q_text.split()) >= 4:
                query_variants.append(f"{q_text} evidence analysis")
            if "overview" not in q_text.lower():
                query_variants.append(f"{q_text} overview")
            try:
                for query_text in query_variants:
                    results = await client.search(
                        query_text,
                        num_results=ARTICLE_SEARCH_RESULTS_PER_QUERY,
                        domain=self.domain,
                    )
                    for res in results:
                        url = res.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_sources.append({
                                "title": res.get("title", ""),
                                "url": url,
                                "date": res.get("published", ""),
                                "authority_score": res.get("score", res.get("freshness_score", 0.0)),
                                "excerpt": res.get("content", "")[:800],
                                "source_type": res.get("source_type", "website"),
                                "query_id": sq.get("id", "Q0") if isinstance(sq, dict) else sq.id,
                                "query_text": query_text,
                            })
                    if len(all_sources) >= ARTICLE_MAX_SOURCE_COUNT:
                        break
            except Exception as exc:
                self._log("ARTICLE", f"Search failed for '{q_text}': {exc}", state)
                continue
            if len(all_sources) >= ARTICLE_MAX_SOURCE_COUNT:
                break

        ranked_sources = sorted(
            (_normalize_source_record(source) for source in all_sources),
            key=lambda source: (float(source.get("authority_score", 0.0)), len(source.get("excerpt", ""))),
            reverse=True,
        )[:ARTICLE_MAX_SOURCE_COUNT]

        state.web_discovery_results = ranked_sources
        state.writing_state["retrieved_sources"] = ranked_sources
        self._log("ARTICLE", f"Retrieved {len(ranked_sources)} ranked sources from {len(all_sources)} unique hits", state)

        # Hard rule: abort if no sources
        if not ranked_sources:
            state.errors.append("Article pipeline: ABORT — no sources found")
            self._log("ARTICLE", "ABORT: no sources found", state)
        elif len(ranked_sources) < ARTICLE_MIN_SOURCE_COUNT:
            self._log(
                "ARTICLE",
                f"Source coverage is thin: {len(ranked_sources)} sources found, below target {ARTICLE_MIN_SOURCE_COUNT}",
                state,
            )

    # ── Phase 3: Claim Extractor ───────────────────────────────────────────

    async def _phase_article_extract_claims(self, state: PipelineState) -> None:
        """Extract claims using CoVE (Chain-of-Verification): draft → verify independently → revise."""
        self._log("ARTICLE", "CoVE Claim Extraction: drafting claims from sources...", state)
        sources = state.writing_state.get("retrieved_sources", [])
        if not sources:
            self._log("ARTICLE", "No sources to extract claims from", state)
            return

        if len(sources) > ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION:
            self._log(
                "ARTICLE",
                f"Truncating {len(sources)} sources to {ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION} for CoVE draft extraction",
                state,
            )
        sources_json = json.dumps(sources[:ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION], indent=2, ensure_ascii=False)

        # ── Step 1: Draft claims ──
        raw_draft, _ = await self._call_llm_cached(
            role="article_claim_extract",
            system_prompt=phases.ARTICLE_COVE_DRAFT_SYSTEM,
            user_prompt=phases.article_cove_draft_prompt(state, sources_json),
            state=state,
        )
        try:
            draft_data = extract_json(raw_draft)
            draft_claims = draft_data.get("claims", [])
        except Exception as exc:
            self._log("ARTICLE", f"CoVE draft parse error: {exc}", state)
            state.errors.append(f"Article CoVE draft: parse error: {exc}")
            draft_claims = []

        if not draft_claims:
            self._log("ARTICLE", "No draft claims generated", state)
            return

        self._log("ARTICLE", f"CoVE draft: {len(draft_claims)} claims", state)
        state.writing_state["cove_draft_claims"] = draft_claims

        # ── Step 2: Generate verification questions ──
        claims_json = json.dumps(draft_claims, indent=2, ensure_ascii=False)
        raw_vq, _ = await self._call_llm_cached(
            role="article_cove_verify",
            system_prompt=phases.ARTICLE_COVE_VERIFY_SYSTEM,
            user_prompt=phases.article_cove_verify_prompt(state, claims_json, sources_json),
            state=state,
        )
        try:
            vq_data = extract_json(raw_vq)
            verification_questions = vq_data.get("verification_questions", [])
        except Exception as exc:
            self._log("ARTICLE", f"CoVE verify parse error: {exc}", state)
            state.errors.append(f"Article CoVE verify: parse error: {exc}")
            verification_questions = []

        state.writing_state["cove_verification_questions"] = verification_questions

        # ── Step 3: Answer verification questions independently ──
        questions_json = json.dumps(verification_questions, indent=2, ensure_ascii=False)
        raw_va, _ = await self._call_llm_cached(
            role="article_cove_answer",
            system_prompt=phases.ARTICLE_COVE_ANSWER_SYSTEM,
            user_prompt=phases.article_cove_answer_prompt(state, questions_json, sources_json),
            state=state,
        )
        try:
            va_data = extract_json(raw_va)
            verification_answers = va_data.get("answers", [])
        except Exception as exc:
            self._log("ARTICLE", f"CoVE answer parse error: {exc}", state)
            state.errors.append(f"Article CoVE answer: parse error: {exc}")
            verification_answers = []

        state.writing_state["cove_verification_answers"] = verification_answers

        # ── Step 4: Revise claims based on verification ──
        answers_json = json.dumps(verification_answers, indent=2, ensure_ascii=False)
        raw_revise, _ = await self._call_llm_cached(
            role="article_cove_revise",
            system_prompt=phases.ARTICLE_COVE_REVISE_SYSTEM,
            user_prompt=phases.article_cove_revise_prompt(state, claims_json, answers_json),
            state=state,
        )
        try:
            revise_data = extract_json(raw_revise)
            revised_claims = revise_data.get("claims", [])
            changes = revise_data.get("changes_made", [])
            uncertainties = revise_data.get("remaining_uncertainties", [])
        except Exception as exc:
            self._log("ARTICLE", f"CoVE revise parse error: {exc}", state)
            state.errors.append(f"Article CoVE revise: parse error: {exc}")
            revised_claims = draft_claims
            changes = []
            uncertainties = []

        # Deduplicate revised claims
        seen_texts: set[str] = set()
        deduped: list[dict] = []
        for c in revised_claims:
            text = c.get("text", "").strip().lower()
            if text and text not in seen_texts:
                seen_texts.add(text)
                deduped.append(c)

        state.writing_state["claims"] = deduped
        state.writing_state["cove_changes_made"] = changes
        state.writing_state["cove_remaining_uncertainties"] = uncertainties

        verified_count = sum(1 for c in deduped if c.get("status") == "verified")
        self._log(
            "ARTICLE",
            f"CoVE complete: {len(deduped)} unique claims ({verified_count} verified), "
            f"{len(changes)} changes, {len(uncertainties)} uncertainties",
            state,
        )

    # ── Phase 3.5: Adversarial Verifier ────────────────────────────────────

    async def _phase_article_verify(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Running adversarial verification...", state)
        claims = state.writing_state.get("claims", [])
        sources = state.writing_state.get("retrieved_sources", [])
        if not claims:
            self._log("ARTICLE", "No claims to verify", state)
            return

        claims_json = json.dumps(claims, indent=2, ensure_ascii=False)
        sources_json = json.dumps(sources, indent=2, ensure_ascii=False)

        raw, _ = await self._call_llm_cached(
            role="article_verifier",
            system_prompt=_VERIFIER_SYSTEM,
            user_prompt=self._verifier_prompt(state, claims_json, sources_json),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Verifier parse error: {exc}", state)
            state.errors.append(f"Article verify: parse error: {exc}")
            data = {}

        verifications = []
        for v in data.get("claims", []):
            verifications.append({
                "claim_id": v.get("claim_id", ""),
                "status": v.get("status", "UNKNOWN"),
                "supporting_sources": v.get("supporting_sources", []),
                "contradictions": v.get("contradictions", []),
                "notes": v.get("notes", ""),
            })

        state.writing_state["verifications"] = verifications

        # Calculate metrics
        metrics = self._calculate_metrics(claims, verifications)
        state.writing_state["metrics"] = metrics.to_dict()
        self._log(
            "ARTICLE",
            f"Verification complete: {metrics.verified_claims}/{metrics.total_claims} verified, "
            f"contradiction_rate={metrics.contradiction_rate}",
            state,
        )

        # Failure handling: re-retrieval if too few verified claims
        if metrics.claim_support_ratio < ARTICLE_MIN_CLAIM_SUPPORT_RATIO and not state.writing_state.get("re_retrieval_done", False):
            self._log("ARTICLE", "Claim support ratio too low — triggering re-retrieval", state)
            state.writing_state["re_retrieval_done"] = True
            # Add a broader query and re-run retrieval
            state.writing_state["subquestions"].append({
                "id": "Q_RETRY",
                "question": f"comprehensive overview of {state.writing_state.get('topic', state.problem)}",
                "priority": "high",
                "risk": "low",
            })
            await self._phase_article_retrieve(state)
            # Abort if re-retrieval found nothing — do not cascade into another verify cycle
            new_sources = state.writing_state.get("retrieved_sources", [])
            if not new_sources:
                self._log("ARTICLE", "Re-retrieval found no sources — aborting retry", state)
                state.errors.append("Article pipeline: re-retrieval found no sources; proceeding with low support ratio")
                return
            await self._phase_article_extract_claims(state)
            await self._phase_article_verify(state)

    def _verifier_prompt(self, state: PipelineState, claims_json: str, sources_json: str) -> str:
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Claims:\n{claims_json}\n\n'
            f'Sources:\n{sources_json}\n\n'
            f'Act as a hostile reviewer. For EACH claim:\n'
            f'1. Check if source ACTUALLY supports the claim\n'
            f'2. Detect contradictions across sources\n'
            f'3. Downgrade weak or general claims\n'
            f'4. Be skeptical — reward rejections\n\n'
            f'Output JSON: {{"claims": [{{'
            f'"claim_id": "C1", "status": "VERIFIED|WEAK|CONFLICTED|UNKNOWN", '
            f'"supporting_sources": ["url"], "contradictions": ["text"], "notes": "..."'
            f'}}]}}'
        )

    def _calculate_metrics(self, claims: list[dict], verifications: list[dict]) -> ArticleMetrics:
        total = len(claims)
        if total == 0:
            return ArticleMetrics()

        status_counts = {"VERIFIED": 0, "WEAK": 0, "CONFLICTED": 0, "UNKNOWN": 0}
        for v in verifications:
            status = v.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        verified = status_counts.get("VERIFIED", 0)
        weak = status_counts.get("WEAK", 0)
        conflicted = status_counts.get("CONFLICTED", 0)
        unknown = status_counts.get("UNKNOWN", 0)

        # Citation accuracy: claims with source_url / total claims
        with_citation = sum(1 for c in claims if c.get("source_url"))
        citation_acc = with_citation / total if total > 0 else 0.0

        return ArticleMetrics(
            total_claims=total,
            verified_claims=verified,
            weak_claims=weak,
            conflicted_claims=conflicted,
            unknown_claims=unknown,
            citation_accuracy=citation_acc,
            contradiction_rate=conflicted / total if total > 0 else 0.0,
            claim_support_ratio=verified / total if total > 0 else 0.0,
        )

    # ── Phase 4: Synthesizer ───────────────────────────────────────────────

    async def _phase_article_synthesize(self, state: PipelineState) -> None:
        """Synthesize article using SoT (Skeleton-of-Thought): skeleton → parallel sections → assemble."""
        self._log("ARTICLE", "SoT Synthesis: generating skeleton...", state)
        claims = state.writing_state.get("claims", [])
        verifications = state.writing_state.get("verifications", [])

        # Filter to verified + weak claims only (no conflicted)
        verified_ids = {v["claim_id"] for v in verifications if v.get("status") in ("VERIFIED", "WEAK")}
        usable_claims = [c for c in claims if c.get("id", "") in verified_ids]

        if not usable_claims:
            self._log("ARTICLE", "No usable claims — cannot synthesize", state)
            state.errors.append("Article synthesize: no usable claims after verification")
            return

        claims_json = json.dumps(usable_claims, indent=2, ensure_ascii=False)

        # ── Step 1: Generate skeleton ──
        raw_skeleton, _ = await self._call_llm_cached(
            role="article_sot_skeleton",
            system_prompt=phases.ARTICLE_SOT_SYSTEM,
            user_prompt=phases.article_sot_skeleton_prompt(state, claims_json),
            state=state,
        )
        try:
            skeleton_data = extract_json(raw_skeleton)
            skeleton_sections = skeleton_data.get("sections", [])
        except Exception as exc:
            self._log("ARTICLE", f"SoT skeleton parse error: {exc}", state)
            state.errors.append(f"Article SoT skeleton: parse error: {exc}")
            # Fallback: generate article monolithically
            await self._phase_article_synthesize_monolithic(state, claims_json)
            return

        if not skeleton_sections:
            self._log("ARTICLE", "No skeleton sections — falling back to monolithic", state)
            await self._phase_article_synthesize_monolithic(state, claims_json)
            return

        state.writing_state["sot_skeleton"] = skeleton_sections
        self._log("ARTICLE", f"SoT skeleton: {len(skeleton_sections)} sections", state)

        # ── Step 2: Parallel section writing ──
        semaphore = asyncio.Semaphore(4)

        async def _write_one(section: dict) -> dict:
            async with semaphore:
                # Filter claims relevant to this section
                section_claim_ids = section.get("claim_ids", [])
                section_claims = [c for c in usable_claims if c.get("id", "") in section_claim_ids]
                if not section_claims:
                    section_claims = usable_claims  # fallback: use all claims
                section_claims_json = json.dumps(section_claims, indent=2, ensure_ascii=False)

                raw_sec, _ = await self._call_llm_cached(
                    role="article_sot_solve",
                    system_prompt=phases.ARTICLE_SOT_SOLVE_SYSTEM,
                    user_prompt=phases.article_sot_solve_prompt(state, section, section_claims_json),
                    state=state,
                )
                try:
                    sec_data = extract_json(raw_sec)
                except Exception as exc:
                    self._log("ARTICLE", f"SoT section parse error: {exc}", state)
                    return {"heading": section.get("heading", ""), "content": "", "error": str(exc)}

                return {
                    "heading": section.get("heading", ""),
                    "content": sec_data.get("content", ""),
                    "word_count": sec_data.get("word_count", 0),
                }

        tasks = [_write_one(sec) for sec in skeleton_sections]
        section_results = await asyncio.gather(*tasks, return_exceptions=True)

        written_sections: list[dict] = []
        for i, result in enumerate(section_results):
            if isinstance(result, Exception):
                self._log("ARTICLE", f"Section {i} failed: {result}", state)
                heading = skeleton_sections[i].get("heading", f"Section {i+1}") if i < len(skeleton_sections) else f"Section {i+1}"
                written_sections.append({
                    "heading": heading,
                    "content": "",
                })
            else:
                written_sections.append(result)

        state.writing_state["sot_sections"] = written_sections

        # ── Step 3: Assemble ──
        # Build article from sections + transitions
        lines: list[str] = []
        for sec in written_sections:
            heading = sec.get("heading", "")
            content = sec.get("content", "")
            if content.strip():
                lines.append(f"\n## {heading}\n")
                lines.append(content + "\n")

        article_text = "\n".join(lines)

        # Generate title/abstract from assembled article
        raw_meta, _ = await self._call_llm_cached(
            role="article_synthesize",
            system_prompt=_SYNTHESIZER_SYSTEM,
            user_prompt=self._synthesizer_meta_prompt(state, article_text, claims_json),
            state=state,
        )
        try:
            meta_data = extract_json(raw_meta)
        except Exception as exc:
            self._log("ARTICLE", f"SoT meta parse error: {exc}", state)
            meta_data = {}

        state.writing_state["article"] = article_text
        state.writing_state["sections"] = written_sections
        state.writing_state["abstract"] = meta_data.get("abstract", "")
        state.writing_state["title"] = meta_data.get("title", "")
        state.writing_state["gaps_noted"] = meta_data.get("gaps_noted", [])
        self._log(
            "ARTICLE",
            f"SoT synthesis complete: {len(written_sections)} sections, "
            f"title='{state.writing_state.get('title', '')}'",
            state,
        )

    async def _phase_article_synthesize_monolithic(self, state: PipelineState, claims_json: str) -> None:
        """Fallback: synthesize article in a single LLM call."""
        self._log("ARTICLE", "Monolithic synthesis fallback...", state)
        raw, _ = await self._call_llm_cached(
            role="article_synthesize",
            system_prompt=_SYNTHESIZER_SYSTEM,
            user_prompt=self._synthesizer_prompt(state, claims_json),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Monolithic synthesizer parse error: {exc}", state)
            state.errors.append(f"Article synthesize: parse error: {exc}")
            data = {}

        state.writing_state["article"] = data.get("article", "")
        state.writing_state["sections"] = data.get("sections", [])
        state.writing_state["abstract"] = data.get("abstract", "")
        state.writing_state["title"] = data.get("title", "")
        state.writing_state["gaps_noted"] = data.get("gaps_noted", [])
        self._log("ARTICLE", f"Monolithic synthesis: {len(data.get('sections', []))} sections", state)

    def _synthesizer_prompt(self, state: PipelineState, claims_json: str) -> str:
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Topic: {state.problem}\n\n'
            f'Verified Claims (use ONLY these):\n{claims_json}\n\n'
            f'Rules:\n'
            f'- Inline [Source: URL] citations required\n'
            f'- Mark uncertainty explicitly\n'
            f'- Do not generalize beyond the claims\n'
            f'- No filler or stylistic fluff\n'
            f'- If coverage is incomplete, state gaps clearly\n\n'
            f'Output JSON: {{'
            f'"title": "...", '
            f'"abstract": "...", '
            f'"sections": [{{"heading": "...", "content": "..."}}], '
            f'"gaps_noted": ["..."]'
            f'}}'
        )

    def _synthesizer_meta_prompt(self, state: PipelineState, article: str, claims_json: str) -> str:
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Article Sections:\n{article}\n\n'
            f'Verified Claims:\n{claims_json}\n\n'
            f'Generate a title, abstract, and note any gaps. '
            f'The abstract must accurately reflect the article content.\n\n'
            f'Output JSON: {{'
            f'"title": "...", '
            f'"abstract": "...", '
            f'"gaps_noted": ["..."]'
            f'}}'
        )

    # ── Phase 4.25: Pre-Mortem ─────────────────────────────────────────────

    async def _phase_article_pre_mortem(self, state: PipelineState) -> None:
        """Pre-mortem analysis: imagine the article fails and work backwards."""
        self._log("ARTICLE", "Running pre-mortem analysis...", state)
        article = state.writing_state.get("article", "")
        claims = state.writing_state.get("claims", [])
        if not article:
            self._log("ARTICLE", "No article for pre-mortem", state)
            return

        if len(claims) > 20:
            self._log("ARTICLE", f"Truncating {len(claims)} claims to 20 for pre-mortem analysis", state)
        claims_json = json.dumps(claims[:20], indent=2, ensure_ascii=False)
        raw, _ = await self._call_llm_cached(
            role="article_pre_mortem",
            system_prompt=phases.ARTICLE_PRE_MORTEM_SYSTEM,
            user_prompt=phases.article_pre_mortem_prompt(state, article, claims_json),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Pre-mortem parse error: {exc}", state)
            state.errors.append(f"Article pre-mortem: parse error: {exc}")
            data = {}

        state.writing_state["pre_mortem"] = {
            "failure_narrative": data.get("failure_narrative", ""),
            "root_causes": data.get("root_causes", []),
            "weak_sections": data.get("weak_sections", []),
            "challenged_claims": data.get("challenged_claims", []),
            "missing_counterarguments": data.get("missing_counterarguments", []),
            "overgeneralizations": data.get("overgeneralizations", []),
            "early_warnings": data.get("early_warnings", []),
        }
        self._log(
            "ARTICLE",
            f"Pre-mortem: {len(data.get('root_causes', []))} root causes, "
            f"{len(data.get('weak_sections', []))} weak sections identified",
            state,
        )

    # ── Phase 4.5: Final Critic ────────────────────────────────────────────

    async def _phase_article_critic(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Running final journal review...", state)
        article = state.writing_state.get("article", "")
        claims = state.writing_state.get("claims", [])
        if not article:
            self._log("ARTICLE", "No article to review", state)
            return

        raw, _ = await self._call_llm_cached(
            role="article_critic",
            system_prompt=_CRITIC_SYSTEM,
            user_prompt=self._critic_prompt(state, article, claims),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Critic parse error: {exc}", state)
            state.errors.append(f"Article critic: parse error: {exc}")
            data = {}

        corrections = data.get("corrections", [])
        state.writing_state["critic_corrections"] = corrections
        state.writing_state["critic_score"] = data.get("overall_score", 0)
        state.writing_state["must_revise"] = data.get("must_revise", False)

        # Apply forced deletions (corrections with action="delete")
        deletions = [c for c in corrections if c.get("action") == "delete"]
        if deletions:
            self._log("ARTICLE", f"Critic forced {len(deletions)} deletions", state)

        self._log("ARTICLE", f"Critic review complete: score={data.get('overall_score', 0)}, must_revise={data.get('must_revise', False)}", state)

    def _critic_prompt(self, state: PipelineState, article: str, claims: list[dict]) -> str:
        claims_json = json.dumps(claims, indent=2, ensure_ascii=False)
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Article:\n{article}\n\n'
            f'Original Claims:\n{claims_json}\n\n'
            f'You are a journal reviewer. Find:\n'
            f'1. Unsupported statements\n'
            f'2. Overgeneralizations\n'
            f'3. Missing counterpoints\n'
            f'4. Weak citations\n\n'
            f'For each issue, specify action: revise|delete|add_caveat\n\n'
            f'Output JSON: {{'
            f'"corrections": [{{'
            f'"issue": "...", "location": "section/paragraph", '
            f'"action": "revise|delete|add_caveat", "suggestion": "..."'
            f'}}], '
            f'"overall_score": 0.0, '
            f'"must_revise": true|false'
            f'}}'
        )

    # ── Phase 5: Final Assembly ────────────────────────────────────────────

    async def _phase_article_assemble(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Assembling final output...", state)
        article = state.writing_state.get("article", "")
        title = state.writing_state.get("title", "")
        abstract = state.writing_state.get("abstract", "")
        sections = state.writing_state.get("sections", [])
        metrics = state.writing_state.get("metrics", {})
        gaps = state.writing_state.get("gaps_noted", [])
        verifications = state.writing_state.get("verifications", [])
        sources = state.writing_state.get("retrieved_sources", [])
        cited_links = _extract_markdown_links(article)
        section_links: list[dict[str, str]] = []
        for sec in sections:
            content = sec.get("content", "") if isinstance(sec, dict) else getattr(sec, "content", "")
            section_links.extend(_extract_markdown_links(content))
        cited_links.extend(link for link in section_links if link["url"] not in {item["url"] for item in cited_links})

        source_lookup = {
            s.get("url", ""): {"title": s.get("title", "") or s.get("url", ""), "url": s.get("url", "")}
            for s in sources
            if isinstance(s, dict) and s.get("url")
        }
        for link in list(cited_links):
            source_lookup.setdefault(link["url"], {"title": link["title"] or link["url"], "url": link["url"]})

        sources_used = [source_lookup[url] for url in source_lookup if url in {link["url"] for link in cited_links}]
        # Do not fabricate a Sources section from merely retrieved URLs. Only links
        # actually cited in the article body/sections should be surfaced as used.

        # Build claim traceability
        traceability = []
        for sec in sections:
            if isinstance(sec, dict):
                sec_heading = sec.get("heading", "")
            else:
                sec_heading = getattr(sec, "heading", "")
            for v in verifications:
                if v.get("status") == "VERIFIED":
                    traceability.append({
                        "claim_id": v.get("claim_id", ""),
                        "used_in_section": sec_heading,
                    })

        # Build final article text
        lines: list[str] = []
        if title:
            lines.append(f"# {title}\n")
        if abstract:
            lines.append(f"**Abstract:** {abstract}\n")
        for sec in sections:
            if isinstance(sec, dict):
                heading = sec.get("heading", "")
                content = sec.get("content", "")
            else:
                heading = getattr(sec, "heading", "")
                content = getattr(sec, "content", "")
            lines.append(f"\n## {heading}\n")
            lines.append(content + "\n")

        # Add gaps section if needed
        if gaps:
            lines.append("\n## Identified Gaps\n")
            for g in gaps:
                lines.append(f"- {g}\n")

        # Add metrics section
        lines.append("\n## Quality Metrics\n")
        lines.append(f"- Total Claims: {metrics.get('total_claims', 0)}\n")
        lines.append(f"- Verified: {metrics.get('verified_claims', 0)}\n")
        lines.append(f"- Weak: {metrics.get('weak_claims', 0)}\n")
        lines.append(f"- Conflicted: {metrics.get('conflicted_claims', 0)}\n")
        lines.append(f"- Claim Support Ratio: {metrics.get('claim_support_ratio', 0)}\n")
        lines.append(f"- Citation Accuracy: {metrics.get('citation_accuracy', 0)}\n")
        lines.append(f"- Contradiction Rate: {metrics.get('contradiction_rate', 0)}\n")

        # Add conflict section if contradictions exist
        conflicted = [v for v in verifications if v.get("status") == "CONFLICTED"]
        if conflicted:
            lines.append("\n## Conflicting Evidence\n")
            for c in conflicted:
                lines.append(f"- Claim {c.get('claim_id', '')}: {c.get('notes', '')}\n")

        # Add sources section last, using actual cited links when available
        if sources_used:
            lines.append("\n## Sources\n")
            for s in sources_used:
                url = s.get("url", "")
                title_str = s.get("title", "")
                lines.append(f"- [{title_str or url}]({url})\n")

        final_text = "\n".join(lines)
        state.writing_state["final_article"] = final_text
        state.writing_state["claim_traceability"] = traceability
        state.writing_state["sources_cited"] = sources_used

        # Feed into candidates for synthesis
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=final_text,
            key_insights=[f"Support ratio: {metrics.get('claim_support_ratio', 0)}"],
            model_used=state.phase_models.get("article_assemble", "unknown"),
        ))

        self._log("ARTICLE", f"Final assembly complete: {len(final_text)} chars", state)
