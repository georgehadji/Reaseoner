# Author: Georgios-Chrysovalantis Chatzivantsidis
"""
ARA Pipeline - Dynamic Pipeline Orchestrator
This file has been refactored to support multiple, method-specific reasoning flows
for improved performance and token-cost efficiency.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import time
from dataclasses import asdict
from typing import Any
from reasoner.models import (PipelineState, SolutionCandidate, CritiqueScore, StressTestResult,
                ScenarioType, GenerationCandidate, CriticScore, VerificationResult,
                MetaEvaluation, ClaimLabel, PerspectiveType, FinalSolution, MetaCognitiveAudit)
from reasoner.parsing import ParseError, extract_json, safe_list, safe_float
from reasoner.llm import ProviderRouter
from reasoner.core import PhaseConfig, make_phase_result, DEFAULT_PERSPECTIVES
from reasoner.core.temperatures import PHASE_TEMPERATURES
from reasoner.core.constants import (
    PHASE_TOKEN_BUDGETS,
    get_token_budget,
    DEFAULT_MAX_TOKENS,
    TRUNCATION,
)
from reasoner.core.search import get_discovery_client, _should_include_result # Import for web search and result gating
from reasoner.neuro.server import create_neuro_router # Assuming neuro is an available module
from reasoner.token_cache import get_token_cache # TOKEN OPTIMIZATION: Token-aware caching
from reasoner.sanitization import sanitize_for_prompt  # SECURITY: prompt-injection defense
import reasoner.phases as phases # Refactored phases

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

# Get token cache instance
token_cache = get_token_cache(
    max_tokens=1_000_000,  # 1M token budget
    ttl_seconds=3600,      # 1 hour TTL
    cache_dir="cache/tokens",
) if TOKEN_OPTIMIZATION["caching"] else None

def _parse_critique_scores(raw_scores: list[dict]) -> list[CritiqueScore]:
    """Safely build CritiqueScore objects from raw LLM output.

    CritiqueScore has six required fields with no defaults.  LLMs occasionally
    omit one; passing the dict directly via **s raises TypeError and empties
    state.scores for the entire run.  Additionally, `perspective` arrives as a
    plain string and must be coerced to the PerspectiveType enum.
    """
    out: list[CritiqueScore] = []
    for s in raw_scores:
        try:
            out.append(CritiqueScore(
                perspective=PerspectiveType(s["perspective"]),
                logical_consistency=float(s.get("logical_consistency") or 0),
                evidence_support=float(s.get("evidence_support") or 0),
                failure_resilience=float(s.get("failure_resilience") or 0),
                feasibility=float(s.get("feasibility") or 0),
                bias_flags=s.get("bias_flags") or [],
                steel_man=s.get("steel_man") or "",
                confidence_vs_accuracy_penalty=float(s.get("confidence_vs_accuracy_penalty") or 0),
            ))
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping malformed CritiqueScore entry: %s", exc)
    return out


class ARAPipeline:
    """
    Dynamic ARA v2.1 Pipeline Orchestrator.
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
        self.phase_configs = self._PHASE_CONFIGS.copy() # Simplified for brevity
        self.perspectives = list(DEFAULT_PERSPECTIVES)

    def _log(self, phase: str, message: str, state: PipelineState) -> None:
        if self.verbose: logger.info(f"[{phase}] {message}")
        state.log(phase, message)

    @staticmethod
    def _enrich_query(query: str, problem: str) -> str:
        """Append disambiguation terms for known collision acronyms."""
        problem_lower = problem.lower()
        query_lower = query.lower()
        # AGI disambiguation
        if "agi" in query_lower and ("artificial general intelligence" in problem_lower or "singularity" in problem_lower or "timeline" in problem_lower):
            if "artificial general intelligence" not in query_lower:
                query += " artificial general intelligence"
        return query.strip()
    
    async def _call_llm_cached(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """
        Call LLM with token-aware caching and cost tracking.

        TOKEN OPTIMIZATION: Checks cache before making LLM call.
        Cache hit = 100% token savings for that call.
        COST TRACKING: Accumulates costs in PipelineState for billing.
        """
        # Resolve temperature from centralized registry unless explicitly overridden
        if "temperature" not in kwargs:
            lookup = phase_key or role
            if lookup in self.phase_configs:
                kwargs["temperature"] = self.phase_configs[lookup].temperature
            else:
                for name, cfg in self.phase_configs.items():
                    if cfg.role == role:
                        kwargs["temperature"] = cfg.temperature
                        break
        # Check cache if enabled
        if token_cache and TOKEN_OPTIMIZATION["caching"]:
            problem = state.problem
            model_id = self.router.get(role).model if hasattr(self.router, 'get') else "unknown"

            # Use full prompt for cache key on context-sensitive phases to avoid stale hits
            cache_prompt = user_prompt if role in ("synthesis", "context_vetting", "primary") else user_prompt[:TRUNCATION.PROBLEM]
            cached_response = await token_cache.get(
                problem=problem,
                phase=role,
                model_id=model_id,
                prompt=cache_prompt,
            )

            if cached_response:
                self._log("CACHE", f"HIT for {role} (saved ~{len(cached_response)//4} tokens)", state)
                # Estimate tokens
                tokens = {"input": len(user_prompt)//4, "output": len(cached_response)//4, "total": (len(user_prompt) + len(cached_response))//4}
                state.detailed_token_usage[role] = tokens
                state.phase_models[role] = model_id
                # Per-phase token and model tracking
                phase_key = getattr(state, '_current_phase_key', None)
                if phase_key:
                    if phase_key not in state.phase_tokens:
                        state.phase_tokens[phase_key] = {"input": 0, "output": 0}
                    state.phase_tokens[phase_key]["input"] += tokens["input"]
                    state.phase_tokens[phase_key]["output"] += tokens["output"]
                    if not hasattr(state, '_phase_models_by_key'):
                        state._phase_models_by_key = {}
                    if phase_key not in state._phase_models_by_key:
                        state._phase_models_by_key[phase_key] = []
                    if model_id not in state._phase_models_by_key[phase_key]:
                        state._phase_models_by_key[phase_key].append(model_id)
                # Cache hit = no additional cost
                return cached_response, {**tokens, "cost_usd": 0.0, "model": model_id, "cached": True}

        # Cache miss - make actual LLM call
        self._log("CACHE", f"MISS for {role}", state)
        raw, metadata = await self.router.call(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **kwargs)

        # Extract cost info from metadata and accumulate in state
        cost_usd = metadata.get("cost_usd", 0.0)
        input_tokens = metadata.get("input_tokens", 0)
        output_tokens = metadata.get("output_tokens", 0)
        model = metadata.get("model", "unknown")
        state.phase_models[role] = model

        # Accumulate costs and tokens
        if cost_usd > 0:
            state.total_cost_usd += cost_usd
            state.phase_costs[role] = cost_usd
        state.detailed_token_usage[role] = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        }
        # Per-phase token and model tracking
        phase_key = getattr(state, '_current_phase_key', None)
        if phase_key:
            if phase_key not in state.phase_tokens:
                state.phase_tokens[phase_key] = {"input": 0, "output": 0}
            state.phase_tokens[phase_key]["input"] += input_tokens
            state.phase_tokens[phase_key]["output"] += output_tokens
            # Track models used in this phase
            if not hasattr(state, '_phase_models_by_key'):
                state._phase_models_by_key = {}
            if phase_key not in state._phase_models_by_key:
                state._phase_models_by_key[phase_key] = []
            if model not in state._phase_models_by_key[phase_key]:
                state._phase_models_by_key[phase_key].append(model)

        # Store in cache
        if token_cache and TOKEN_OPTIMIZATION["caching"]:
            model_id = self.router.get(role).model if hasattr(self.router, 'get') else "unknown"
            cache_prompt = user_prompt if role in ("synthesis", "context_vetting", "primary") else user_prompt[:TRUNCATION.PROBLEM]
            await token_cache.set(
                problem=state.problem,
                phase=role,
                model_id=model_id,
                prompt=cache_prompt,
                response=raw,
                tokens_used=input_tokens + output_tokens,
            )

        return raw, metadata

    def _get_method_from_preset(self) -> str:
        """Determines the reasoning method from the preset name."""
        preset = self.preset_name or ""
        if "debate" in preset: return "debate"
        if "iterative" in preset: return "iterative"
        if "jury" in preset or "orchestrated" in preset: return "jury"
        if "research" in preset: return "research"
        if "scientific" in preset: return "scientific"
        if "socratic" in preset: return "socratic"
        if "pre-mortem" in preset or "premortem" in preset: return "pre_mortem"
        if "bayesian" in preset: return "bayesian"
        if "dialectical" in preset: return "dialectical"
        if "analogical" in preset: return "analogical"
        if "delphi" in preset: return "delphi"
        return "multi_perspective" # Default

    async def run(self, problem: str) -> PipelineState:
        """Main entry point. Executes the dynamic pipeline."""
        state = self.initial_state if self.initial_state else PipelineState(problem=problem, preset_name=self.preset_name)
        
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

        # --- CONTEXT VETTING (NEW UNIVERSAL PHASE) ---
        if not state.vetted_context: # Only vet context if not already done
            await self._phase_context_vetting(state, source_type=self.source_type)
        else:
            pass # Skipping _phase_context_vetting (vetted_context already set).

        # --- DYNAMIC METHOD BRANCHING ---
        method = self._get_method_from_preset()
        self._log("ORCHESTRATOR", f"Routing to '{method}' method pipeline.", state)

        # --- DEEP READ (Optional - for critical sources) ---
        # Only run deep read if enabled and not already done by research method
        if method != "research":
            await self._phase_deep_read(state)
        
        # --- CROSS-PHASE VALIDATION ---
        self._validate_evidence_coverage(state)

        if method == "debate": await self._run_debate_pipeline(state)
        elif method == "iterative": await self._run_iterative_pipeline(state)
        elif method == "jury": await self._run_jury_pipeline(state)
        elif method == "research": await self._run_research_pipeline(state)
        elif method == "scientific": await self._run_scientific_pipeline(state)
        elif method == "socratic": await self._run_socratic_pipeline(state)
        elif method == "pre_mortem": await self._run_pre_mortem_pipeline(state)
        elif method == "bayesian": await self._run_bayesian_pipeline(state)
        elif method == "dialectical": await self._run_dialectical_pipeline(state)
        elif method == "analogical": await self._run_analogical_pipeline(state)
        elif method == "delphi": await self._run_delphi_pipeline(state)
        else: await self._run_multi_perspective_pipeline(state)

        # --- UNIVERSAL END PHASE ---
        await self._phase_synthesis(state)
        
        return state

    # ────────────────────────────────────────────────────────────────────
    # Method-Specific Pipeline Flows
    # ────────────────────────────────────────────────────────────────────

    async def _run_multi_perspective_pipeline(self, state: PipelineState):
        await self._phase_2_perspectives(state)
        await self._phase_3_critique(state)
        await self._phase_4_stress_test(state)

    async def _run_iterative_pipeline(self, state: PipelineState):
        MAX_ROUNDS = 3
        CONVERGENCE_THRESHOLD = 8.5
        for i in range(MAX_ROUNDS):
            self._log("ITERATIVE", f"Starting round {i+1}/{MAX_ROUNDS}", state)
            await self._phase_2_perspectives(state, use_reflexion=True)
            await self._phase_3_critique(state)
            # Store insights for the next round
            new_memories = [s.steel_man for s in state.scores if s.steel_man]
            state.reflexion_memory.extend(new_memories)
            # A2: Early convergence exit
            if state.scores:
                mean_score = sum(s.logical_consistency for s in state.scores) / len(state.scores)
                if mean_score >= CONVERGENCE_THRESHOLD:
                    self._log("ITERATIVE", f"Converged at round {i+1} (mean={mean_score:.2f}≥{CONVERGENCE_THRESHOLD}). Stopping early.", state)
                    break
            if i < MAX_ROUNDS - 1: # Don't clear on last round
                state.candidates, state.scores, state.top_candidates = [], [], []

    async def _run_debate_pipeline(self, state: PipelineState):
        await self._phase_debate_opening(state)
        await self._phase_debate_rebuttal(state)
        await self._phase_debate_cross_examine(state)  # A5
        await self._phase_debate_judge(state)

    async def _run_jury_pipeline(self, state: PipelineState):
        await self._phase_jury_generate(state)
        await self._phase_jury_critique(state)
        await self._phase_jury_verify_and_meta_eval(state)
        await self._phase_jury_weighted_ranking(state)  # A3

    async def _run_research_pipeline(self, state: PipelineState):
        await self._phase_research_web_search(state)
        await self._phase_2_perspectives(state) # Re-use for analysis of search results
        await self._phase_3_critique(state)

    async def _run_scientific_pipeline(self, state: PipelineState):
        await self._phase_scientific_hypothesize(state)
        await self._phase_scientific_test(state)
        await self._phase_4_stress_test(state)

    async def _run_socratic_pipeline(self, state: PipelineState):
        await self._phase_socratic_question(state)
        await self._phase_socratic_answer(state)

    # ────────────────────────────────────────────────────────────────────
    # Modular, Reusable & Method-Specific Phase Implementations
    # ────────────────────────────────────────────────────────────────────

    # --- SHARED PHASES ---
    async def _phase_enhance_prompt(self, state: PipelineState):
        """Optional pre-phase: rewrite the user's problem for clarity and specificity."""
        if state.enhanced_problem:
            self._log("PROMPT-ENHANCE", "Using cached enhanced prompt.", state)
            return
        self._log("PROMPT-ENHANCE", "Enhancing user prompt...", state)
        from reasoner.phases import detect_language
        lang = detect_language(state.problem)
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
            if enhanced and len(enhanced) >= 20:
                state.enhanced_problem = enhanced
                self._log("PROMPT-ENHANCE", f"Enhanced prompt: {enhanced[:TRUNCATION.API_STORAGE]}...", state)
            else:
                state.enhanced_problem = state.problem
                self._log("PROMPT-ENHANCE", "Enhancement returned empty/short result; using original prompt.", state)
        except Exception as exc:
            state.enhanced_problem = state.problem
            self._log("PROMPT-ENHANCE", f"Enhancement failed ({exc}); using original prompt.", state)

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

    async def _phase_1_decompose(self, state: PipelineState):
        self._log("PHASE-1", "Decomposing problem...", state)
        # Ensure decomposition uses enhanced prompt if available
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

    async def _phase_context_vetting(self, state: PipelineState, source_type: str = "general") -> None:
        """
        Iterative RAG Phase: Retrieves and vets external context using CoT to flag issues.
        Now uses an iterative loop where the LLM decides if more searches are needed.
        
        Args:
            state: The pipeline state
            source_type: Type of sources to search (general, academic, social, news, code)
        """
        self._log("VETTING", f"Starting iterative context gathering (source: {source_type})...", state)
        
        # Skip if already done by research method
        if state.web_discovery_results:
            self._log("VETTING", "Reusing existing web discovery results from research phase.", state)
            await self._vet_results(state, state.web_discovery_results)
            return
        
        max_iterations = 3
        current_results: list[dict] = []
        seen_urls: set[str] = set()
        
        try:
            client, _ = await get_discovery_client(source_type=source_type)
        except Exception as e:
            self._log("VETTING", f"Failed to initialize discovery client: {e}", state)
            state.errors.append(f"Vetting: Client init failed: {e}")
            return
        
        # Iterative search loop
        for i in range(1, max_iterations + 1):
            self._log("VETTING", f"Iteration {i}/{max_iterations}: Planning searches...", state)
            
            # Ask LLM if more searches are needed
            raw_decision, _ = await self._call_llm_cached(
                role="primary",
                phase_key="research",
                system_prompt=phases.ITERATIVE_CONTEXT_SYSTEM,
                user_prompt=phases.iterative_context_prompt(state, current_results, i, max_iterations),
                state=state)
            
            try:
                decision_data = extract_json(raw_decision)
            except ParseError as e:
                self._log("VETTING", f"Failed to parse iteration decision: {e}", state)
                break
            
            action = decision_data.get("action", "done")
            reasoning = decision_data.get("reasoning", "")
            self._log("VETTING", f"Action: {action}. Reason: {reasoning}", state)

            if action == "done" or i == max_iterations:
                break

            # Guard: LLM occasionally returns "queries" as a bare string instead of
            # a list.  Slicing a string produces chars, not query terms, silently
            # corrupting every downstream search call.
            _raw_q = decision_data.get("queries", [])
            if not isinstance(_raw_q, list):
                # CRITICAL FIX: Log warning when LLM returns malformed queries
                # and attempt to recover by treating string as single query
                if isinstance(_raw_q, str) and _raw_q.strip():
                    queries = [_raw_q.strip()[:TRUNCATION.SNIPPET]]  # Use as single query, truncate to avoid abuse
                    self._log("VETTING", f"LLM returned string query instead of list. Recovered: '{queries[0]}'", state)
                else:
                    self._log("VETTING", f"LLM returned malformed queries (type: {type(_raw_q).__name__}, value: {_raw_q!r}). Skipping this iteration.", state)
                    state.errors.append(f"Vetting: LLM returned non-list queries: {_raw_q!r}")
                    continue
            else:
                queries = [q for q in _raw_q[:TRUNCATION.KEY_INSIGHTS] if isinstance(q, str) and q.strip()]
            
            if not queries:
                self._log("VETTING", "No valid queries to execute. Breaking search loop.", state)
                break

            self._log("VETTING", f"Executing queries: {queries}", state)
            
            # Execute searches concurrently with query enrichment
            enriched_queries = [self._enrich_query(q, state.problem) for q in queries]
            async def _search(q: str):
                try:
                    return await client.search(q, num_results=5, source_type=source_type, domain=self.domain)
                except Exception as exc:
                    self._log("VETTING", f"Query failed '{q}': {exc}", state)
                    return []
            
            results_nested = await asyncio.gather(*[_search(q) for q in enriched_queries])
            
            # Flatten, deduplicate, and apply relevance gating
            dropped = 0
            for res_list in results_nested:
                for res in res_list:
                    url = res.get("url")
                    if not url or url in seen_urls:
                        continue
                    if not _should_include_result(res):
                        dropped += 1
                        continue
                    seen_urls.add(url)
                    current_results.append(res)
            
            if dropped:
                self._log("VETTING", f"Dropped {dropped} low-quality results this iteration.", state)
            self._log("VETTING", f"Found {len(current_results)} unique results so far.", state)
        
        state.web_discovery_results = current_results
        self._log("VETTING", f"Iterative search complete. Total results: {len(current_results)}", state)
        
        # Apply CoT vetting to all results
        await self._vet_results(state, current_results)
    
    async def _vet_results(self, state: PipelineState, results: list[dict]) -> None:
        """Apply CoT vetting to search results."""
        self._log("VETTING", "Applying CoT vetting to results...", state)
        
        vetted_results = []
        for result in results:
            retrieved_text = result.get("snippet", "")
            if not retrieved_text:
                continue
            sanitized_text = sanitize_for_prompt(retrieved_text)[0]
            try:
                raw_flags, _ = await self._call_llm_cached(
                    role="context_vetting",
                    system_prompt=phases.COT_DETECTION_SYSTEM,
                    user_prompt=phases.cot_detection_prompt(state, sanitized_text),
                    max_tokens=512, state=state)
                flags_data = extract_json(raw_flags)
                result["vetting_flags"] = flags_data.get("flags", [])
                if result["vetting_flags"]:
                    self._log("VETTING", f"Flagged issues in a retrieved snippet (source: {result.get('source')}).", state)
            except ParseError as e:
                self._log("VETTING", f"CoT vetting parse error for snippet (source: {result.get('source')}): {e}", state)
                result["vetting_flags"] = [{"statement": "(CoT vetting parse error)", "reasoning": str(e)}]
            except Exception as e:
                self._log("VETTING", f"CoT vetting failed for snippet (source: {result.get('source')}): {e}", state)
                result["vetting_flags"] = [{"statement": "(CoT vetting failed)", "reasoning": str(e)}]
            vetted_results.append(result)
        
        state.vetted_context = vetted_results
        self._log("VETTING", "Context vetting complete.", state)

    async def _phase_deep_read(self, state: PipelineState, max_sources: int = 3) -> None:
        """
        Deep Read Phase: Fetch full content from critical sources and extract
        structured summaries using an LLM.
        
        Args:
            state: The pipeline state
            max_sources: Maximum number of sources to deep read (default: 3)
        """
        self._log("DEEP_READ", "Starting deep read of critical sources...", state)
        
        # Import here to avoid circular imports
        from reasoner.scraper import scrape_urls
        
        # Determine which sources need deep reading
        sources_to_scrape = []
        
        # Check if decomposition marked any sources as critical
        if state.decomposition and isinstance(state.decomposition, dict):
            critical_sources = state.decomposition.get("critical_sources", [])
            if critical_sources:
                sources_to_scrape = [s.get("url") for s in critical_sources if s.get("url")]
        
        # Fallback: use top vetted results
        if not sources_to_scrape and state.vetted_context:
            sources_to_scrape = [
                r.get("url") for r in state.vetted_context[:max_sources]
                if r.get("url")
            ]
        
        if not sources_to_scrape:
            self._log("DEEP_READ", "No sources available for deep reading.", state)
            return
        
        self._log("DEEP_READ", f"Deep reading {len(sources_to_scrape)} sources...", state)
        
        # Feature flag for safety: set REASONER_DEEP_READ_LLM=0 to disable LLM extraction
        use_llm_extraction = os.getenv("REASONER_DEEP_READ_LLM", "1") != "0"
        
        try:
            scraped_results = await scrape_urls(sources_to_scrape)
            
            for scraped in scraped_results:
                url = scraped.get("url")
                title = scraped.get("title", "Unknown")
                
                # Find matching result in vetted_context
                matching_result = None
                for result in state.vetted_context:
                    if result.get("url") == url:
                        matching_result = result
                        break
                
                if not matching_result:
                    continue
                
                if scraped.get("success"):
                    matching_result["deep_content"] = scraped.get("content", "")
                    matching_result["deep_title"] = title
                    self._log("DEEP_READ", f"Successfully scraped: {title}", state)
                    
                    if use_llm_extraction:
                        try:
                            sanitized_content = sanitize_for_prompt(scraped.get("content", ""))[0]
                            raw_extraction, _ = await self._call_llm_cached(
                                role="primary",
                                system_prompt=phases.DEEP_READ_SYSTEM,
                                user_prompt=phases.deep_read_prompt(
                                    state, url, title, sanitized_content
                                ),
                                phase_key="deep_read",
                                max_tokens=1024, state=state)
                            extraction = extract_json(raw_extraction)
                            matching_result["summary"] = extraction.get("summary", "").strip()
                            matching_result["key_facts"] = safe_list(extraction.get("key_facts"))
                            matching_result["relevant_quotes"] = safe_list(extraction.get("relevant_quotes"))
                            matching_result["extraction_success"] = True
                            self._log("DEEP_READ", f"Extracted summary for: {title}", state)
                        except ParseError as exc:
                            self._log("DEEP_READ", f"Extraction parse error for {url}: {exc}", state)
                            # Fail-soft: use raw content as summary
                            matching_result["summary"] = scraped.get("content", "")[:TRUNCATION.CONTENT]
                            matching_result["key_facts"] = []
                            matching_result["relevant_quotes"] = []
                            matching_result["extraction_success"] = False
                        except Exception as exc:
                            self._log("DEEP_READ", f"Extraction failed for {url}: {exc}", state)
                            matching_result["summary"] = scraped.get("content", "")[:TRUNCATION.CONTENT]
                            matching_result["key_facts"] = []
                            matching_result["relevant_quotes"] = []
                            matching_result["extraction_success"] = False
                    else:
                        # Legacy path: no LLM extraction
                        matching_result["summary"] = scraped.get("content", "")[:TRUNCATION.CONTENT]
                        matching_result["key_facts"] = []
                        matching_result["relevant_quotes"] = []
                        matching_result["extraction_success"] = False
                else:
                    self._log("DEEP_READ", f"Failed to scrape {url}: {scraped.get('error')}", state)
                    # Shallow-read fallback using title + snippet
                    if use_llm_extraction:
                        try:
                            snippet = sanitize_for_prompt(matching_result.get("snippet", ""))[0]
                            raw_fallback, _ = await self._call_llm_cached(
                                role="primary",
                                phase_key="deep_read",
                                system_prompt=phases.SHALLOW_READ_SYSTEM,
                                user_prompt=phases.shallow_read_prompt(state, url, title, snippet),
                                max_tokens=512, state=state)
                            fallback = extract_json(raw_fallback)
                            matching_result["summary"] = fallback.get("summary", "").strip()
                            matching_result["key_facts"] = safe_list(fallback.get("key_facts"))
                            matching_result["relevant_quotes"] = safe_list(fallback.get("relevant_quotes"))
                            matching_result["extraction_success"] = False
                        except Exception as exc:
                            self._log("DEEP_READ", f"Shallow read fallback failed for {url}: {exc}", state)
                            matching_result["summary"] = f"(Scrape failed: {scraped.get('error')})"
                            matching_result["key_facts"] = []
                            matching_result["relevant_quotes"] = []
                            matching_result["extraction_success"] = False
                    else:
                        matching_result["summary"] = f"(Scrape failed: {scraped.get('error')})"
                        matching_result["key_facts"] = []
                        matching_result["relevant_quotes"] = []
                        matching_result["extraction_success"] = False
            
            self._log("DEEP_READ", "Deep read complete.", state)
            
        except Exception as e:
            self._log("DEEP_READ", f"Deep read failed: {e}", state)
            state.errors.append(f"Deep read failed: {e}")

    def _validate_evidence_coverage(self, state: PipelineState) -> None:
        """
        Light-weight cross-phase validation: ensure that uncertain assumptions
        have at least some extracted evidence in vetted_context.
        """
        if not state.decomposition:
            return
        
        # Handle both dict (raw LLM output) and Decomposition dataclass
        if isinstance(state.decomposition, dict):
            assumptions = state.decomposition.get("assumptions", [])
        else:
            assumptions = [
                {"text": a.text, "label": a.label.value}
                for a in (state.decomposition.assumptions or [])
            ]
        
        uncertain = [a for a in assumptions if a.get("label") in ("HYPOTHESIS", "UNKNOWN")]
        if not uncertain:
            return
        
        summaries = [
            vc for vc in (state.vetted_context or [])
            if (vc.get("summary") or "").strip() and vc.get("summary") != "INSUFFICIENT"
        ]
        
        if not summaries:
            self._log(
                "VALIDATION",
                f"No extracted evidence for {len(uncertain)} uncertain assumption(s). "
                "Proceeding with low-evidence synthesis.",
                state,
            )

    async def _phase_synthesis(self, state: PipelineState):
        self._log("SYNTHESIS", "Synthesizing final solution...", state)
        # TOKEN OPTIMIZATION: Use synthesis-specific token budget + caching (highest budget)
        lang_instruction = phases.get_language_instruction(state)
        system_prompt = f"{lang_instruction}\n\n{phases.SYNTHESIS_SYSTEM}"
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

    # --- MULTI-PERSPECTIVE & ITERATIVE PHASES ---
    async def _phase_2_perspectives(self, state: PipelineState, use_reflexion: bool = False):
        self._log("PHASE-2", "Running multi-perspective analysis...", state)

        _PERSPECTIVE_HALLUCINATION_KEYWORDS = {"greek text", "greek characters", "parsing errors", "encoding issues", "unicode problems"}

        def _is_perspective_hallucinated(candidate: SolutionCandidate) -> bool:
            if state.language != "English":
                return False
            text = f"{candidate.content} {' '.join(candidate.key_insights)}".lower()
            return any(kw in text for kw in _PERSPECTIVE_HALLUCINATION_KEYWORDS)

        async def _get_perspective(p_name: str):
            p_enum = PerspectiveType(p_name)
            system_prompt = phases.PERSPECTIVE_SYSTEMS.get(p_name)
            # TOKEN OPTIMIZATION: Use phase-aware context with aggressive compression
            user_prompt = phases.perspective_prompt(state, p_name)
            # TOKEN OPTIMIZATION: Use perspective-specific token budget + caching
            raw, _ = await self._call_llm_cached(
                role=p_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                state=state,
                max_tokens=get_token_budget(p_name) if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
            )
            data = extract_json(raw)
            # Guard against absent keys: content/key_insights are typed str/list[str] and
            # must not be None — downstream prompt builders slice content and iterate insights.
            core_analysis = data.get("core_analysis") or ""
            if not isinstance(core_analysis, str):
                core_analysis = json.dumps(core_analysis) if isinstance(core_analysis, (dict, list)) else str(core_analysis)
            key_insights = data.get("key_insights") or []
            if not isinstance(key_insights, list):
                key_insights = [str(key_insights)] if key_insights else []
            return SolutionCandidate(
                perspective=p_enum,
                content=core_analysis,
                key_insights=key_insights,
                model_used="",
            )

        def _perspective_name(p) -> str:
            return p.name if hasattr(p, 'name') else str(p)

        tasks = [_get_perspective(_perspective_name(p)) for p in self.perspectives]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            p_name = _perspective_name(self.perspectives[i])
            if isinstance(r, Exception):
                msg = f"Perspective '{p_name}' failed: {r}"
                self._log("PHASE-2", msg, state)
                state.errors.append(msg)
            else:
                if _is_perspective_hallucinated(r):
                    self._log("PHASE-2", f"Filtering hallucinated perspective '{p_name}'; regenerating once.", state)
                    try:
                        replacement = await _get_perspective(p_name)
                        if _is_perspective_hallucinated(replacement):
                            self._log("PHASE-2", f"Replacement for '{p_name}' still hallucinated; keeping with penalty.", state)
                        state.candidates.append(replacement)
                    except Exception as exc:
                        self._log("PHASE-2", f"Failed to regenerate perspective '{p_name}': {exc}", state)
                        state.errors.append(f"Perspective '{p_name}' regeneration failed: {exc}")
                else:
                    state.candidates.append(r)

    async def _phase_3_critique(self, state: PipelineState):
        self._log("PHASE-3", "Critiquing candidates...", state)
        if not state.candidates:
            self._log("PHASE-3", "No candidates to critique. Skipping.", state)
            state.scores = []
            state.top_candidates = []
            return
        # TOKEN OPTIMIZATION: Use scoring-specific token budget + caching
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.CRITIQUE_SYSTEM,
            user_prompt=phases.critique_prompt(state),
            state=state,
            max_tokens=get_token_budget("scoring") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        try:
            data = extract_json(raw)
        except ParseError as exc:
            self._log("PHASE-3", f"Failed to parse critique response: {exc}", state)
            state.errors.append(f"Critique parse error: {exc}")
            data = {}
        state.scores = _parse_critique_scores(data.get("scores", []))
        # Pruning logic and potential recovery path
        for score in state.scores:
            if score.confidence_vs_accuracy_penalty > 5.0: # Threshold for triggering recovery
                candidate_to_check = next((c for c in state.candidates if c.perspective == score.perspective), None)
                if candidate_to_check:
                    self._log("PHASE-3", f"High penalty for {score.perspective}. Triggering recovery path.", state)
                    await self._run_recovery_path(state, candidate_to_check)

        scored_perspectives = {s.perspective: s.total for s in state.scores}
        top_p = sorted(scored_perspectives, key=scored_perspectives.get, reverse=True)[:self.top_k]
        state.top_candidates = [c for c in state.candidates if c.perspective in top_p]

    async def _phase_4_stress_test(self, state: PipelineState):
        self._log("PHASE-4", "Running stress tests...", state)
        # TOKEN OPTIMIZATION: Use stress_testing-specific token budget + caching
        raw, _ = await self._call_llm_cached(
            role="stress_testing",
            system_prompt=phases.STRESS_SYSTEM,
            user_prompt=phases.stress_test_prompt(state),
            state=state,
            max_tokens=get_token_budget("stress_testing") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        try:
            data = extract_json(raw)
        except ParseError as exc:
            self._log("PHASE-4", f"Failed to parse stress test response: {exc}", state)
            state.errors.append(f"Stress test parse error: {exc}")
            data = {}
        # Use ScenarioType.coerce() so that LLM variants ("constraint violation",
        # "constraint-violation") all map to the correct enum member.  Without it,
        # the raw string is stored and any enum-identity check downstream fails.
        _HALLUCINATION_KEYWORDS = {
            "greek", "parsing", "encoding", "json", "invalid text", "missing text",
            "unicode", "charset", "markdown", "truncated output", "length limits",
            "context misinterpretation", "off-topic response", "output format",
            "markdown fence", "json parse error", "model limitation", "token limit",
        }

        def _is_hallucinated(st: dict) -> bool:
            text = f"{st.get('failure_mode', '')} {st.get('scenario', '')}".lower()
            return any(kw in text for kw in _HALLUCINATION_KEYWORDS)

        _stress: list[StressTestResult] = []
        for st in data.get("stress_tests", []):
            try:
                if _is_hallucinated(st):
                    self._log("PHASE-4", f"Filtering hallucinated stress test: {st}", state)
                    continue
                _stress.append(StressTestResult(
                    scenario=ScenarioType.coerce(st.get("scenario", "optimal")),
                    survival_rate=float(st.get("survival_rate") or 0),
                    failure_mode=st.get("failure_mode") or "",
                    recovery_path=st.get("recovery_path") or "",
                ))
            except (ValueError, TypeError) as exc:
                logger.warning("Skipping malformed StressTestResult: %s", exc)
        if not _stress:
            _stress.append(StressTestResult(
                scenario=ScenarioType.OPTIMAL,
                survival_rate=1.0,
                failure_mode="",
                recovery_path="",
            ))
        state.stress_results = _stress

    # --- DEBATE PHASES ---
    async def _phase_debate_opening(self, state: PipelineState):
        self._log("DEBATE", "Round 1: Opening Statements", state)
        async def _get_opening(side: str):
            raw, _ = await self._call_llm_cached(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_OPENING_SYSTEM, user_prompt=phases.debate_opening_prompt(state, side), state=state)
            return extract_json(raw)
        
        results = await asyncio.gather(_get_opening("A"), _get_opening("B"), return_exceptions=True)
        statements = []
        for side, r in zip(["A", "B"], results):
            if isinstance(r, Exception):
                msg = f"Debate opening '{side}' failed: {r}"
                self._log("DEBATE", msg, state)
                state.errors.append(msg)
            else:
                statements.append(r)
        state.debate_rounds.append({"round": 1, "type": "opening", "statements": statements})

    async def _phase_debate_rebuttal(self, state: PipelineState):
        self._log("DEBATE", "Round 2: Rebuttals", state)
        # Guard: opening phase may have produced fewer than 2 statements if one side failed.
        # Abort the rebuttal round rather than crash with IndexError.
        opening_statements = state.debate_rounds[0]['statements'] if state.debate_rounds else []
        if len(opening_statements) < 2:
            msg = f"Debate rebuttal skipped: only {len(opening_statements)} opening statement(s) available"
            self._log("DEBATE", msg, state)
            state.errors.append(msg)
            return
        statement_a = opening_statements[0].get('content', '')
        statement_b = opening_statements[1].get('content', '')
        async def _get_rebuttal(side: str, opponent_statement: str):
            raw, _ = await self._call_llm_cached(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_REBUTTAL_SYSTEM, user_prompt=phases.debate_rebuttal_prompt(state, side, opponent_statement), state=state)
            return extract_json(raw)
        
        results = await asyncio.gather(_get_rebuttal("A", statement_b), _get_rebuttal("B", statement_a), return_exceptions=True)
        rebuttals = []
        for side, r in zip(["A", "B"], results):
            if isinstance(r, Exception):
                msg = f"Debate rebuttal '{side}' failed: {r}"
                self._log("DEBATE", msg, state)
                state.errors.append(msg)
            else:
                rebuttals.append(r)
        state.debate_rounds.append({"round": 2, "type": "rebuttal", "rebuttals": rebuttals})

    async def _phase_debate_judge(self, state: PipelineState):
        self._log("DEBATE", "Round 3: Judging", state)
        raw, _ = await self._call_llm_cached(role="systemic", system_prompt=phases.DEBATE_JUDGE_SYSTEM, user_prompt=phases.debate_judge_prompt(state), state=state)
        data = extract_json(raw)
        state.scores = _parse_critique_scores(data.get("scores", []))  # Store judge's scores
        # This data can then be used by the final synthesis step

    # --- Other method-specific phase implementations would go here (Jury, Research, etc.) ---
    # They would follow the same pattern: call the correct prompt from `phases.py`
    # with a minimal context, and parse the result into the `state` object.
    async def _phase_research_web_search(self, state: PipelineState):
        self._log("RESEARCH", "Starting deep iterative research...", state)
        max_iterations = 3
        current_knowledge = []
        
        try:
            client = await get_discovery_client()
        except Exception as e:
            self._log("RESEARCH", f"Failed to initialize discovery client: {e}", state)
            state.errors.append(f"Research: Client init failed: {e}")
            return

        for i in range(1, max_iterations + 1):
            self._log("RESEARCH", f"Iteration {i}/{max_iterations}: Planning searches...", state)
            raw, _ = await self._call_llm_cached(
                role="primary",
                phase_key="research",
                system_prompt=phases.DEEP_RESEARCH_SYSTEM,
                user_prompt=phases.deep_research_prompt(state, current_knowledge, i, max_iterations),
                state=state)
            try:
                data = extract_json(raw)
            except ParseError as e:
                self._log("RESEARCH", f"Failed to parse research plan: {e}", state)
                break
                
            action = data.get("action")
            reasoning = data.get("reasoning", "")
            self._log("RESEARCH", f"Action: {action}. Reason: {reasoning}", state)
            
            if action == "done" or i == max_iterations:
                break
                
            # Same guard as context-vetting: LLM may return a string, not a list.
            _raw_q = data.get("queries", [])
            queries = _raw_q[:TRUNCATION.KEY_INSIGHTS] if isinstance(_raw_q, list) else []
            if not queries:
                break
                
            self._log("RESEARCH", f"Executing queries: {queries}", state)
            
            # Execute queries concurrently with query enrichment
            enriched_queries = [self._enrich_query(q, state.problem) for q in queries]
            async def _search(q):
                try:
                    return await client.search(q, num_results=3, domain=self.domain)
                except Exception as exc:
                    self._log("RESEARCH", f"Query failed '{q}': {exc}", state)
                    return []
                    
            results_nested = await asyncio.gather(*[_search(q) for q in enriched_queries])
            
            # Flatten and deduplicate
            new_results = []
            seen_urls = {res.get("url") for res in current_knowledge}
            
            for res_list in results_nested:
                for res in res_list:
                    url = res.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        new_results.append(res)
            
            self._log("RESEARCH", f"Found {len(new_results)} new unique sources.", state)
            current_knowledge.extend(new_results)
            
        state.web_discovery_results = current_knowledge
        self._log("RESEARCH", f"Deep research complete. Total sources: {len(state.web_discovery_results)}", state)
    async def _phase_jury_generate(self, state: PipelineState):
        self._log("JURY", "Generating independent solutions...", state)
        
        async def _get_generator(gen_id: str):
            raw, _ = await self._call_llm_cached(
                role=gen_id,
                system_prompt=phases.JURY_GENERATOR_SYSTEM,
                user_prompt=phases.jury_generator_prompt(state, gen_id), state=state)
            data = extract_json(raw)
            return GenerationCandidate(**data, model_used="")

        # Extract generator roles
        gen_roles = [cfg.role for name, cfg in self.phase_configs.items() if "generator" in name]
        if not gen_roles: # Fallback if config is minimal
            gen_roles = ["generator_1", "generator_2", "generator_3"]
            
        tasks = [_get_generator(role) for role in gen_roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                role = gen_roles[i]
                msg = f"Jury generator '{role}' failed: {r}"
                self._log("JURY", msg, state)
                state.errors.append(msg)
            else:
                state.generation_candidates.append(r)

    async def _phase_jury_critique(self, state: PipelineState):
        self._log("JURY_CRITIQUE", "Jury critiquing candidates...", state)
        
        async def _get_jury_critique(critic_id: str):
            raw, _ = await self._call_llm_cached(
                role=critic_id,
                system_prompt=phases.JURY_CRITIC_SYSTEM,
                user_prompt=phases.jury_critic_prompt(state),
                state=state) # Critics should be focused
            data = extract_json(raw)
            return CriticScore(**data)

        # Get critics from preset (simplified for now, assume roles exist)
        critic_roles = [cfg.role for name, cfg in self.phase_configs.items() if "critic" in name]
        if not critic_roles:
            critic_roles = ["critic_1", "critic_2", "critic_3"]
            
        tasks = [_get_jury_critique(role) for role in critic_roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                role = critic_roles[i]
                msg = f"Jury critic '{role}' failed: {r}"
                self._log("JURY_CRITIQUE", msg, state)
                state.errors.append(msg)
            else:
                state.critic_scores.append(r)

        # After critiques, identify if any candidates need recovery path
        for critic_score in state.critic_scores:
            for gen_id, scores in critic_score.candidate_scores.items():
                # Check the confidence_vs_accuracy_penalty
                if scores.get("confidence_vs_accuracy_penalty", 0.0) > 5.0: # Threshold
                    candidate_to_check = next((gc for gc in state.generation_candidates if gc.generator_id == gen_id), None)
                    if candidate_to_check:
                        self._log("JURY_CRITIQUE", f"High penalty for Jury candidate {gen_id}. Triggering recovery path.", state)
                        await self._run_recovery_path(state, candidate_to_check)

    async def _phase_jury_verify_and_meta_eval(self, state: PipelineState):
        self._log("JURY", "Verifying claims and meta-evaluating critics...", state)

        def _parse_verification_results(raw_list: list[dict]) -> list[VerificationResult]:
            out: list[VerificationResult] = []
            for v in raw_list:
                try:
                    verdict_raw = v.get("verdict", "UNKNOWN")
                    verdict = ClaimLabel(verdict_raw) if verdict_raw in [e.value for e in ClaimLabel] else ClaimLabel.UNKNOWN
                    out.append(VerificationResult(
                        claim=str(v.get("claim", "")),
                        source_generator=str(v.get("source_generator", "")),
                        verdict=verdict,
                        evidence=str(v.get("evidence", "")),
                        confidence=float(v.get("confidence") or 0.0),
                    ))
                except (KeyError, ValueError, TypeError) as exc:
                    logger.warning("Skipping malformed VerificationResult entry: %s", exc)
            return out

        def _parse_meta_evaluation(data: dict) -> MetaEvaluation:
            try:
                return MetaEvaluation(
                    critic_reliability=data.get("critic_reliability", {}),
                    bias_analysis=data.get("bias_analysis", {}),
                    agreement_rate=float(data.get("agreement_rate") or 0.0),
                    most_reliable_critic=str(data.get("most_reliable_critic", "")),
                    least_reliable_critic=str(data.get("least_reliable_critic", "")),
                    meta_insight=str(data.get("meta_insight", "")),
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Malformed MetaEvaluation response: %s", exc)
                return MetaEvaluation(
                    critic_reliability={},
                    bias_analysis={},
                    agreement_rate=0.0,
                    most_reliable_critic="",
                    least_reliable_critic="",
                    meta_insight="",
                )

        # 1. Verification
        raw_v, _ = await self._call_llm_cached(
            role="verifier",
            system_prompt=phases.JURY_VERIFIER_SYSTEM,
            user_prompt=phases.jury_verifier_prompt(state), state=state)
        v_data = extract_json(raw_v)
        state.verification_results = _parse_verification_results(v_data.get("verifications", []))

        # 2. Meta Evaluation
        raw_m, _ = await self._call_llm_cached(
            role="meta_evaluator",
            system_prompt=phases.JURY_META_EVAL_SYSTEM,
            user_prompt=phases.jury_meta_eval_prompt(state), state=state)
        m_data = extract_json(raw_m)
        state.meta_evaluation = _parse_meta_evaluation(m_data)
    async def _phase_scientific_hypothesize(self, state: PipelineState):
        self._log("SCIENTIFIC", "Generating hypotheses...", state)
        raw, _ = await self._call_llm_cached(
            role="primary",
            system_prompt=phases.SCIENTIFIC_HYPOTHESIS_SYSTEM,
            user_prompt=phases.scientific_hypothesis_prompt(state), state=state)
        data = extract_json(raw)
        state.scientific_state["hypotheses"] = data.get("hypotheses", [])

    async def _phase_scientific_test(self, state: PipelineState):
        self._log("SCIENTIFIC", "Running falsification tests...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.SCIENTIFIC_TEST_SYSTEM,
            user_prompt=phases.scientific_test_prompt(state), state=state)
        data = extract_json(raw)
        state.scientific_state["test_results"] = data.get("test_results", [])
        # A1: Inline Bayesian posterior update — compute posterior for each hypothesis
        hypotheses = state.scientific_state.get("hypotheses", [])
        test_results = state.scientific_state.get("test_results", [])
        for hyp in hypotheses:
            hyp_id = hyp.get("id", "")
            tests = [t for t in test_results if t.get("hypothesis_id") == hyp_id]
            supported = sum(1 for t in tests if t.get("result") == "SUPPORTED")
            hyp["posterior_probability"] = round(supported / max(len(tests), 1), 2)
        state.scientific_state["hypotheses"] = hypotheses
    async def _phase_socratic_question(self, state: PipelineState):
        self._log("SOCRATIC", "Generating Socratic questions...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",  # A4: questioner uses destructive role for genuine challenge
            system_prompt=phases.SOCRATIC_QUESTION_SYSTEM,
            user_prompt=phases.socratic_question_prompt(state), state=state)
        data = extract_json(raw)
        state.socratic_state["questions"] = data.get("questions", [])

    async def _phase_socratic_answer(self, state: PipelineState):
        self._log("SOCRATIC", "Attempting Dialectic answers...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",  # A4: answerer uses constructive role — genuinely different model
            system_prompt=phases.SOCRATIC_ANSWER_SYSTEM,
            user_prompt=phases.socratic_answer_prompt(state), state=state)
        data = extract_json(raw)
        state.socratic_state["answers"] = data.get("answers", [])

    # ─────────────────────────────────────────────────────────────────
    # Track A: Existing Method Improvements
    # ─────────────────────────────────────────────────────────────────

    async def _phase_debate_cross_examine(self, state: PipelineState):
        """A5: Cross-examination — each side challenges the other's specific claims."""
        self._log("DEBATE", "Running cross-examination...", state)
        side_a_claims = []
        side_b_claims = []
        for rd in state.debate_rounds:
            if rd.get("phase") == "rebuttal":
                if rd.get("side") == "A":
                    side_a_claims.append(rd.get("content", "")[:TRUNCATION.CONTENT])
                elif rd.get("side") == "B":
                    side_b_claims.append(rd.get("content", "")[:TRUNCATION.CONTENT])
        tasks = [
            self._call_llm_cached(
                role="constructive",
                system_prompt=phases.DEBATE_CROSS_SYSTEM,
                user_prompt=phases.debate_cross_examine_prompt(state, "A", side_b_claims), state=state),
            self._call_llm_cached(
                role="destructive",
                system_prompt=phases.DEBATE_CROSS_SYSTEM,
                user_prompt=phases.debate_cross_examine_prompt(state, "B", side_a_claims), state=state),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                self._log("DEBATE", f"Cross-examine error: {r}", state)
                continue
            raw, _ = r
            data = extract_json(raw)
            state.debate_rounds.append({
                "phase": "cross_examine",
                "side": data.get("side", "?"),
                "challenges": data.get("challenges", []),
            })

    async def _phase_jury_weighted_ranking(self, state: PipelineState):
        """A3: Rerank generators by critic reliability weights."""
        self._log("JURY", "Computing reliability-weighted ranking...", state)
        reliability: dict[str, float] = {}
        if state.meta_evaluation:
            reliability = state.meta_evaluation.critic_reliability or {}
        generator_scores: dict[str, float] = {}
        for crit_score in state.scores:
            crit_id = (
                crit_score.perspective.value
                if hasattr(crit_score.perspective, "value")
                else str(crit_score.perspective)
            )
            weight = reliability.get(crit_id, 1.0)
            for cand in state.candidates:
                gen_id = (
                    cand.perspective.value
                    if hasattr(cand.perspective, "value")
                    else str(cand.perspective)
                )
                generator_scores[gen_id] = generator_scores.get(gen_id, 0.0) + (
                    crit_score.logical_consistency * weight
                )
        state.jury_weighted_ranking = sorted(
            generator_scores.keys(),
            key=lambda gid: generator_scores[gid],
            reverse=True,
        )
        self._log("JURY", f"Weighted ranking: {state.jury_weighted_ranking}", state)

    # ─────────────────────────────────────────────────────────────────
    # B1: Pre-Mortem Analysis
    # ─────────────────────────────────────────────────────────────────

    async def _run_pre_mortem_pipeline(self, state: PipelineState):
        await self._phase_pre_mortem_failure(state)
        await self._phase_pre_mortem_backtrack(state)
        await self._phase_pre_mortem_signals(state)
        await self._phase_pre_mortem_redesign(state)

    async def _phase_pre_mortem_failure(self, state: PipelineState):
        self._log("PRE-MORTEM", "Constructing failure narrative...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.PRE_MORTEM_FAILURE_SYSTEM,
            user_prompt=phases.pre_mortem_failure_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["failure_narrative"] = data

    async def _phase_pre_mortem_backtrack(self, state: PipelineState):
        self._log("PRE-MORTEM", "Identifying root cause pivot point...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.PRE_MORTEM_BACKTRACK_SYSTEM,
            user_prompt=phases.pre_mortem_backtrack_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["root_cause"] = data

    async def _phase_pre_mortem_signals(self, state: PipelineState):
        self._log("PRE-MORTEM", "Identifying early warning signals...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.PRE_MORTEM_SIGNALS_SYSTEM,
            user_prompt=phases.pre_mortem_signals_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["early_signals"] = data.get("early_signals", [])
        state.pre_mortem_state["monitoring_cadence"] = data.get("monitoring_cadence", "")

    async def _phase_pre_mortem_redesign(self, state: PipelineState):
        self._log("PRE-MORTEM", "Generating hardened redesign...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.PRE_MORTEM_REDESIGN_SYSTEM,
            user_prompt=phases.pre_mortem_redesign_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["hardened_solution"] = data.get("hardened_solution", "")
        state.pre_mortem_state["safeguards"] = data.get("safeguards", [])
        state.pre_mortem_state["checkpoints"] = data.get("checkpoints", [])
        state.pre_mortem_state["rollback_plan"] = data.get("rollback_plan", "")

    # ─────────────────────────────────────────────────────────────────
    # B2: Bayesian Reasoning
    # ─────────────────────────────────────────────────────────────────

    async def _run_bayesian_pipeline(self, state: PipelineState):
        await self._phase_bayesian_priors(state)
        await self._phase_bayesian_likelihood(state)
        await self._phase_bayesian_posterior(state)
        await self._phase_bayesian_sensitivity(state)

    async def _phase_bayesian_priors(self, state: PipelineState):
        self._log("BAYESIAN", "Eliciting prior distributions...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",
            system_prompt=phases.BAYESIAN_PRIOR_SYSTEM,
            user_prompt=phases.bayesian_prior_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["hypotheses_with_priors"] = data.get("hypotheses", [])

    async def _phase_bayesian_likelihood(self, state: PipelineState):
        self._log("BAYESIAN", "Assessing likelihoods...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.BAYESIAN_LIKELIHOOD_SYSTEM,
            user_prompt=phases.bayesian_likelihood_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["evidence_likelihoods"] = data.get("likelihoods", [])
        state.bayesian_state["observations"] = data.get("observations", [])

    async def _phase_bayesian_posterior(self, state: PipelineState):
        self._log("BAYESIAN", "Computing posteriors...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.BAYESIAN_POSTERIOR_SYSTEM,
            user_prompt=phases.bayesian_posterior_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["posteriors"] = data.get("posteriors", [])
        state.bayesian_state["most_probable"] = data.get("most_probable", "")

    async def _phase_bayesian_sensitivity(self, state: PipelineState):
        self._log("BAYESIAN", "Running sensitivity analysis...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.BAYESIAN_SENSITIVITY_SYSTEM,
            user_prompt=phases.bayesian_sensitivity_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["sensitivity_results"] = data.get("sensitivity_analysis", [])
        state.bayesian_state["most_sensitive_assumption"] = data.get("most_sensitive_assumption", "")

    # ─────────────────────────────────────────────────────────────────
    # B3: Dialectical Reasoning (Hegelian Aufhebung)
    # ─────────────────────────────────────────────────────────────────

    async def _run_dialectical_pipeline(self, state: PipelineState):
        await self._phase_dialectical_thesis(state)
        await self._phase_dialectical_antithesis(state)
        await self._phase_dialectical_contradictions(state)
        await self._phase_dialectical_aufhebung(state)

    async def _phase_dialectical_thesis(self, state: PipelineState):
        self._log("DIALECTICAL", "Formulating thesis...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",
            system_prompt=phases.DIALECTICAL_THESIS_SYSTEM,
            user_prompt=phases.dialectical_thesis_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["thesis"] = data.get("thesis", "")
        state.dialectical_state["key_commitments"] = data.get("key_commitments", [])
        state.dialectical_state["thesis_assumptions"] = data.get("assumptions", [])

    async def _phase_dialectical_antithesis(self, state: PipelineState):
        self._log("DIALECTICAL", "Formulating antithesis...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.DIALECTICAL_ANTITHESIS_SYSTEM,
            user_prompt=phases.dialectical_antithesis_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["antithesis"] = data.get("antithesis", "")
        state.dialectical_state["contradictions_exposed"] = data.get("contradictions_exposed", [])
        state.dialectical_state["negated_commitments"] = data.get("negated_commitments", [])

    async def _phase_dialectical_contradictions(self, state: PipelineState):
        self._log("DIALECTICAL", "Analyzing contradictions...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.DIALECTICAL_CONTRADICTIONS_SYSTEM,
            user_prompt=phases.dialectical_contradictions_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["irreconcilable"] = data.get("irreconcilable", [])
        state.dialectical_state["compatible"] = data.get("compatible", [])
        state.dialectical_state["synthesis_candidates"] = data.get("synthesis_candidates", [])

    async def _phase_dialectical_aufhebung(self, state: PipelineState):
        self._log("DIALECTICAL", "Formulating Aufhebung...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.DIALECTICAL_AUFHEBUNG_SYSTEM,
            user_prompt=phases.dialectical_aufhebung_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["aufhebung"] = data.get("aufhebung", "")
        state.dialectical_state["preserved_from_thesis"] = data.get("preserved_from_thesis", [])
        state.dialectical_state["preserved_from_antithesis"] = data.get("preserved_from_antithesis", [])
        state.dialectical_state["transcended"] = data.get("transcended", "")
        state.dialectical_state["new_insights"] = data.get("new_insights", [])

    # ─────────────────────────────────────────────────────────────────
    # B4: Analogical Reasoning (Structure-Mapping Theory, Gentner 1983)
    # ─────────────────────────────────────────────────────────────────

    async def _run_analogical_pipeline(self, state: PipelineState):
        await self._phase_analogical_abstraction(state)
        await self._phase_analogical_domain_search(state)
        if not state.analogical_state.get("source_domains"):
            state.errors.append("Analogical: domain search returned no source domains; skipping mapping and transfer.")
            return
        await self._phase_analogical_mapping(state)
        await self._phase_analogical_transfer(state)

    async def _phase_analogical_abstraction(self, state: PipelineState):
        self._log("ANALOGICAL", "Extracting abstract problem structure...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_ABSTRACTION_SYSTEM,
            user_prompt=phases.analogical_abstraction_prompt(state), state=state)
        data = extract_json(raw)
        state.analogical_state["abstract_structure"] = data.get("abstract_structure", "") or ""
        state.analogical_state["constraints"] = data.get("constraints", [])
        state.analogical_state["objectives"] = data.get("objectives", [])
        state.analogical_state["actors"] = data.get("actors", [])
        state.analogical_state["core_dynamics"] = data.get("core_dynamics", [])
        state.analogical_state["structural_type"] = data.get("structural_type", "") or ""

    async def _phase_analogical_domain_search(self, state: PipelineState):
        self._log("ANALOGICAL", "Searching for isomorphic source domains...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_DOMAIN_SEARCH_SYSTEM,
            user_prompt=phases.analogical_domain_search_prompt(state), state=state)
        data = extract_json(raw)
        _raw_domains = data.get("source_domains", [])
        state.analogical_state["source_domains"] = _raw_domains if isinstance(_raw_domains, list) else []

    async def _phase_analogical_mapping(self, state: PipelineState):
        self._log("ANALOGICAL", "Mapping source domain elements to target problem...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_MAPPING_SYSTEM,
            user_prompt=phases.analogical_mapping_prompt(state), state=state)
        data = extract_json(raw)
        _raw_mappings = data.get("analogy_mappings", [])
        state.analogical_state["analogy_mappings"] = _raw_mappings if isinstance(_raw_mappings, list) else []
        state.analogical_state["unmapped_elements"] = data.get("unmapped_elements", [])
        state.analogical_state["mapping_quality"] = data.get("mapping_quality", "") or ""

    async def _phase_analogical_transfer(self, state: PipelineState):
        self._log("ANALOGICAL", "Transferring and adapting solution from source domain...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.ANALOGICAL_TRANSFER_SYSTEM,
            user_prompt=phases.analogical_transfer_prompt(state), state=state)
        data = extract_json(raw)
        state.analogical_state["transferred_solution"] = data.get("transferred_solution", "") or ""
        state.analogical_state["transfer_steps"] = data.get("transfer_steps", [])
        state.analogical_state["adaptations_required"] = data.get("adaptations_required", [])
        state.analogical_state["broken_analogies"] = data.get("broken_analogies", [])
        state.analogical_state["transfer_confidence"] = data.get("confidence", "") or ""
        state.analogical_state["caveats"] = data.get("caveats", [])

    # ─────── B5: Delphi Method ───────

    async def _run_delphi_pipeline(self, state: PipelineState):
        await self._phase_delphi_round1(state)
        await self._phase_delphi_aggregation(state)
        await self._phase_delphi_round2(state)
        await self._phase_delphi_convergence(state)
        await self._phase_delphi_dissent(state)

    async def _phase_delphi_round1(self, state: PipelineState):
        self._log("DELPHI", "Round 1: Independent expert estimates...", state)
        tasks = [
            self._call_llm_cached(
                role=f"expert_{i+1}",
                system_prompt=phases.DELPHI_EXPERT_SYSTEM,
                user_prompt=phases.delphi_round1_prompt(state, expert_num=i+1), state=state)
            for i in range(4)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        estimates = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                state.errors.append(f"Delphi: Expert {i+1} Round 1 failed: {result}")
                continue
            raw, _ = result
            try:
                data = extract_json(raw)
            except ParseError as e:
                state.errors.append(f"Delphi: Expert {i+1} Round 1 parse error: {e}")
                continue
            if not isinstance(data, dict):
                state.errors.append(f"Delphi: Expert {i+1} Round 1 returned non-dict, skipping.")
                continue
            data["expert_id"] = f"expert_{i+1}"
            estimates.append(data)
        state.delphi_state["round_1_estimates"] = estimates

    async def _phase_delphi_aggregation(self, state: PipelineState):
        """Aggregate round 1 estimates: compute median, IQR, identify outlier."""
        self._log("DELPHI", "Aggregating expert estimates...", state)
        estimates = state.delphi_state.get("round_1_estimates", [])
        if not estimates:
            state.errors.append("Delphi: No estimates to aggregate.")
            return
        # Extract numeric values
        values = []
        for e in estimates:
            val = e.get("estimate_value")
            if isinstance(val, (int, float)):
                values.append(val)
        if len(values) >= 2:
            values_sorted = sorted(values)
            n = len(values_sorted)
            mid = n // 2
            median = (values_sorted[mid-1] + values_sorted[mid]) / 2 if n % 2 == 0 else float(values_sorted[mid])
            q1 = values_sorted[n//4] if n > 2 else values_sorted[0]
            q3 = values_sorted[3*n//4] if n > 2 else values_sorted[-1]
            iqr = q3 - q1
            # Identify outlier (furthest from median)
            outlier_id = None
            max_dist = -1.0
            for e in estimates:
                val = e.get("estimate_value")
                if isinstance(val, (int, float)):
                    dist = abs(val - median)
                    if dist > max_dist:
                        max_dist = dist
                        outlier_id = e.get("expert_id")
            state.delphi_state["aggregated_stats"] = {
                "median": median,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "outlier_expert": outlier_id,
                "outlier_distance": max_dist if max_dist >= 0 else None,
                "n_estimates": len(values),
            }
        else:
            # Fallback: use LLM to aggregate qualitative estimates
            raw, _ = await self._call_llm_cached(
                role="synthesis",
                system_prompt=phases.DELPHI_AGGREGATION_SYSTEM,
                user_prompt=phases.delphi_aggregation_prompt(state), state=state)
            data = extract_json(raw)
            state.delphi_state["aggregated_stats"] = data

    async def _phase_delphi_round2(self, state: PipelineState):
        self._log("DELPHI", "Round 2: Experts revise with anonymous aggregate...", state)
        estimates = state.delphi_state.get("round_1_estimates", [])
        # Iterate actual expert IDs to handle any R1 failures correctly
        expert_ids = [e.get("expert_id", f"expert_{i+1}") for i, e in enumerate(estimates)]
        tasks = [
            self._call_llm_cached(
                role=eid,
                system_prompt=phases.DELPHI_REVISION_SYSTEM,
                user_prompt=phases.delphi_round2_prompt(state, expert_id=eid), state=state)
            for eid in expert_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        revised = []
        for eid, result in zip(expert_ids, results):
            if isinstance(result, Exception):
                state.errors.append(f"Delphi: {eid} Round 2 failed: {result}")
                continue
            raw, _ = result
            try:
                data = extract_json(raw)
            except ParseError as e:
                state.errors.append(f"Delphi: {eid} Round 2 parse error: {e}")
                continue
            if not isinstance(data, dict):
                state.errors.append(f"Delphi: {eid} Round 2 returned non-dict, skipping.")
                continue
            data["expert_id"] = eid
            revised.append(data)
        state.delphi_state["round_2_estimates"] = revised

    async def _phase_delphi_convergence(self, state: PipelineState):
        self._log("DELPHI", "Checking convergence...", state)
        estimates = state.delphi_state.get("round_2_estimates", [])
        values = [e.get("revised_estimate") for e in estimates if isinstance(e.get("revised_estimate"), (int, float))]
        if len(values) >= 2:
            values_sorted = sorted(values)
            n = len(values_sorted)
            mid = n // 2
            median = (values_sorted[mid-1] + values_sorted[mid]) / 2 if n % 2 == 0 else float(values_sorted[mid])
            q1 = values_sorted[n//4] if n > 2 else values_sorted[0]
            q3 = values_sorted[3*n//4] if n > 2 else values_sorted[-1]
            iqr = q3 - q1
            # Converged if IQR < 20% of |median| (or median is 0 and IQR is 0)
            converged = (iqr / abs(median) < 0.2) if median != 0 else (iqr == 0)
            state.delphi_state["converged"] = converged
            state.delphi_state["consensus"] = {
                "median": median,
                "iqr": iqr,
                "converged": converged,
            }
        else:
            # Qualitative convergence via LLM
            raw, _ = await self._call_llm_cached(
                role="synthesis",
                system_prompt=phases.DELPHI_CONVERGENCE_SYSTEM,
                user_prompt=phases.delphi_convergence_prompt(state), state=state)
            data = extract_json(raw)
            state.delphi_state["converged"] = data.get("converged", False)
            state.delphi_state["consensus"] = data

    async def _phase_delphi_dissent(self, state: PipelineState):
        self._log("DELPHI", "Capturing minority dissent...", state)
        stats = state.delphi_state.get("aggregated_stats", {})
        outlier = stats.get("outlier_expert", "expert_1")
        # Map outlier string like "expert_2" to role
        role = outlier if outlier in ("expert_1", "expert_2", "expert_3", "expert_4") else "expert_1"
        raw, _ = await self._call_llm_cached(
            role=role,
            system_prompt=phases.DELPHI_DISSENT_SYSTEM,
            user_prompt=phases.delphi_dissent_prompt(state), state=state)
        data = extract_json(raw)
        state.delphi_state["dissent"] = data

    async def _run_recovery_path(self, state: PipelineState, candidate_to_verify: SolutionCandidate | GenerationCandidate) -> None:
        """Executes a cross-verification path for a potentially problematic candidate."""
        self._log("RECOVERY", f"Initiating recovery path for candidate: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}", state)
        
        try:
            raw_verification, _ = await self._call_llm_cached(
                role="recovery_path",
                system_prompt=phases.CROSS_VERIFICATION_SYSTEM,
                user_prompt=phases.cross_verification_prompt(state, candidate_solution=asdict(candidate_to_verify)),
                # verification uses recovery_path temperature from registry
                max_tokens=1024, state=state)
            verification_data = extract_json(raw_verification)
            if verification_data.get("verification_findings"):
                self._log("RECOVERY", f"Cross-verification found issues for candidate. Findings: {verification_data['verification_findings'][:TRUNCATION.MEMORY]}", state)
                # Do NOT append to state.errors — recovery findings are diagnostics, not pipeline failures.
            else:
                self._log("RECOVERY", "Cross-verification found no issues.", state)
        except ParseError as e:
            self._log("RECOVERY", f"Recovery Path: Parse error during verification: {e}", state)
            state.errors.append(f"Recovery Path: Parse error during verification for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        except Exception as e:
            self._log("RECOVERY", f"Recovery Path: Verification failed: {e}", state)
            state.errors.append(f"Recovery Path: Verification failed for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        
        self._log("RECOVERY", "Recovery path complete.", state)
