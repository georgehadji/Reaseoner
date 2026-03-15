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
import time
from dataclasses import asdict
from typing import Any
from models import (PipelineState, SolutionCandidate, CritiqueScore, StressTestResult, 
                GenerationCandidate, CriticScore, VerificationResult, MetaEvaluation,
                ClaimLabel, PerspectiveType, FinalSolution, MetaCognitiveAudit)
from parsing import ParseError, extract_json, safe_list, safe_float
from llm import ProviderRouter
from core import PhaseConfig, make_phase_result, DEFAULT_PERSPECTIVES
from core.search import get_discovery_client # Import for web search
from neuro.server import create_neuro_router # Assuming neuro is an available module
import phases # Refactored phases

logger = logging.getLogger(__name__)

class ARAPipeline:
    """
    Dynamic ARA v2.1 Pipeline Orchestrator.
    Routes execution to method-specific pipelines based on the selected preset.
    """
    _PHASE_CONFIGS: dict[str, PhaseConfig] = {
        # Define base configs...
        "classification": PhaseConfig(role="classification"), "decomposition": PhaseConfig(role="decomposition"),
        "perspective": PhaseConfig(role="primary"), "scoring": PhaseConfig(role="scoring"),
        "stress_testing": PhaseConfig(role="stress_testing"), "synthesis": PhaseConfig(role="synthesis"),
        "generator": PhaseConfig(role="generator_1"), "critic": PhaseConfig(role="critic_1"),
        "verifier": PhaseConfig(role="verifier"), "meta_evaluator": PhaseConfig(role="meta_evaluator"),
        "context_vetting": PhaseConfig(role="context_vetting"), # New role for CoT vetting
        "recovery_path": PhaseConfig(role="recovery_path"), # New role for cross-verification
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
        self.phase_configs = self._PHASE_CONFIGS.copy() # Simplified for brevity
        self.perspectives = list(DEFAULT_PERSPECTIVES)

    def _log(self, phase: str, message: str, state: PipelineState) -> None:
        if self.verbose: logger.info(f"[{phase}] {message}")
        state.log(phase, message)

    def _get_method_from_preset(self) -> str:
        """Determines the reasoning method from the preset name."""
        preset = self.preset_name or ""
        if "debate" in preset: return "debate"
        if "iterative" in preset: return "iterative"
        if "jury" in preset or "orchestrated" in preset: return "jury"
        if "research" in preset: return "research"
        if "scientific" in preset: return "scientific"
        if "socratic" in preset: return "socratic"
        return "multi_perspective" # Default

    async def run(self, problem: str) -> PipelineState:
        """Main entry point. Executes the dynamic pipeline."""
        state = self.initial_state if self.initial_state else PipelineState(problem=problem, preset_name=self.preset_name)
        
        # --- UNIVERSAL START PHASES ---
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

        if method == "debate": await self._run_debate_pipeline(state)
        elif method == "iterative": await self._run_iterative_pipeline(state)
        elif method == "jury": await self._run_jury_pipeline(state)
        elif method == "research": await self._run_research_pipeline(state)
        elif method == "scientific": await self._run_scientific_pipeline(state)
        elif method == "socratic": await self._run_socratic_pipeline(state)
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
        for i in range(MAX_ROUNDS):
            self._log("ITERATIVE", f"Starting round {i+1}/{MAX_ROUNDS}", state)
            await self._phase_2_perspectives(state, use_reflexion=True)
            await self._phase_3_critique(state)
            # Store insights for the next round
            new_memories = [s.steel_man for s in state.scores if s.steel_man]
            state.reflexion_memory.extend(new_memories)
            if i < MAX_ROUNDS - 1: # Don't clear on last round
                state.candidates, state.scores, state.top_candidates = [], [], []

    async def _run_debate_pipeline(self, state: PipelineState):
        await self._phase_debate_opening(state)
        await self._phase_debate_rebuttal(state)
        await self._phase_debate_judge(state)

    async def _run_jury_pipeline(self, state: PipelineState):
        await self._phase_jury_generate(state)
        await self._phase_jury_critique(state)
        await self._phase_jury_verify_and_meta_eval(state)

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
    async def _phase_0_classify(self, state: PipelineState):
        self._log("PHASE-0", "Classifying task...", state)
        # Simplified implementation
        from phases import detect_language
        lang = detect_language(state.problem)
        raw, _ = await self.router.call(
            role="classification",
            system_prompt=phases.CLASSIFICATION_SYSTEM,
            user_prompt=phases.classification_prompt(state.problem, lang)
        )
        data = extract_json(raw)
        state.task_type = data.get("task_type")
        state.language = data.get("language")

    async def _phase_1_decompose(self, state: PipelineState):
        self._log("PHASE-1", "Decomposing problem...", state)
        # Simplified implementation
        raw, _ = await self.router.call(
            role="decomposition",
            system_prompt=phases.DECOMPOSITION_SYSTEM,
            user_prompt=phases.decomposition_prompt(state)
        )
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
            raw_decision, _ = await self.router.call(
                role="primary",
                system_prompt=phases.ITERATIVE_CONTEXT_SYSTEM,
                user_prompt=phases.iterative_context_prompt(state, current_results, i, max_iterations),
                temperature=0.3,
            )
            
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
            
            queries = decision_data.get("queries", [])[:3]
            if not queries:
                break
            
            self._log("VETTING", f"Executing queries: {queries}", state)
            
            # Execute searches concurrently
            async def _search(q: str):
                try:
                    return await client.search(q, num_results=5, source_type=source_type, domain=self.domain)
                except Exception as exc:
                    self._log("VETTING", f"Query failed '{q}': {exc}", state)
                    return []
            
            results_nested = await asyncio.gather(*[_search(q) for q in queries])
            
            # Flatten and deduplicate
            for res_list in results_nested:
                for res in res_list:
                    url = res.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        current_results.append(res)
            
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
            try:
                raw_flags, _ = await self.router.call(
                    role="context_vetting",
                    system_prompt=phases.COT_DETECTION_SYSTEM,
                    user_prompt=phases.cot_detection_prompt(state, retrieved_text),
                    temperature=0.1,
                    max_tokens=512,
                )
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
        Deep Read Phase: Fetch full content from critical sources.
        
        This phase is called after vetting to scrape the full content of the most
        critical sources identified during decomposition or vetting.
        
        Args:
            state: The pipeline state
            max_sources: Maximum number of sources to deep read (default: 3)
        """
        self._log("DEEP_READ", "Starting deep read of critical sources...", state)
        
        # Import here to avoid circular imports
        from scraper import scrape_urls
        
        # Determine which sources need deep reading
        # Priority: sources marked as critical in decomposition, or top results by default
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
        
        try:
            scraped_results = await scrape_urls(sources_to_scrape)
            
            # Add deep content to vetted context
            for scraped in scraped_results:
                if scraped.get("success"):
                    # Find matching result in vetted_context and enhance it
                    for result in state.vetted_context:
                        if result.get("url") == scraped.get("url"):
                            result["deep_content"] = scraped.get("content", "")
                            result["deep_title"] = scraped.get("title", "")
                            self._log("DEEP_READ", f"Successfully scraped: {scraped.get('title', 'Unknown')}", state)
                            break
                else:
                    self._log("DEEP_READ", f"Failed to scrape {scraped.get('url')}: {scraped.get('error')}", state)
            
            self._log("DEEP_READ", "Deep read complete.", state)
            
        except Exception as e:
            self._log("DEEP_READ", f"Deep read failed: {e}", state)
            state.errors.append(f"Deep read failed: {e}")


    async def _phase_synthesis(self, state: PipelineState):
        self._log("SYNTHESIS", "Synthesizing final solution...", state)
        raw, _ = await self.router.call(
            role="synthesis",
            system_prompt=phases.SYNTHESIS_SYSTEM,
            user_prompt=phases.synthesis_prompt(state)
        )
        # Parse the synthesis response
        from parsing import extract_solution_prose, extract_json
        json_data = extract_json(raw) or {}

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

        state.final_solution = FinalSolution(
            core_solution=extract_solution_prose(raw) or json_data.get("core_solution", raw),
            critical_insights=json_data.get("critical_insights", []),
            action_blueprint=json_data.get("action_blueprint", []),
            open_questions=json_data.get("open_questions", []),
            claim_labels=clean_labels,
            meta_audit=MetaCognitiveAudit(
                most_dangerous_assumption=meta_audit_data.get("most_dangerous_assumption", ""),
                dominant_bias=meta_audit_data.get("dominant_bias", ""),
                remaining_uncertainty=meta_audit_data.get("remaining_uncertainty", ""),
                assumption_failure_impact=meta_audit_data.get("assumption_failure_impact", ""),
                non_obvious_insight=meta_audit_data.get("non_obvious_insight", "")
            ),
            sources=json_data.get("sources", [])
        )

    # --- MULTI-PERSPECTIVE & ITERATIVE PHASES ---
    async def _phase_2_perspectives(self, state: PipelineState, use_reflexion: bool = False):
        self._log("PHASE-2", "Running multi-perspective analysis...", state)
        
        async def _get_perspective(p_name: str):
            p_enum = PerspectiveType(p_name)
            system_prompt = phases.PERSPECTIVE_SYSTEMS.get(p_name)
            user_prompt = phases.perspective_prompt(state, p_name)
            raw, _ = await self.router.call(role=p_name, system_prompt=system_prompt, user_prompt=user_prompt)
            data = extract_json(raw)
            # Guard against absent keys: content/key_insights are typed str/list[str] and
            # must not be None — downstream prompt builders slice content and iterate insights.
            return SolutionCandidate(
                perspective=p_enum,
                content=data.get("core_analysis") or "",
                key_insights=data.get("key_insights") or [],
                model_used="",
            )
        
        tasks = [_get_perspective(p.name) for p in self.perspectives]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                p_name = self.perspectives[i].name
                msg = f"Perspective '{p_name}' failed: {r}"
                self._log("PHASE-2", msg, state)
                state.errors.append(msg)
            else:
                state.candidates.append(r)

    async def _phase_3_critique(self, state: PipelineState):
        self._log("PHASE-3", "Critiquing candidates...", state)
        raw, _ = await self.router.call(role="scoring", system_prompt=phases.CRITIQUE_SYSTEM, user_prompt=phases.critique_prompt(state))
        data = extract_json(raw)
        state.scores = [CritiqueScore(**s) for s in data.get("scores", [])]
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
        raw, _ = await self.router.call(role="stress_testing", system_prompt=phases.STRESS_SYSTEM, user_prompt=phases.stress_test_prompt(state))
        data = extract_json(raw)
        state.stress_results = [StressTestResult(**st) for st in data.get("stress_tests", [])]

    # --- DEBATE PHASES ---
    async def _phase_debate_opening(self, state: PipelineState):
        self._log("DEBATE", "Round 1: Opening Statements", state)
        async def _get_opening(side: str):
            raw, _ = await self.router.call(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_OPENING_SYSTEM, user_prompt=phases.debate_opening_prompt(state, side))
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
            raw, _ = await self.router.call(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_REBUTTAL_SYSTEM, user_prompt=phases.debate_rebuttal_prompt(state, side, opponent_statement))
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
        raw, _ = await self.router.call(role="systemic", system_prompt=phases.DEBATE_JUDGE_SYSTEM, user_prompt=phases.debate_judge_prompt(state))
        data = extract_json(raw)
        state.scores = [CritiqueScore(**s) for s in data.get("scores", [])] # Store judge's scores
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
            raw, _ = await self.router.call(
                role="primary",
                system_prompt=phases.DEEP_RESEARCH_SYSTEM,
                user_prompt=phases.deep_research_prompt(state, current_knowledge, i, max_iterations),
                temperature=0.3
            )
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
                
            queries = data.get("queries", [])[:3] # Max 3 queries per iteration
            if not queries:
                break
                
            self._log("RESEARCH", f"Executing queries: {queries}", state)
            
            # Execute queries concurrently
            async def _search(q):
                try:
                    return await client.search(q, num_results=3, domain=self.domain)
                except Exception as exc:
                    self._log("RESEARCH", f"Query failed '{q}': {exc}", state)
                    return []
                    
            results_nested = await asyncio.gather(*[_search(q) for q in queries])
            
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
            raw, _ = await self.router.call(
                role=gen_id,
                system_prompt=phases.JURY_GENERATOR_SYSTEM,
                user_prompt=phases.jury_generator_prompt(state, gen_id)
            )
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
            raw, _ = await self.router.call(
                role=critic_id,
                system_prompt=phases.JURY_CRITIC_SYSTEM,
                user_prompt=phases.jury_critic_prompt(state),
                temperature=0.1 # Critics should be focused
            )
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
        
        # 1. Verification
        raw_v, _ = await self.router.call(
            role="verifier",
            system_prompt=phases.JURY_VERIFIER_SYSTEM,
            user_prompt=phases.jury_verifier_prompt(state)
        )
        v_data = extract_json(raw_v)
        state.verification_results = [VerificationResult(**v) for v in v_data.get("verifications", [])]
        
        # 2. Meta Evaluation
        raw_m, _ = await self.router.call(
            role="meta_evaluator",
            system_prompt=phases.JURY_META_EVAL_SYSTEM,
            user_prompt=phases.jury_meta_eval_prompt(state)
        )
        m_data = extract_json(raw_m)
        state.meta_evaluation = MetaEvaluation(**m_data)
    async def _phase_scientific_hypothesize(self, state: PipelineState):
        self._log("SCIENTIFIC", "Generating hypotheses...", state)
        raw, _ = await self.router.call(
            role="primary",
            system_prompt=phases.SCIENTIFIC_HYPOTHESIS_SYSTEM,
            user_prompt=phases.scientific_hypothesis_prompt(state)
        )
        data = extract_json(raw)
        state.scientific_state["hypotheses"] = data.get("hypotheses", [])

    async def _phase_scientific_test(self, state: PipelineState):
        self._log("SCIENTIFIC", "Running falsification tests...", state)
        raw, _ = await self.router.call(
            role="scoring",
            system_prompt=phases.SCIENTIFIC_TEST_SYSTEM,
            user_prompt=phases.scientific_test_prompt(state)
        )
        data = extract_json(raw)
        state.scientific_state["test_results"] = data.get("test_results", [])
    async def _phase_socratic_question(self, state: PipelineState):
        self._log("SOCRATIC", "Generating Socratic questions...", state)
        raw, _ = await self.router.call(
            role="primary",
            system_prompt=phases.SOCRATIC_QUESTION_SYSTEM,
            user_prompt=phases.socratic_question_prompt(state)
        )
        data = extract_json(raw)
        state.socratic_state["questions"] = data.get("questions", [])

    async def _phase_socratic_answer(self, state: PipelineState):
        self._log("SOCRATIC", "Attempting Dialectic answers...", state)
        raw, _ = await self.router.call(
            role="scoring", # Using scoring role for the 'student' response
            system_prompt=phases.SOCRATIC_ANSWER_SYSTEM,
            user_prompt=phases.socratic_answer_prompt(state)
        )
        data = extract_json(raw)
        state.socratic_state["answers"] = data.get("answers", [])

    async def _run_recovery_path(self, state: PipelineState, candidate_to_verify: SolutionCandidate | GenerationCandidate) -> None:
        """Executes a cross-verification path for a potentially problematic candidate."""
        self._log("RECOVERY", f"Initiating recovery path for candidate: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}", state)
        
        try:
            raw_verification, _ = await self.router.call(
                role="recovery_path",
                system_prompt=phases.CROSS_VERIFICATION_SYSTEM,
                user_prompt=phases.cross_verification_prompt(state, candidate_solution=asdict(candidate_to_verify)),
                temperature=0.2, # Keep verification focused
                max_tokens=1024,
            )
            verification_data = extract_json(raw_verification)
            if verification_data.get("verification_findings"):
                self._log("RECOVERY", f"Cross-verification found issues for candidate. Findings: {verification_data['verification_findings'][:2]}", state)
                state.errors.append(f"Recovery Path: Issues found for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {json.dumps(verification_data['verification_findings'])}")
            else:
                self._log("RECOVERY", "Cross-verification found no issues.", state)
        except ParseError as e:
            self._log("RECOVERY", f"Recovery Path: Parse error during verification: {e}", state)
            state.errors.append(f"Recovery Path: Parse error during verification for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        except Exception as e:
            self._log("RECOVERY", f"Recovery Path: Verification failed: {e}", state)
            state.errors.append(f"Recovery Path: Verification failed for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        
        self._log("RECOVERY", "Recovery path complete.", state)
