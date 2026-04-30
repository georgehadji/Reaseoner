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
from reasoner.phases._shared import HUMANIZATION_RULES
from reasoner.sanitization import clean_llm_artifacts
from reasoner.application.mixins._protocol import PipelineMixinProtocol
from reasoner.core.search import get_search_client
from reasoner.core.constants import (
    ARTICLE_MAX_SOURCE_COUNT,
    ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION,
    ARTICLE_MIN_CLAIM_SUPPORT_RATIO,
    ARTICLE_MIN_SOURCE_COUNT,
    ARTICLE_SEARCH_RESULTS_PER_QUERY,
    TRUNCATION,
)

logger = logging.getLogger(__name__)

_WRITING_INDICATORS = [
    # English
    r"\b(write|draft|compose|author|create)\b.*\b(article|essay|blog|report|paper|explainer)\b",
    r"\barticle\b.*\b(about|on)\b",
    # Greek (γράψε=write, άρθρο=article, έκθεση=essay, κείμενο=text)
    r"\b(γράψε|γράψτε|συντάξε|συντάξτε|δημιούργησε|δημιουργήστε)\b.*\b(άρθρο|έκθεση|αναφορά|κείμενο|paper)\b",
    r"\b(άρθρο|έκθεση)\b.*\b(για|σχετικά\s+με|πάνω\s+σε)\b",
    # Spanish (escribe=write, artículo=article, ensayo=essay)
    r"\b(escribe|escribir|redacta|redactar|crea|crear)\b.*\b(artículo|ensayo|blog|reporte|paper)\b",
    # French (écris=write, article=article, essai=essay)
    r"\b(écris|écrire|rédige|rédiger|rédigez|rédiges|crée|créer)\b.*\b(article|essai|blog|rapport|paper)\b",
]

_PAPER_INDICATORS = [
    r"\b(write|draft|compose|create|prepare)\b.*\b(paper|thesis|dissertation|academic\s+report)\b",
    r"\b(academic\s+paper|research\s+paper|term\s+paper|scientific\s+paper)\b",
    # Greek patterns
    r"\b(πτυχιακ[ήη]|διπλωματικ[ήη]|ακαδημαϊκ[ήη]\s+εργασ[ίι]α|επιστημονικ[ήη]\s+εργασ[ίι]α)\b",
    r"\b(ερευνητικ[ήη]\s+εργασ[ίι]α|γράψ[εε]\b.*\bεργασ[ίι]α)\b",
]

_THESIS_INDICATORS = [
    r"\b(thesis|dissertation|phd|master.{0,3}s\s+thesis)\b",
    # Greek patterns
    r"\b(πτυχιακ[ήη]\s+εργασ[ίι]α|διπλωματικ[ήη]\s+εργασ[ίι]α|διδακτορικ[ήη]|μεταπτυχιακ[ήη])\b",
]

_REFERENTIAL_SIGNALS = ["continue", "expand", "revise that", "elaborate", "add more"]


def detect_document_type(problem: str) -> str:
    """Classify writing request: 'article' | 'paper' | 'thesis'."""
    lower = problem.lower()
    if any(re.search(p, lower) for p in _THESIS_INDICATORS):
        return "thesis"
    if any(re.search(p, lower) for p in _PAPER_INDICATORS):
        return "paper"
    return "article"


def is_article_request(problem: str) -> bool:
    """Detect if the user is asking for a structured written piece."""
    lower = problem.lower()
    return any(re.search(p, lower) for p in _WRITING_INDICATORS + _PAPER_INDICATORS + _THESIS_INDICATORS)


def is_referential_followup(problem: str, history: list) -> bool:
    """Detect if a follow-up message refers to prior context."""
    if not history:
        return False
    lower = problem.lower()
    return any(sig in lower for sig in _REFERENTIAL_SIGNALS)


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
    + HUMANIZATION_RULES
)

_CRITIC_SYSTEM = (
    "You are a journal reviewer. Find unsupported statements, overgeneralizations, missing counterpoints. "
    "Force revisions or deletions. Output actionable corrections. Output JSON only."
)

