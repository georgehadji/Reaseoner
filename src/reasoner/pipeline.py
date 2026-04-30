# Author: Georgios-Chrysovalantis Chatzivantsidis
"""
Reasoner Pipeline - Dynamic Pipeline Orchestrator
This file has been refactored to support multiple, method-specific reasoning flows
for improved performance and token-cost efficiency.
"""

from __future__ import annotations
import asyncio
import functools
import json
import logging
import os
import re
import time
from dataclasses import asdict
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def timed(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that records phase duration in ``state.phase_durations``."""
    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        start = time.monotonic()
        try:
            return await func(self, *args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            state = args[0] if args else None
            if state is not None and hasattr(state, "phase_durations"):
                state.phase_durations[func.__name__] = elapsed
            # Only log if we have a valid state object
            if state is not None and hasattr(state, "log"):
                self._log("TIMING", f"{func.__name__} completed in {elapsed*1000:.1f}ms", state)

    return async_wrapper  # type: ignore[return-value]
from reasoner.models import (PipelineState, SolutionCandidate, CritiqueScore, StressTestResult,
                ScenarioType, GenerationCandidate, CriticScore, VerificationResult,
                MetaEvaluation, ClaimLabel, PerspectiveType, FinalSolution, MetaCognitiveAudit, TaskType)
from reasoner.parsing import ParseError, extract_json, safe_list, safe_float, _parse_critique_scores
from reasoner.llm import LLMError, ProviderRouter
from reasoner.infrastructure.llm.executor import LLMExecutor
from reasoner.core import PhaseConfig, make_phase_result, DEFAULT_PERSPECTIVES
from reasoner.core.temperatures import PHASE_TEMPERATURES
from reasoner.core.constants import (
    ARTICLE_MIN_SOURCE_COUNT,
    PHASE_TOKEN_BUDGETS,
    get_token_budget,
    DEFAULT_MAX_TOKENS,
    TRUNCATION,
)
from reasoner.core.search import get_discovery_client  # Import for web search
from reasoner.token_cache import get_token_cache # TOKEN OPTIMIZATION: Token-aware caching
from reasoner.sanitization import sanitize_for_prompt, clean_llm_artifacts  # SECURITY: prompt-injection defense
import reasoner.phases as phases # Refactored phases
from reasoner.application.mixins.search_mixin import SearchMixin
from reasoner.application.mixins.perspective_mixin import PerspectiveMixin
from reasoner.application.mixins.debate_mixin import DebateMixin
from reasoner.application.mixins.jury_mixin import JuryMixin
from reasoner.application.mixins.research_mixin import ResearchMixin
from reasoner.application.mixins.dialectical_mixin import DialecticalMixin
from reasoner.application.mixins.delphi_mixin import DelphiMixin
from reasoner.application.mixins.cognitive_mixin import CognitiveMixin
from reasoner.application.mixins.recovery_mixin import RecoveryMixin
from reasoner.application.mixins.writing_mixin import WritingMixin
from reasoner.application.mixins.article_pipeline import ArticlePipelineMixin
from reasoner.application.mixins.coding_pipeline import CodingMixin
from reasoner.application.mixins.brainstorming_mixin import BrainstormingMixin

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# TOKEN OPTIMIZATION CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

# Enable/disable token optimization features
TOKEN_OPTIMIZATION = {
    "dynamic_budgets": True,      # Use phase-specific token budgets
    "context_compression": True,  # Use aggressive context truncation
    "prompt_compression": True,   # Use compressed prompts
    "neuro_compression": False,   # Use neuro-style text compression (experimental)
    "caching": True,              # Enable token-aware caching
}

# ─────────────────────────────────────────────────────────────────────
# PHASE SUBAGENT FEATURE FLAGS
# Toggle per-phase hyperagent orchestration (default OFF for safety)
# ─────────────────────────────────────────────────────────────────────
USE_PHASE_SUBAGENTS = {
    "enhancement": os.getenv("USE_SUBAGENT_ENHANCEMENT", "false").lower() == "true",
    "decomposition": os.getenv("USE_SUBAGENT_DECOMPOSITION", "false").lower() == "true",
    "critique": os.getenv("USE_SUBAGENT_CRITIQUE", "false").lower() == "true",
    "synthesis": os.getenv("USE_SUBAGENT_SYNTHESIS", "false").lower() == "true",
    "search": os.getenv("USE_SUBAGENT_SEARCH", "false").lower() == "true",
}

# Get token cache instance
token_cache = get_token_cache(
    max_tokens=1_000_000,  # 1M token budget
    ttl_seconds=3600,      # 1 hour TTL
    cache_dir="cache/tokens",
) if TOKEN_OPTIMIZATION["caching"] else None

class ReasonerPipeline(
    SearchMixin,
    PerspectiveMixin,
    DebateMixin,
    JuryMixin,
    DelphiMixin,
    ResearchMixin,
    CognitiveMixin,
    DialecticalMixin,
    RecoveryMixin,
    WritingMixin,
    ArticlePipelineMixin,
    CodingMixin,
    BrainstormingMixin,
):
    """
    Dynamic Reasoner v2.1 Pipeline Orchestrator.
    Routes execution to method-specific pipelines based on the selected preset.
    """
    _PHASE_CONFIGS: dict[str, PhaseConfig] = {
        "classification": PhaseConfig(role="classification", temperature=PHASE_TEMPERATURES["classification"]),
        "decomposition": PhaseConfig(role="decomposition", temperature=PHASE_TEMPERATURES["decomposition"]),
        "perspective": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["perspective"]),
        "constructive": PhaseConfig(role="constructive", temperature=PHASE_TEMPERATURES["perspective"]),
        "destructive": PhaseConfig(role="destructive", temperature=PHASE_TEMPERATURES["perspective"]),
        "systemic": PhaseConfig(role="systemic", temperature=PHASE_TEMPERATURES["perspective"]),
        "minimalist": PhaseConfig(role="minimalist", temperature=PHASE_TEMPERATURES["perspective"]),
        "scoring": PhaseConfig(role="scoring", temperature=PHASE_TEMPERATURES["scoring"]),
        "stress_testing": PhaseConfig(role="stress_testing", temperature=PHASE_TEMPERATURES["stress_testing"]),
        "synthesis": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "generator": PhaseConfig(role="generator_1", temperature=PHASE_TEMPERATURES["generator"]),
        "critic": PhaseConfig(role="critic_1", temperature=PHASE_TEMPERATURES["critic"]),
        "verifier": PhaseConfig(role="verifier", temperature=PHASE_TEMPERATURES["verifier"]),
        "meta_evaluator": PhaseConfig(role="meta_evaluator", temperature=PHASE_TEMPERATURES["meta_evaluator"]),
        "context_vetting": PhaseConfig(role="context_vetting", temperature=PHASE_TEMPERATURES["context_vetting"]),
        "recovery_path": PhaseConfig(role="recovery_path", temperature=PHASE_TEMPERATURES["recovery_path"]),
        "primary": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "research": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["research"]),
        "deep_read": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["deep_read"]),
        "writing_outline": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "writing_draft": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "writing_factcheck": PhaseConfig(role="verifier", temperature=PHASE_TEMPERATURES["verifier"]),
        "writing_assemble": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "article_decompose": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_claim_extract": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_cove_verify": PhaseConfig(role="verifier", temperature=PHASE_TEMPERATURES["verifier"]),
        "article_cove_answer": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_cove_revise": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_verifier": PhaseConfig(role="verifier", temperature=PHASE_TEMPERATURES["verifier"]),
        "article_synthesize": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "article_pre_mortem": PhaseConfig(role="destructive", temperature=PHASE_TEMPERATURES["perspective"]),
        "article_critic": PhaseConfig(role="critic_1", temperature=PHASE_TEMPERATURES["critic"]),
        "article_assemble": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "article_revise": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "article_humanize": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_sot_skeleton": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "article_sot_solve": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["primary"]),
        "coding_spec": PhaseConfig(role="primary", temperature=PHASE_TEMPERATURES["decomposition"]),
        "coding_generate": PhaseConfig(role="constructive", temperature=PHASE_TEMPERATURES["perspective"]),
        "coding_review": PhaseConfig(role="destructive", temperature=PHASE_TEMPERATURES["scoring"]),
        "coding_tests": PhaseConfig(role="verifier", temperature=PHASE_TEMPERATURES["verifier"]),
        "coding_assemble": PhaseConfig(role="synthesis", temperature=PHASE_TEMPERATURES["synthesis"]),
        "prompt_enhancement": PhaseConfig(role="prompt_enhancement", temperature=PHASE_TEMPERATURES["primary"]),
        "expert_1": PhaseConfig(role="expert_1", temperature=PHASE_TEMPERATURES["generator"]),
        "expert_2": PhaseConfig(role="expert_2", temperature=PHASE_TEMPERATURES["generator"]),
        "expert_3": PhaseConfig(role="expert_3", temperature=PHASE_TEMPERATURES["generator"]),
        "expert_4": PhaseConfig(role="expert_4", temperature=PHASE_TEMPERATURES["generator"]),
    }

    def __init__(self, router: ProviderRouter, preset_name: str | None = None, initial_state: PipelineState | None = None, **kwargs) -> None:
        self.router = router
        self.preset_name = preset_name
        self.initial_state = initial_state
        self.verbose = kwargs.get('verbose', True)
        self.parallel = kwargs.get('parallel_perspectives', True)
        self.top_k = kwargs.get('top_k', 2)
        self.source_type = kwargs.get('source_type', 'general')  # For iterative RAG
        self.domain = kwargs.get('domain', None)  # For domain-specific search
        self.enhance_prompt = kwargs.get('enhance_prompt', False)
        self.attachments = kwargs.get('attachments', [])
        self.phase_configs = self._PHASE_CONFIGS.copy()
        self.perspectives = list(DEFAULT_PERSPECTIVES)
        self._executor = LLMExecutor(
            router=router,
            phase_configs=self.phase_configs,
            token_cache=token_cache,
            caching_enabled=TOKEN_OPTIMIZATION["caching"],
        )

    def _log(self, phase: str, message: str, state: PipelineState) -> None:
        if self.verbose: logger.info(f"[{phase}] {message}")
        state.log(phase, message)

    async def _build_attachment_context(
        self,
        attachments: list[dict[str, Any]],
        query: str | None = None,
    ) -> str:
        """Build a context string from extracted attachment texts.

        When DOCUMENT_SEMANTIC_RETRIEVAL_ENABLED is true and a query is provided,
        retrieves only the most relevant chunks via semantic search instead of
        injecting the full document text.

        Format is designed to be unambiguous to LLMs: the injected text IS the
        actual file content.  We use explicit markers so the model cannot mistake
        this for metadata or instructions.
        """
        from reasoner.core.settings import settings

        # ── Semantic retrieval path (opt-in) ──
        if (
            settings.DOCUMENT_SEMANTIC_RETRIEVAL_ENABLED
            and query
            and attachments
        ):
            try:
                from reasoner.documents.vector_store import DocumentVectorStore

                store = DocumentVectorStore()
                file_ids = [att.get("file_id", "") for att in attachments if att.get("file_id")]
                chunks = await store.retrieve(query, file_ids, top_k=5)
                if chunks:
                    parts: list[str] = []
                    for i, chunk_text in enumerate(chunks, 1):
                        parts.append(
                            f"=== EXCERPT {i} (most relevant passage) ===\n"
                            f"[CONTENT START]\n"
                            f"{chunk_text}\n"
                            f"[CONTENT END]"
                        )
                    return (
                        "=== ATTACHED FILES (semantic excerpts) ===\n"
                        "The user has uploaded file(s). Below are the most relevant "
                        "passages retrieved from those files based on the query.\n\n"
                        + "\n\n".join(parts)
                        + "\n=== END OF ATTACHED FILES ==="
                    )
            except Exception as exc:
                logger.warning(
                    "Semantic attachment retrieval failed, falling back to full text: %s", exc
                )

        # ── Fallback: verbatim full-text injection ──
        parts: list[str] = []
        for att in attachments:
            filename = att.get("filename", "unknown")
            extracted = att.get("extracted_text", "").strip()
            if extracted:
                parts.append(
                    f"=== FILE: {filename} ===\n"
                    f"[CONTENT START]\n"
                    f"{extracted}\n"
                    f"[CONTENT END]"
                )
        if not parts:
            return ""
        return (
            "=== ATTACHED FILES (full content provided below) ===\n"
            "The user has uploaded the following file(s). "
            "Treat the content between [CONTENT START] and [CONTENT END] "
            "as the actual file contents.\n\n"
            + "\n\n".join(parts)
            + "\n=== END OF ATTACHED FILES ==="
        )

    async def _call_llm_cached(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Delegate to LLMExecutor — caching, cost tracking, and routing live there."""
        hints = getattr(state, "quality_hints", {})
        if hints:
            hint = hints.get(role) or hints.get(phase_key or "") or ""
            if hint:
                user_prompt = f"{user_prompt}\n\n[Quality Note: {hint}]"
        return await self._executor.execute(role, system_prompt, user_prompt, state, phase_key, **kwargs)

    def _get_method_from_preset(self) -> str:
        """Determines the reasoning method from the preset name."""
        preset = self.preset_name or ""
        if "debate" in preset: return "debate"
        if "jury" in preset or "orchestrated" in preset: return "jury"
        if "research" in preset: return "research"
        if "scientific" in preset: return "scientific"
        if "socratic" in preset: return "socratic"
        if "pre-mortem" in preset or "premortem" in preset: return "pre_mortem"
        if "bayesian" in preset: return "bayesian"
        if "dialectical" in preset: return "dialectical"
        if "analogical" in preset: return "analogical"
        if "delphi" in preset: return "delphi"
        if "self-discover" in preset: return "self_discover"
        if "cove" in preset: return "cove"
        if "sot" in preset: return "sot"
        if "tot" in preset: return "tot"
        if "pot" in preset: return "pot"
        if "coding" in preset or "code-gen" in preset: return "coding"
        if "writing" in preset or "article" in preset or "essay" in preset: return "writing"
        if "cross-language" in preset or "cross_language" in preset: return "cross_language"
        if "brainstorming" in preset or "brainstorm" in preset: return "brainstorming"
        return "multi_perspective" # Default

    async def run(self, problem: str) -> PipelineState:
        """Main entry point. Executes the dynamic pipeline."""
        if not problem or not str(problem).strip():
            raise ValueError("Problem cannot be empty")

        state = self.initial_state if self.initial_state else PipelineState(problem=problem, preset_name=self.preset_name)
        
        # --- ATTACHMENTS: Inject extracted text into problem ---
        if self.attachments:
            state.attachments = self.attachments
            # Use enhanced_problem as query for semantic retrieval if available,
            # otherwise fall back to the raw problem.
            query_for_retrieval = state.enhanced_problem or state.problem or ""
            attachment_context = await self._build_attachment_context(
                self.attachments, query=query_for_retrieval
            )
            if attachment_context:
                state.problem = f"{state.problem}\n\n{attachment_context}"
                if state.enhanced_problem:
                    state.enhanced_problem = f"{state.enhanced_problem}\n\n{attachment_context}"
        
        # --- ARTICLE DETECTION: bypass generic classification for writing requests ---
        from reasoner.application.mixins.article_pipeline import is_article_request
        if is_article_request(state.problem):
            state.task_type = TaskType.TECHNICAL
            state.decomposition = ["article workflow"]
            state.method = "writing"
            self._log("ORCHESTRATOR", "Article request detected — bypassing generic classification", state)

        # --- UNIVERSAL START PHASES ---
        if self.enhance_prompt and not state.enhanced_problem:
            await self._phase_enhance_prompt(state)
        elif not state.enhanced_problem:
            state.enhanced_problem = state.problem
        if not state.task_type: # Only classify if not already done
            await self._phase_0_classify(state)
        else:
            pass # Skipping _phase_0_classify (task_type already set).
        if not state.decomposition: # Only decompose if not already done
            await self._phase_1_decompose(state)
        else:
            pass # Skipping _phase_1_decompose (decomposition already set).

        # --- DYNAMIC METHOD BRANCHING (detect early to control universal phases) ---
        method = self._get_method_from_preset()
        self._log("ORCHESTRATOR", f"Routing to '{method}' method pipeline.", state)

        # --- CONTEXT VETTING (skip for brainstorming — pure ideation needs no web context) ---
        if method != "brainstorming" and not state.vetted_context:
            await self._phase_context_vetting(state, source_type=self.source_type)

        # --- DEEP READ (Optional - for critical sources) ---
        # Run deep read for research method, OR for technical/hybrid problems
        # that ask for learning resources, frameworks, or tutorials.
        # Never run for brainstorming — VS generation works from the raw problem.
        _edu_keywords = {"learn", "tutorial", "framework", "steps", "how to", "getting started",
                         "βήματα", "μάθω", "εκμάθηση", "οδηγός", "resources"}
        _historical_religious_keywords = {
            "schism", "church", "orthodox", "catholic", "protestant", "bible", "theology",
            "christianity", "islam", "judaism", "buddhism", "hinduism", "reformation",
            "crusade", "empire", "byzantine", "medieval", "ancient", "history", "historical",
            "philosophy", "philosopher", "plato", "aristotle", "kant", "nietzsche",
        }
        _is_knowledge_dense = (
            state.task_type in (TaskType.TECHNICAL, TaskType.HYBRID, TaskType.ANALYTICAL)
            and any(kw in state.problem.lower() for kw in _edu_keywords | _historical_religious_keywords)
        )
        if method == "research" or (method != "brainstorming" and _is_knowledge_dense):
            await self._phase_deep_read(state)
        
        # --- CROSS-LANGUAGE TRANSLATION (Optional) ---
        if self.preset_name and ("cross-language" in self.preset_name or "cross_language" in self.preset_name):
            await self._phase_cross_language_translate_in(state)

        # --- CROSS-PHASE VALIDATION ---
        self._validate_evidence_coverage(state)

        # --- DYNAMIC METHOD DISPATCH via PipelineFlow ---
        from reasoner.application.flows import build_default_flow_registry
        flow = build_default_flow_registry(self)
        sequence = flow.get_sequence(method)
        for step in sequence:
            await step.fn(state)

        # --- UNIVERSAL END PHASE ---
        await self._phase_synthesis(state)

        # --- OPTIONAL POST-SYNTHESIS CROSS-MODEL VERIFICATION ---
        if getattr(self, 'post_synthesis_verify', False) or (state.preset_name and "cove" in state.preset_name):
            await self._phase_post_synthesis_verify(state)

        # --- CROSS-LANGUAGE BACK-TRANSLATION (Optional) ---
        if self.preset_name and ("cross-language" in self.preset_name or "cross_language" in self.preset_name):
            await self._phase_cross_language_translate_out(state)

        return state

    def _validate_enhancement(self, original: str, enhanced: str) -> bool:
        """Reject enhancements that distort meaning, append foreign text, or blow up length."""
        if not enhanced or len(enhanced) < 20:
            return False
        # Length guard — reject if more than 1.5x the original (prevents injection bloat).
        # For very short prompts, allow up to 100 chars so concise inputs can still be expanded.
        if len(enhanced) > max(100, len(original) * 1.5):
            return False
            
        # Language translation guard — reject if the LLM helpfully translated the prompt
        # (e.g., from Greek to English), losing the user's implicit language preference.
        from reasoner.phases._shared import detect_language
        if detect_language(original) != detect_language(enhanced):
            return False
            
        # Fusion guard — reject if original text is concatenated without whitespace separator
        # (indicates the LLM glued extra text directly onto the original)
        stripped = original.rstrip(";!?.\n ")
        if stripped in enhanced and not enhanced.endswith(stripped + " "):
            tail = enhanced[len(stripped):]
            if tail and not tail[0].isspace():
                return False
        # Semantic-flip guard — simple heuristic: if the original asks a positive question
        # and the enhanced asks a negative one, reject. (We can't do full semantic analysis,
        # but we can guard against obvious polarity inversions.)
        # For now, the stricter system prompt handles this; the length/fusion guards catch
        # the most common corruption vectors.
        return True

    @timed
    async def _phase_enhance_prompt(self, state: PipelineState):
        """Optional pre-phase: rewrite the user's problem for clarity and specificity."""
        if state.enhanced_problem:
            self._log("PROMPT-ENHANCE", "Using cached enhanced prompt.", state)
            return

        # ── Subagent path (opt-in via env) ────────────────────────────
        if USE_PHASE_SUBAGENTS["enhancement"]:
            self._log("PROMPT-ENHANCE", "Using EnhancementHyperAgent (subagent mode)...", state)
            from reasoner.subagents.enhancement.hyper_agent import EnhancementHyperAgent
            agent = EnhancementHyperAgent()
            try:
                enhanced = await agent.execute(state, self.router)
                if self._validate_enhancement(state.problem, enhanced):
                    state.enhanced_problem = enhanced
                    self._log("PROMPT-ENHANCE", f"Enhanced prompt: {enhanced[:TRUNCATION.API_STORAGE]}...", state)
                else:
                    state.enhanced_problem = state.problem
                    self._log("PROMPT-ENHANCE", "Subagent enhancement rejected by validation; using original prompt.", state)
            except Exception as exc:
                state.enhanced_problem = state.problem
                self._log("PROMPT-ENHANCE", f"Subagent enhancement failed ({exc}); using original prompt.", state)
            return

        # ── Legacy monolithic path ─────────────────────────────────────
        self._log("PROMPT-ENHANCE", "Enhancing user prompt (monolithic mode)...", state)
        from reasoner.phases import detect_language
        lang = state.language or detect_language(state.problem)
        raw, _ = await self._call_llm_cached(
            role="prompt_enhancement",
            system_prompt=phases.PROMPT_ENHANCEMENT_SYSTEM,
            user_prompt=phases.prompt_enhancement_prompt(state.problem, lang),
            state=state,
            max_tokens=get_token_budget("classification") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        try:
            data = extract_json(raw)
            enhanced = data.get("enhanced_problem", "").strip()
            if self._validate_enhancement(state.problem, enhanced):
                state.enhanced_problem = enhanced
                self._log("PROMPT-ENHANCE", f"Enhanced prompt: {enhanced[:TRUNCATION.API_STORAGE]}...", state)
            else:
                state.enhanced_problem = state.problem
                self._log("PROMPT-ENHANCE", "Enhancement rejected by validation; using original prompt.", state)
        except Exception as exc:
            state.enhanced_problem = state.problem
            self._log("PROMPT-ENHANCE", f"Enhancement failed ({exc}); using original prompt.", state)

    @timed
    async def _phase_0_classify(self, state: PipelineState):
        self._log("PHASE-0", "Classifying task...", state)
        from reasoner.phases import detect_language
        problem = state.enhanced_problem or state.problem
        lang = detect_language(problem)
        raw, _ = await self._call_llm_cached(
            role="classification",
            system_prompt=phases.CLASSIFICATION_SYSTEM,
            user_prompt=phases.classification_prompt(problem, lang, state),
            state=state,
            max_tokens=get_token_budget("classification") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        data = extract_json(raw)
        state.task_type = data.get("task_type")
        detected_lang = data.get("language") or lang
        # Guard: if heuristic found non-English but LLM hallucinated English, trust heuristic
        if detected_lang == "English" and lang != "English":
            detected_lang = lang
        state.language = detected_lang

    @timed
    async def _phase_1_decompose(self, state: PipelineState):
        self._log("PHASE-1", "Decomposing problem...", state)

        # ── Subagent path (opt-in via env) ────────────────────────────
        if USE_PHASE_SUBAGENTS["decomposition"]:
            from reasoner.subagents.decomposition.hyper_agent import DecompositionHyperAgent
            agent = DecompositionHyperAgent()
            try:
                original_problem = state.problem
                if state.enhanced_problem:
                    state.problem = state.enhanced_problem
                state.decomposition = await agent.execute(state, self.router)
                state.problem = original_problem
                self._log("PHASE-1", "DecompositionHyperAgent complete.", state)
            except Exception as exc:
                state.problem = original_problem
                self._log("PHASE-1", f"DecompositionHyperAgent failed ({exc}), falling back to legacy.", state)
                # Fall through to legacy path
            else:
                return

        # ── Legacy monolithic path ─────────────────────────────────────
        original_problem = state.problem
        if state.enhanced_problem:
            state.problem = state.enhanced_problem
        raw, _ = await self._call_llm_cached(
            role="decomposition",
            system_prompt=phases.DECOMPOSITION_SYSTEM,
            user_prompt=phases.decomposition_prompt(state),
            state=state,
            max_tokens=get_token_budget("decomposition") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        # Restore original problem after decomposition so state remains consistent
        state.problem = original_problem
        data = extract_json(raw)
        state.decomposition = data # Simplified

    @timed
    async def _phase_synthesis(self, state: PipelineState):
        self._log("SYNTHESIS", "Synthesizing final solution...", state)

        method_name = self._get_method_from_preset()

        # ── Brainstorming path — synthesize from VS developments ──────────────
        if method_name == "brainstorming":
            await self._phase_synthesis_brainstorming(state)
            return

        if method_name == "writing" and state.writing_state.get("final_article"):
            self._log("SYNTHESIS", "Using assembled article directly for writing workflow.", state)
            final_article = state.writing_state.get("final_article", "")
            raw_cited_sources = state.writing_state.get("sources_cited", [])
            article_link_lookup = {
                url.strip(): {"title": title.strip() or url.strip(), "url": url.strip()}
                for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", final_article)
            }
            cited_sources: list[dict[str, str]] = []
            seen_urls: set[str] = set()
            for source in raw_cited_sources:
                if isinstance(source, dict):
                    url = str(source.get("url", "")).strip()
                    title = str(source.get("title", "")).strip() or article_link_lookup.get(url, {}).get("title", url)
                elif isinstance(source, str):
                    url = source.strip()
                    title = article_link_lookup.get(url, {}).get("title", url)
                else:
                    continue
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                cited_sources.append({"title": title or url, "url": url})
            confidence_parts = [
                f"Claim support ratio: {state.writing_state.get('metrics', {}).get('claim_support_ratio', 0)}",
                f"Citation accuracy: {state.writing_state.get('metrics', {}).get('citation_accuracy', 0)}",
            ]
            if len(cited_sources) < ARTICLE_MIN_SOURCE_COUNT:
                confidence_parts.append(
                    f"Evidence base is limited to {len(cited_sources)} source links, below the preferred target of {ARTICLE_MIN_SOURCE_COUNT}."
                )
            state.final_solution = FinalSolution(
                core_solution=final_article,
                critical_insights=state.writing_state.get("final_changes", [])[:5] or state.writing_state.get("gaps_noted", [])[:5],
                action_blueprint=[],
                open_questions=state.writing_state.get("gaps_noted", []),
                claim_labels={},
                meta_audit=MetaCognitiveAudit(
                    most_dangerous_assumption="",
                    dominant_bias="",
                    remaining_uncertainty=" ".join(confidence_parts).strip(),
                    assumption_failure_impact="",
                    non_obvious_insight="",
                ),
                sources=cited_sources,
            )
            return

        # ── Subagent path (opt-in via env) ────────────────────────────
        if USE_PHASE_SUBAGENTS["synthesis"]:
            from reasoner.subagents.synthesis.hyper_agent import SynthesisHyperAgent
            agent = SynthesisHyperAgent()
            try:
                state.final_solution = await agent.execute(state, self.router)
                self._log("SYNTHESIS", "SynthesisHyperAgent complete.", state)
                return
            except Exception as exc:
                self._log("SYNTHESIS", f"SynthesisHyperAgent failed ({exc}), falling back to legacy.", state)
                # Fall through to legacy path

        # ── Legacy monolithic path ─────────────────────────────────────
        # TOKEN OPTIMIZATION: Use synthesis-specific token budget + caching (highest budget)
        # Language instruction is already included in synthesis_prompt() via get_language_instruction()
        # and SYNTHESIS_SYSTEM contains its own LANGUAGE RULE block, so we don't inject it here too.
        system_prompt = phases.SYNTHESIS_SYSTEM
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=system_prompt,
            user_prompt=phases.synthesis_prompt(state),
            state=state,
            max_tokens=get_token_budget("synthesis") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        # Parse the synthesis response
        from reasoner.parsing import extract_solution_prose, extract_json, strip_json_fences
        try:
            json_data = extract_json(raw) or {}
        except ParseError as exc:
            self._log("SYNTHESIS", f"Failed to parse JSON from synthesis: {exc}", state)
            json_data = {}

        # Build prose fallback if [SOLUTION] tags are missing
        def _reconstruct_prose(data: dict) -> str:
            parts = []
            insights = data.get("critical_insights", [])
            if insights:
                parts.append("Critical Insights:\n" + "\n".join(f"- {i}" for i in insights))
            bp = data.get("action_blueprint", [])
            if bp:
                parts.append("Action Blueprint:\n" + "\n".join(
                    f"- {b.get('step', '')}: {b.get('action', '')}" for b in bp if isinstance(b, dict)
                ))
            oq = data.get("open_questions", [])
            if oq:
                parts.append("Open Questions:\n" + "\n".join(f"- {q}" for q in oq))
            return "\n\n".join(parts)

        core_solution = extract_solution_prose(raw)
        if not core_solution:
            core_solution = json_data.get("core_solution", "")
        if not core_solution:
            core_solution = _reconstruct_prose(json_data)
        if not core_solution:
            # Last resort: strip any JSON fences from raw text so user never sees raw JSON
            core_solution = strip_json_fences(raw)

        core_solution = clean_llm_artifacts(core_solution)

        # Citation integrity validator: warn on URLs not present in current context
        allowed_urls = {r.get("url", "").rstrip("/") for r in (state.vetted_context or [])}
        allowed_urls.update(r.get("url", "").rstrip("/") for r in (state.web_discovery_results or []))
        import re as _re
        found_urls = set(_re.findall(r"https?://[^\s\)\]]+", core_solution))
        for url in found_urls:
            base = url.rstrip("/")
            if base and base not in allowed_urls:
                self._log("SYNTHESIS", f"Citation integrity warning: {url} not found in current context", state)

        # Safely handle claim labels
        raw_labels = json_data.get("claim_labels", {})
        if not isinstance(raw_labels, dict): raw_labels = {}
        clean_labels = {}
        for k, v in raw_labels.items():
            try:
                # Use value if it's already a valid Enum string, else UNKNOWN
                if v in [e.value for e in ClaimLabel]:
                    clean_labels[k] = ClaimLabel(v)
                else:
                    clean_labels[k] = ClaimLabel.UNKNOWN
            except Exception:
                clean_labels[k] = ClaimLabel.UNKNOWN

        # Safely handle meta audit
        meta_audit_data = json_data.get("meta_audit", {})
        if not isinstance(meta_audit_data, dict): meta_audit_data = {}

        # Safely coerce sources to list[dict[str, str]]
        def _coerce_sources(items):
            out = []
            for item in items:
                if isinstance(item, dict) and "title" in item:
                    out.append({"title": str(item.get("title", "")), "url": str(item.get("url", ""))})
                elif isinstance(item, str):
                    import re
                    m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", item)
                    if m:
                        out.append({"title": m.group(1).strip(), "url": m.group(2).strip()})
                    else:
                        out.append({"title": item.strip(), "url": ""})
            return out

        # Sanitize action blueprint: drop entries without at least one expected key or empty action
        raw_bp = json_data.get("action_blueprint", [])
        clean_bp = []
        for step in (raw_bp if isinstance(raw_bp, list) else []):
            if isinstance(step, dict):
                if not any(k in step for k in ("step", "action", "time_horizon", "go_criteria", "fallback")):
                    continue
                if not str(step.get("step", "") or "").strip() and not str(step.get("action", "") or "").strip():
                    continue
                clean_bp.append(step)
            elif step is not None and str(step).strip():
                clean_bp.append({"step": "", "action": str(step).strip(), "time_horizon": "", "go_criteria": "", "fallback": ""})

        state.final_solution = FinalSolution(
            core_solution=core_solution,
            critical_insights=json_data.get("critical_insights", []),
            action_blueprint=clean_bp,
            open_questions=json_data.get("open_questions", []),
            claim_labels=clean_labels,
            meta_audit=MetaCognitiveAudit(
                most_dangerous_assumption=meta_audit_data.get("most_dangerous_assumption", ""),
                dominant_bias=meta_audit_data.get("dominant_bias", ""),
                remaining_uncertainty=meta_audit_data.get("remaining_uncertainty", ""),
                assumption_failure_impact=meta_audit_data.get("assumption_failure_impact", ""),
                non_obvious_insight=meta_audit_data.get("non_obvious_insight", "")
            ),
            sources=_coerce_sources(json_data.get("sources", []))
        )

    @timed
    async def _phase_post_synthesis_verify(self, state: PipelineState) -> None:
        """Optional cross-model verification of the final synthesis."""
        if not state.final_solution:
            return
        synthesis_text = state.final_solution.core_solution
        if not synthesis_text:
            return
        self._log("POST-SYNTHESIS", "Running cross-model verification...", state)
        try:
            raw, _ = await self._call_llm_cached(
                role="post_synthesis_verify",
                system_prompt=phases.POST_SYNTHESIS_VERIFY_SYSTEM,
                user_prompt=phases.post_synthesis_verify_prompt(synthesis_text, state), state=state)
            data = extract_json(raw)
            state.final_solution.verification_audit = {
                "verification_questions": data.get("verification_questions", []),
                "evaluation": data.get("evaluation", []),
                "recommendations": data.get("recommendations", []),
            }
        except Exception as e:
            self._log("POST-SYNTHESIS", f"Verification failed: {e}", state)
            state.errors.append(f"Post-synthesis verification error: {e}")

    async def _phase_cross_language_translate_in(self, state: PipelineState) -> None:
        """Translate the problem into English before reasoning.

        Stores the original problem and detected language in
        ``state.cross_language_state`` so the synthesis can be
        translated back later.
        """
        from reasoner.infrastructure.translation import get_deepl_client

        source_lang = state.language
        # Skip if already English or unknown
        if not source_lang or source_lang.lower() in ("english", "en", "unknown", ""):
            self._log("CROSS-LANG", "Source language is English — skipping translation in.", state)
            return

        original_problem = state.problem
        original_enhanced = state.enhanced_problem

        self._log("CROSS-LANG", f"Translating problem from {source_lang} to English...", state)
        try:
            client = get_deepl_client()
            result = await client.translate(original_problem, target_lang="EN")
            translated = result.get("text") or original_problem
            detected = result.get("detected_source_language", source_lang)

            state.problem = translated
            if original_enhanced and original_enhanced != original_problem:
                enh_result = await client.translate(original_enhanced, target_lang="EN")
                state.enhanced_problem = enh_result.get("text") or original_enhanced
            else:
                state.enhanced_problem = translated

            state.cross_language_state = {
                "original_problem": original_problem,
                "original_enhanced": original_enhanced,
                "source_language": detected,
                "translated_problem": translated,
                "direction": "in",
            }
            self._log("CROSS-LANG", f"Translated ({len(original_problem)} → {len(translated)} chars)", state)
        except Exception as e:
            self._log("CROSS-LANG", f"Translation in failed: {e} — continuing with original text.", state)
            state.errors.append(f"Cross-language translation-in error: {e}")

    async def _phase_cross_language_translate_out(self, state: PipelineState) -> None:
        """Translate the final synthesis back to the original language."""
        from reasoner.infrastructure.translation import get_deepl_client

        if not state.cross_language_state or not state.cross_language_state.get("source_language"):
            self._log("CROSS-LANG", "No source language recorded — skipping translation out.", state)
            return

        source_lang = state.cross_language_state["source_language"]
        target_lang = source_lang.upper()

        synthesis_text = ""
        if state.final_solution and state.final_solution.core_solution:
            synthesis_text = state.final_solution.core_solution
        elif state.candidates:
            synthesis_text = state.candidates[0].content

        if not synthesis_text:
            self._log("CROSS-LANG", "No synthesis text to translate back.", state)
            return

        self._log("CROSS-LANG", f"Translating synthesis back to {target_lang}...", state)
        try:
            client = get_deepl_client()
            result = await client.translate(synthesis_text, target_lang=target_lang, source_lang="EN")
            translated = result.get("text") or synthesis_text

            if state.final_solution:
                state.final_solution.core_solution = translated
            state.cross_language_state["translated_synthesis"] = translated
            state.cross_language_state["direction"] = "out"
            self._log("CROSS-LANG", f"Back-translated ({len(synthesis_text)} → {len(translated)} chars)", state)
        except Exception as e:
            self._log("CROSS-LANG", f"Translation out failed: {e} — leaving synthesis in English.", state)
            state.errors.append(f"Cross-language translation-out error: {e}")