_REVISER_SYSTEM = (
    "You are an expert editor. You receive an article draft and a list of corrections from a reviewer. "
    "Apply every correction faithfully: revise flagged sentences, delete hallucinated claims, and add missing "
    "caveats. Preserve the author's voice and structure. Output ONLY the revised article text, no JSON wrapper."
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
        doc_type = detect_document_type(state.problem)
        state.writing_state["document_type"] = doc_type
        self._log("ARTICLE", f"Document type detected: {doc_type}", state)
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
        raw_sqs = data.get("subquestions", [])
        if not isinstance(raw_sqs, list):
            raw_sqs = []

        for sq in raw_sqs:
            if not isinstance(sq, dict):
                continue
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

        # Detect whether the topic requires entity-specific data (financials, metrics, team, etc.)
        # that may not be publicly available — flag to constrain downstream verdicts
        entity_signals = [
            r"\b(startup|company|firm|fund|investment\s+case|invest\s+in|should\s+(we|i)\s+invest)\b",
            r"\b(revenue|valuation|runway|burn\s+rate|cap\s+table|financials|arr|mrr|ebitda)\b",
            r"\b(team|founder|cto|ceo|headcount|employees)\b",
            r"\b(Series\s+[A-D]|seed\s+round|pre-seed|vc\s+fund)\b",
        ]
        problem_lower = state.problem.lower()
        needs_entity_data = any(re.search(p, problem_lower) for p in entity_signals)
        state.writing_state["needs_entity_data"] = needs_entity_data
        if needs_entity_data:
            self._log("ARTICLE", "Entity-specific data required — synthesis will block unsupported verdicts", state)

    def _decomposer_prompt(self, state: PipelineState) -> str:
        doc_type = state.writing_state.get("document_type", "article")
        if doc_type in ("paper", "thesis"):
            structure_hint = (
                f'This is an academic {doc_type}. Decompose into research questions that map to:\n'
                f'Introduction → Literature Review → Methodology → Results → Discussion → Conclusion\n'
                f'Identify theoretical gaps, methodological considerations, and empirical evidence requirements.\n'
            )
        else:
            structure_hint = (
                f'Maximize coverage, minimize overlap\n'
                f'Identify uncertainty explicitly\n'
                f'Tag high-risk hallucination zones\n'
            )
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Topic: {state.problem}\n'
            f'Document type: {doc_type}\n\n'
            f'Decompose into atomic research questions.\n'
            f'Constraints:\n'
            f'- {structure_hint}'
            f'\nOutput JSON: {{"topic": "...", '
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
            client, _ = await get_search_client()
        except Exception as e:
            self._log("ARTICLE", f"Search client failed: {e}", state)
            state.errors.append(f"Article retrieve: {e}")
            return

        import asyncio as _asyncio

        lang = (getattr(state, "detected_language", None) or "en").lower()

        def _build_variants(sq) -> list[tuple[str, str]]:
            """Return (query_text, query_id) pairs for a subquestion."""
            q_text = sq.get("question", "") if isinstance(sq, dict) else sq.question
            q_id = sq.get("id", "Q0") if isinstance(sq, dict) else sq.id
            variants = [q_text]
            if lang.startswith("en"):
                if len(q_text.split()) >= 4:
                    variants.append(f"{q_text} evidence analysis")
                if "overview" not in q_text.lower():
                    variants.append(f"{q_text} overview")
            return [(v, q_id) for v in variants]

        all_queries: list[tuple[str, str]] = []
        for sq in subquestions:
            all_queries.extend(_build_variants(sq))

        async def _search_one(query_text: str, query_id: str) -> list[dict]:
            try:
                results = await client.search(
                    query_text,
                    num_results=ARTICLE_SEARCH_RESULTS_PER_QUERY,
                    domain=self.domain,
                )
                return [
                    {
                        "title": res.get("title", ""),
                        "url": res.get("url", ""),
                        "date": res.get("published", ""),
                        "authority_score": res.get("score", res.get("freshness_score", 0.0)),
                        "excerpt": res.get("content", "")[:800],
                        "source_type": res.get("source_type", "website"),
                        "query_id": query_id,
                        "query_text": query_text,
                    }
                    for res in results
                    if res.get("url")
                ]
            except Exception as exc:
                self._log("ARTICLE", f"Search failed for '{query_text[:60]}': {exc}", state)
                return []

        self._log("ARTICLE", f"Running {len(all_queries)} queries in parallel...", state)
        batch_results = await _asyncio.gather(*[_search_one(qt, qid) for qt, qid in all_queries])

        all_sources: list[dict] = []
        seen_urls: set[str] = set()
        for batch in batch_results:
            for item in batch:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(item)
                if len(all_sources) >= ARTICLE_MAX_SOURCE_COUNT:
                    break
            if len(all_sources) >= ARTICLE_MAX_SOURCE_COUNT:
                break

        ranked_sources = sorted(
            (_normalize_source_record(source) for source in all_sources),
            key=lambda source: (float(source.get("authority_score", 0.0)), len(source.get("excerpt", ""))),
            reverse=True,
        )[:ARTICLE_MAX_SOURCE_COUNT]

        self._log("ARTICLE", f"Initial retrieval: {len(ranked_sources)} ranked sources from {len(all_sources)} unique hits", state)

        # Fallback: if no sources from subquestions, try a broad search with the original problem
        if not ranked_sources:
            self._log("ARTICLE", "No sources from subquestions — trying broad fallback search...", state)
            try:
                fallback_results = await client.search(
                    state.problem,
                    num_results=ARTICLE_SEARCH_RESULTS_PER_QUERY * 2,
                    domain=self.domain,
                )
                for res in fallback_results:
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
                            "query_id": "FALLBACK",
                            "query_text": state.problem,
                        })
                ranked_sources = sorted(
                    (_normalize_source_record(source) for source in all_sources),
                    key=lambda source: (float(source.get("authority_score", 0.0)), len(source.get("excerpt", ""))),
                    reverse=True,
                )[:ARTICLE_MAX_SOURCE_COUNT]
            except Exception as exc:
                self._log("ARTICLE", f"Fallback search failed: {exc}", state)

        state.web_discovery_results = ranked_sources
        state.writing_state["retrieved_sources"] = ranked_sources
        self._log("ARTICLE", f"Retrieved {len(ranked_sources)} ranked sources from {len(all_sources)} unique hits", state)

        if not ranked_sources and state.vetted_context:
            self._log("ARTICLE", "No sources from search — using Phase 3 vetted context as fallback", state)
            fallback = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "date": r.get("date", r.get("published", "")),
                    "authority_score": r.get("freshness_score", 0.5),
                    "excerpt": (r.get("snippet") or r.get("content", ""))[:800],
                    "source_type": "website",
                    "query_id": "VETTED_FALLBACK",
                    "query_text": state.problem,
                }
                for r in state.vetted_context
                if r.get("url")
            ]
            ranked_sources = fallback[:ARTICLE_MAX_SOURCE_COUNT]
            state.web_discovery_results = ranked_sources
            state.writing_state["retrieved_sources"] = ranked_sources
            self._log("ARTICLE", f"Vetted context fallback: {len(ranked_sources)} sources available", state)

        if not ranked_sources:
            self._log("ARTICLE", "No sources found — falling back to knowledge-only synthesis", state)
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
            state.pending_events.append({"type": "phase_warning", "message": "Skipped: no sources available from Phase 6 (Retrieve Sources)."})
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
            self._log("ARTICLE", f"CoVE draft parse error (fallback v2): {exc}", state)
            draft_claims = self._extract_cove_array_fallback(raw_draft, "claims")
            if not draft_claims:
                state.errors.append(f"Article CoVE draft: parse error (fallback v2): {exc}")

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
            verification_questions = self._extract_cove_array_fallback(raw_vq, "verification_questions")
            if not verification_questions:
                state.errors.append(f"Article CoVE verify: parse error: {exc}")

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
            verification_answers = self._extract_cove_array_fallback(raw_va, "answers")
            if not verification_answers:
                state.errors.append(f"Article CoVE answer: parse error: {exc}")

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
            revised_claims = self._extract_cove_array_fallback(raw_revise, "claims")
            changes = self._extract_cove_array_fallback(raw_revise, "changes_made")
            uncertainties = self._extract_cove_array_fallback(raw_revise, "remaining_uncertainties")
            if not revised_claims:
                state.errors.append(f"Article CoVE revise: parse error: {exc}")
                revised_claims = draft_claims
            if not changes:
                changes = []
            if not uncertainties:
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
            state.pending_events.append({"type": "phase_warning", "message": "Skipped: no claims extracted from Phase 7 (Extract Claims)."})
            return

        claims_json = json.dumps(claims, indent=2, ensure_ascii=False)
        
        # Truncate URLs in sources for the prompt to prevent token limit issues with massive percent-encoded strings
        sources_for_prompt = []
        for s in sources:
            s_copy = s.copy()
            url = s_copy.get("url", "")
            if len(url) > 150:
                s_copy["url"] = url[:150] + "..."
            sources_for_prompt.append(s_copy)
        
        sources_json = json.dumps(sources_for_prompt, indent=2, ensure_ascii=False)

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
            f'1. Check if the claim\'s own source ACTUALLY supports the claim (not just mentions the topic)\n'
            f'2. Cross-source check: identify numerical values (percentages, market sizes, growth rates, dates) '
            f'that appear in MULTIPLE sources — flag any where different sources report conflicting numbers for the same metric\n'
            f'3. Downgrade claims citing only general/market-overview sources when entity-specific data is needed\n'
            f'4. Mark as CONFLICTED if any two sources give inconsistent figures for the same statistic\n'
            f'5. Be skeptical — reward rejections over false acceptances\n\n'
            f'Output JSON: {{"claims": [{{'
            f'"claim_id": "C1", "status": "VERIFIED|WEAK|CONFLICTED|UNKNOWN", '
            f'"supporting_sources": ["url"], "contradictions": ["description of conflict between sources"], "notes": "..."'
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
            self._log("ARTICLE", "No usable claims — falling back to knowledge-only synthesis", state)
            if not state.writing_state.get("retrieved_sources"):
                state.pending_events.append({
                    "type": "phase_warning",
                    "message": "No sources or verified claims available. Output will rely on model knowledge only — treat as unverified.",
                })
            await self._phase_article_synthesize_monolithic(state, "[]")
            return

        claims_json = json.dumps(usable_claims, indent=2, ensure_ascii=False)

        # ── Step 1: Generate skeleton ──
        doc_type = state.writing_state.get("document_type", "article")
        is_academic = doc_type in ("paper", "thesis")
        raw_skeleton, _ = await self._call_llm_cached(
            role="article_sot_skeleton",
            system_prompt=phases.ACADEMIC_SOT_SYSTEM if is_academic else phases.ARTICLE_SOT_SYSTEM,
            user_prompt=(
                phases.academic_sot_skeleton_prompt(state, claims_json)
                if is_academic
                else phases.article_sot_skeleton_prompt(state, claims_json)
            ),
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
                    system_prompt=(
                        phases.ACADEMIC_SOT_SOLVE_SYSTEM if is_academic else phases.ARTICLE_SOT_SOLVE_SYSTEM
                    ),
                    user_prompt=(
                        phases.academic_sot_solve_prompt(state, section, section_claims_json)
                        if is_academic
                        else phases.article_sot_solve_prompt(state, section, section_claims_json)
                    ),
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
        has_claims = claims_json.strip() not in ("[]", "", "null")
        needs_entity_data = state.writing_state.get("needs_entity_data", False)
        if has_claims:
            evidence_section = (
                f'Verified Claims (use ONLY these):\n{claims_json}\n\n'
                f'Rules:\n'
                f'- Inline [Source: URL] citations required\n'
                f'- Mark uncertainty explicitly\n'
                f'- Do not generalize beyond the claims\n'
                f'- No filler or stylistic fluff\n'
                f'- If coverage is incomplete, state gaps clearly\n\n'
            )
        else:
            evidence_section = (
                f'No external sources were retrieved. Write from expert knowledge.\n\n'
                f'Rules:\n'
                f'- Do not fabricate citations or URLs\n'
                f'- Mark claims that would benefit from empirical support with (unverified)\n'
                f'- Write with authority but epistemic honesty\n'
                f'- Note in gaps_noted that no sources were available\n\n'
            )
        entity_constraint = ""
        if needs_entity_data:
            entity_constraint = (
                f'CRITICAL DATA CONSTRAINT: This topic requires entity-specific data '
                f'(financials, team, metrics, cap table, runway, etc.). '
                f'If verified claims do not include direct data from the specific entity, '
                f'you MUST NOT issue a specific investment recommendation, verdict, or rating. '
                f'Instead, state explicitly what data is missing and why a verdict cannot be made responsibly. '
                f'Use language like "insufficient entity-specific data to assess" rather than filling gaps with inference.\n\n'
            )
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Topic: {state.problem}\n\n'
            f'{entity_constraint}'
            f'{evidence_section}'
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
            state.pending_events.append({"type": "phase_warning", "message": "Skipped: no article draft available from Phase 9 (Synthesize)."})
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
        # Defensive: strip markdown fences locally in case parsing.py is cached old
        raw_clean = raw.strip()
        if raw_clean.startswith("```json"):
            raw_clean = raw_clean[7:].lstrip()
        elif raw_clean.startswith("```"):
            raw_clean = raw_clean[3:].lstrip()
        if raw_clean.rstrip().endswith("```"):
            raw_clean = raw_clean.rstrip()[:-3].rstrip()

        try:
            data = extract_json(raw_clean)
        except Exception as exc:
            self._log("ARTICLE", f"Pre-mortem parse error: {exc}", state)
            # Fallback: try to extract fields with regex so we don't lose everything
            data = self._extract_pre_mortem_fallback(raw_clean)
            # Only record a hard error if the fallback also comes up empty
            if not data or not any(v for v in data.values() if v):
                state.errors.append(f"Article pre-mortem: parse error: {exc}")

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

        # Build correction list from pre-mortem findings and apply them
        pm_corrections = []
        for claim in data.get("challenged_claims", []):
            pm_corrections.append({"issue": claim, "action": "add_caveat", "suggestion": f"Add uncertainty caveat: {claim}"})
        for og in data.get("overgeneralizations", []):
            pm_corrections.append({"issue": og, "action": "revise", "suggestion": f"Narrow claim: {og}"})
        if pm_corrections:
            await self._apply_corrections_to_article(state, pm_corrections, source="pre_mortem")

    # ── Phase 4.5: Final Critic ────────────────────────────────────────────

    async def _phase_article_critic(self, state: PipelineState) -> None:
        self._log("ARTICLE", "Running final journal review...", state)
        article = state.writing_state.get("article", "")
        claims = state.writing_state.get("claims", [])
        if not article:
            self._log("ARTICLE", "No article to review", state)
            state.pending_events.append({"type": "phase_warning", "message": "Skipped: no article draft available from Phase 9 (Synthesize)."})
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

        self._log("ARTICLE", f"Critic review complete: score={data.get('overall_score', 0)}, must_revise={data.get('must_revise', False)}", state)

        if corrections:
            await self._apply_corrections_to_article(state, corrections, source="critic")

    def _critic_prompt(self, state: PipelineState, article: str, claims: list[dict]) -> str:
        claims_json = json.dumps(claims, indent=2, ensure_ascii=False)
        doc_type = state.writing_state.get("document_type", "article")
        if doc_type in ("paper", "thesis"):
            reviewer_role = "You are a peer reviewer for an academic journal."
            criteria = (
                f'1. Unsupported or uncited statements\n'
                f'2. Overgeneralizations beyond the evidence\n'
                f'3. Missing counterarguments or alternative interpretations\n'
                f'4. Weak or missing methodology justification\n'
                f'5. Insufficient literature engagement\n'
                f'6. Informal language that should be academic\n'
                f'7. Logical gaps between evidence and conclusion\n'
            )
        else:
            reviewer_role = "You are a journal reviewer."
            criteria = (
                f'1. Unsupported statements\n'
                f'2. Overgeneralizations\n'
                f'3. Missing counterpoints\n'
                f'4. Weak citations\n'
            )
        return (
            f'{phases.get_language_instruction(state)}\n\n'
            f'Document type: {doc_type}\n\n'
            f'Article:\n{article}\n\n'
            f'Original Claims:\n{claims_json}\n\n'
            f'{reviewer_role} Find:\n'
            f'{criteria}\n'
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

    # ── Revision helper ────────────────────────────────────────────────────

    async def _apply_corrections_to_article(
        self,
        state: PipelineState,
        corrections: list[dict],
        source: str = "critic",
    ) -> None:
        """Call the article_revise LLM role to apply corrections to the current article draft."""
        article = state.writing_state.get("article", "")
        if not article or not corrections:
            return

        corrections_text = "\n".join(
            f"- [{c.get('action', 'revise')}] {c.get('issue', '')} → {c.get('suggestion', '')}"
            for c in corrections
        )
        user_prompt = (
            f"{phases.get_language_instruction(state)}\n\n"
            f"Apply the following corrections to the article.\n\n"
            f"CORRECTIONS ({source}):\n{corrections_text}\n\n"
            f"ARTICLE:\n{article}\n\n"
            f"Output ONLY the full revised article text."
        )
        try:
            revised, _ = await self._call_llm_cached(
                role="article_revise",
                system_prompt=_REVISER_SYSTEM,
                user_prompt=user_prompt,
                state=state,
            )
            revised = revised.strip()
            if revised and len(revised) >= len(article) * 0.5:
                state.writing_state["article"] = revised
                state.writing_state["article_revised"] = revised
                self._log("ARTICLE", f"Reviser ({source}) applied {len(corrections)} corrections", state)
            else:
                self._log("ARTICLE", f"Reviser ({source}) returned short/empty response — keeping original", state)
        except Exception as exc:
            self._log("ARTICLE", f"Reviser ({source}) failed: {exc} — keeping original", state)

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

        doc_type = state.writing_state.get("document_type", "article")
        ref_heading = "References" if doc_type in ("paper", "thesis") else "Sources"

        # Build final article text
        lines: list[str] = []
        if title:
            lines.append(f"# {title}\n")
        if abstract:
            if doc_type in ("paper", "thesis"):
                lines.append(f"## Abstract\n\n{abstract}\n")
            else:
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

        # Add references/sources section — numbered bibliography for academic docs
        if sources_used:
            lines.append(f"\n## {ref_heading}\n")
            for i, s in enumerate(sources_used, 1):
                url = s.get("url", "")
                title_str = s.get("title", "") or url
                if doc_type in ("paper", "thesis"):
                    date_str = s.get("date", "")
                    year = date_str[:4] if date_str and len(date_str) >= 4 and date_str[:4].isdigit() else ""
                    year_part = f" ({year})." if year else "."
                    lines.append(f"{i}. {title_str}{year_part} Retrieved from {url}\n")
                else:
                    lines.append(f"- [{title_str}]({url})\n")

        final_text = clean_llm_artifacts("\n".join(lines))
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

    # ── Phase 5.5: Humanize ───────────────────────────────────────────────

    async def _phase_article_humanize(self, state: PipelineState) -> None:
        """Two-pass humanize: audit AI-writing tells, then rewrite to eliminate them."""
        self._log("ARTICLE", "Humanize pass: auditing AI-writing patterns...", state)
        article = state.writing_state.get("final_article", "") or state.writing_state.get("article", "")
        if not article or len(article) < 100:
            self._log("ARTICLE", "No article to humanize", state)
            return

        raw, _ = await self._call_llm_cached(
            role="article_humanize",
            system_prompt=phases.WRITING_HUMANIZE_SYSTEM,
            user_prompt=phases.writing_humanize_prompt(state, article),
            state=state,
        )
        try:
            data = extract_json(raw)
        except Exception as exc:
            self._log("ARTICLE", f"Humanize parse error: {exc}", state)
            state.errors.append(f"Article humanize: parse error: {exc}")
            return

        humanized = clean_llm_artifacts(data.get("humanized_article", ""))
        ai_tells = data.get("ai_tells", [])

        if not humanized or len(humanized) < len(article) * 0.5:
            skip_reason = "empty_response" if not humanized else "truncated_below_threshold"
            self._log("ARTICLE", f"Humanize returned {skip_reason} — keeping original", state)
            state.writing_state["humanize_skipped"] = True
            state.writing_state["humanize_skip_reason"] = skip_reason
            return

        state.writing_state["ai_tells_found"] = ai_tells
        state.writing_state["humanized_article"] = humanized

        # Update the candidate with the humanized version
        if state.candidates:
            last = state.candidates[-1]
            state.candidates[-1] = SolutionCandidate(
                perspective=last.perspective,
                content=humanized,
                key_insights=last.key_insights,
                model_used=last.model_used,
            )

        self._log(
            "ARTICLE",
            f"Humanize complete: {len(ai_tells)} AI tells fixed, "
            f"{len(humanized)} chars",
            state,
        )

    # ── Fallback extraction helpers ──────────────────────────────────────────

    def _extract_pre_mortem_fallback(self, text: str) -> dict[str, Any]:
        """
        Robust fallback for pre-mortem JSON extraction when the LLM
        produces malformed JSON (fences, unescaped quotes, truncation).
        Uses delimiter-aware scanning rather than naive regex so that
        unescaped quotes inside values don't truncate extraction early.
        """
        data: dict[str, Any] = {}
        _ALL_KEYS = [
            "failure_narrative", "root_causes", "weak_sections",
            "challenged_claims", "missing_counterarguments",
            "overgeneralizations", "early_warnings",
        ]

        def _find_value_start(key: str) -> int | None:
            m = re.search(rf'"{key}"\s*:\s*', text)
            return m.end() if m else None

        def _find_value_end(start: int, is_array: bool = False) -> int:
            """Find the end of a value starting at *start*.
            For arrays, balances []. For strings, scans until an unescaped
            quote followed by structural punctuation (comma or brace).
            """
            if is_array:
                if start >= len(text) or text[start] != "[":
                    return len(text)
                depth = 0
                in_str = False
                escape = False
                for i in range(start, len(text)):
                    ch = text[i]
                    if escape:
                        escape = False
                        continue
                    if ch == "\\" and in_str:
                        escape = True
                        continue
                    if ch == '"' and not escape:
                        in_str = not in_str
                        continue
                    if not in_str:
                        if ch == "[":
                            depth += 1
                        elif ch == "]":
                            depth -= 1
                            if depth == 0:
                                return i + 1
                return len(text)
            else:
                # String value — must start with quote
                if start >= len(text) or text[start] != '"':
                    return len(text)
                in_str = False
                escape = False
                for i in range(start, len(text)):
                    ch = text[i]
                    if escape:
                        escape = False
                        continue
                    if ch == "\\" and in_str:
                        escape = True
                        continue
                    if ch == '"' and not escape:
                        in_str = not in_str
                        if not in_str:
                            # Closing quote found — confirm it's followed by
                            # structural punctuation before accepting
                            j = i + 1
                            while j < len(text) and text[j].isspace():
                                j += 1
                            if j < len(text) and text[j] in ",}]":
                                return i + 1
                            # Otherwise keep scanning (it was an internal quote)
                return len(text)

        def _extract_str(key: str) -> str:
            start = _find_value_start(key)
            if start is None:
                return ""
            end = _find_value_end(start, is_array=False)
            if end <= start + 1:
                return ""
            # Strip the surrounding quotes
            val = text[start:end]
            if val.startswith('"'):
                val = val[1:]
            # Find the last quote that was meant to close the value
            # (scan backwards for a quote that is followed by structural punctuation)
            for i in range(len(val) - 1, -1, -1):
                if val[i] == '"':
                    j = i + 1
                    while j < len(val) and val[j].isspace():
                        j += 1
                    if j == len(val) or val[j] in ",}]":
                        val = val[:i]
                        break
            return val.replace('\\"', '"').strip()

        def _extract_list(key: str) -> list[str]:
            start = _find_value_start(key)
            if start is None:
                return []
            end = _find_value_end(start, is_array=True)
            arr_text = text[start:end]
            if not arr_text.startswith("["):
                return []
            # Extract individual string items.
            # We scan for quoted segments, but we only treat a quote as a
            # string terminator when it is followed by comma or ] (allowing
            # whitespace).  This tolerates unescaped quotes inside values.
            items: list[str] = []
            i = 1  # skip [
            while i < len(arr_text) - 1:
                while i < len(arr_text) and arr_text[i].isspace():
                    i += 1
                if i >= len(arr_text) or arr_text[i] != '"':
                    i += 1
                    continue
                item_start = i
                in_str = False
                escape = False
                for j in range(i, len(arr_text)):
                    ch = arr_text[j]
                    if escape:
                        escape = False
                        continue
                    if ch == "\\" and in_str:
                        escape = True
                        continue
                    if ch == '"' and not escape:
                        in_str = not in_str
                        if not in_str:
                            # Confirm this is a real terminator (followed by , or ])
                            k = j + 1
                            while k < len(arr_text) and arr_text[k].isspace():
                                k += 1
                            if k < len(arr_text) and arr_text[k] in ",]":
                                items.append(arr_text[item_start + 1:j].replace('\\"', '"'))
                                i = j + 1
                                break
                else:
                    break
                # Skip comma
                while i < len(arr_text) and arr_text[i].isspace():
                    i += 1
                if i < len(arr_text) and arr_text[i] == ",":
                    i += 1
            return [it for it in items if it]

        data["failure_narrative"] = _extract_str("failure_narrative")
        data["root_causes"] = _extract_list("root_causes")
        data["weak_sections"] = _extract_list("weak_sections")
        data["challenged_claims"] = _extract_list("challenged_claims")
        data["missing_counterarguments"] = _extract_list("missing_counterarguments")
        data["overgeneralizations"] = _extract_list("overgeneralizations")
        data["early_warnings"] = _extract_list("early_warnings")
        return data

    def _extract_cove_array_fallback(self, text: str, field: str) -> list[dict]:
        """
        Extract an array of objects for *field* from malformed CoVE JSON.
        Tolerates fences, truncation, and unescaped quotes.
        """
        # Strip fences
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean[7:].lstrip()
        elif clean.startswith("```"):
            clean = clean[3:].lstrip()
        if clean.rstrip().endswith("```"):
            clean = clean.rstrip()[:-3].rstrip()

        # Find the field's array — tolerate missing closing ]
        m = re.search(rf'"{field}"\s*:\s*\[(.*)', clean, re.DOTALL)
        if not m:
            return []
        arr_text = m.group(1)

        # Extract individual objects with a bracket balancer (tolerates truncation)
        items: list[dict] = []
        i = 0
        while i < len(arr_text):
            # Find next '{'
            while i < len(arr_text) and arr_text[i] != '{':
                i += 1
            if i >= len(arr_text):
                break
            start = i
            depth = 0
            in_str = False
            escape = False
            for j in range(i, len(arr_text)):
                ch = arr_text[j]
                if escape:
                    escape = False
                    continue
                if ch == "\\" and in_str:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_str = not in_str
                    continue
                if not in_str:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            obj_str = arr_text[start:j + 1]
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict):
                                    items.append(obj)
                            except json.JSONDecodeError:
                                obj_data = self._extract_kv_pairs_from_object(obj_str)
                                if obj_data:
                                    items.append(obj_data)
                            i = j + 1
                            break
            else:
                # Truncated object — try to extract what we can
                obj_str = arr_text[start:]
                obj_data = self._extract_kv_pairs_from_object(obj_str)
                if obj_data:
                    items.append(obj_data)
                break
        return items

    def _extract_kv_pairs_from_object(self, obj_str: str) -> dict[str, Any] | None:
        """Extract key-value pairs from a (possibly truncated) JSON object string."""
        data: dict[str, Any] = {}
        for kv in re.finditer(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str):
            data[kv.group(1)] = kv.group(2).replace('\\"', '"')
        # Also try bare values (numbers, booleans)
        for kv in re.finditer(r'"([^"]+)"\s*:\s*(true|false|null|\d+(?:\.\d+)?)\s*(?:,|\}|$)', obj_str):
            key = kv.group(1)
            val = kv.group(2)
            if val == "true":
                data[key] = True
            elif val == "false":
                data[key] = False
            elif val == "null":
                data[key] = None
            else:
                try:
                    data[key] = int(val)
                except ValueError:
                    data[key] = float(val)
        return data if data else None
