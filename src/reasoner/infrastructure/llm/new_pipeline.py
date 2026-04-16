"""
New ARA Pipeline using Hexagonal Architecture

This pipeline uses:
- LLM Provider ports (not concrete implementations)
- Event-sourced aggregates for state
- Event store for persistence
- Event bus for notifications
"""

from __future__ import annotations

import logging
import time
from typing import Any

from reasoner.infrastructure.llm.ports import LLMProvider, LLMConfig, Message, MessageRole
from reasoner.core.temperatures import PHASE_TEMPERATURES
from reasoner.core.constants import get_token_budget
from reasoner.core.aggregates.pipeline import PipelineAggregate
from reasoner.core.events.domain_events import make_event, EventType
from reasoner.infrastructure.persistence.event_store import EventStore

logger = logging.getLogger(__name__)


class NewARAPipeline:
    """
    New ARA Pipeline using Hexagonal Architecture.
    
    This pipeline:
    - Uses LLMProvider port (not concrete implementations)
    - Records all state changes as domain events
    - Supports resume from any phase
    - Persists events to event store
    """
    
    def __init__(
        self,
        router: Any,  # ProviderRouter from legacy llm.py
        preset_name: str | None = None,
        top_k: int = 2,
        source_type: str = "general",
        domain: str | None = None,
        parallel: bool = True,
    ):
        self.router = router
        self.preset_name = preset_name
        self.top_k = top_k
        self.source_type = source_type
        self.domain = domain
        self.parallel = parallel
        self.verbose = True
    
    def _log(self, phase: str, message: str, aggregate: PipelineAggregate) -> None:
        """Log message and record in aggregate."""
        if self.verbose:
            logger.info(f"[{phase}] {message}")
        aggregate.state_data.logs.append(f"[{phase}] {message}")
    
    async def run_with_aggregate(
        self,
        problem: str,
        aggregate: PipelineAggregate,
        event_store: EventStore | None = None,
    ) -> Any:
        """
        Run pipeline with event-sourced aggregate.
        
        All state changes are recorded as domain events.
        """
        from reasoner.models import PipelineState
        
        # Create legacy state for compatibility
        state = PipelineState(problem=problem, preset_name=self.preset_name)
        
        # Get method from preset
        method = self._get_method_from_preset()
        self._log("ORCHESTRATOR", f"Using method: {method}", aggregate)
        
        # --- UNIVERSAL PHASES ---
        
        # Phase 0: Classification
        self._log("PHASE", "Starting classification", aggregate)
        await self._phase_classify(state, aggregate, event_store)
        
        # Phase 1: Decomposition
        self._log("PHASE", "Starting decomposition", aggregate)
        await self._phase_decompose(state, aggregate, event_store)
        
        # Phase 2: Context Vetting
        self._log("PHASE", "Starting context vetting", aggregate)
        await self._phase_context_vetting(state, aggregate, event_store)
        
        # --- METHOD-SPECIFIC PHASES ---
        
        if method == "multi_perspective":
            await self._run_multi_perspective(state, aggregate, event_store)
        elif method == "jury":
            await self._run_jury(state, aggregate, event_store)
        elif method == "debate":
            await self._run_debate(state, aggregate, event_store)
        elif method == "research":
            await self._run_research(state, aggregate, event_store)
        elif method == "socratic":
            await self._run_socratic(state, aggregate, event_store)
        # Add other methods as needed
        
        # --- SYNTHESIS ---
        
        self._log("PHASE", "Starting synthesis", aggregate)
        await self._phase_synthesis(state, aggregate, event_store)
        
        return state
    
    async def _phase_classify(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Classification phase using LLM port."""
        # Record phase started
        start_event = make_event(
            EventType.PHASE_STARTED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="classification",
        )
        aggregate.record_event(start_event)
        
        # Get LLM provider from router
        provider = self.router.get_provider_for_role("classification", self.preset_name)
        
        # Build messages
        from reasoner.phases import classification_prompt, CLASSIFICATION_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=CLASSIFICATION_SYSTEM),
            Message(role=MessageRole.USER, content=classification_prompt(state.problem, "English")),
        ]
        
        # Call LLM
        config = LLMConfig(max_tokens=get_token_budget("classification"), temperature=PHASE_TEMPERATURES["classification"])
        response = await provider.complete(messages, config)
        
        # Parse result
        import json
        from reasoner.parsing import extract_json
        
        try:
            result = extract_json(response.content)
            state.task_type = result.get("task_type", "analytical")
            state.language = result.get("language", "English")
        except Exception as e:
            logger.warning(f"Classification parse error: {e}")
            state.task_type = "analytical"
            state.language = "English"
        
        # Record phase completed
        complete_event = make_event(
            EventType.PHASE_COMPLETED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="classification",
            result={"task_type": state.task_type, "language": state.language},
            tokens={"prompt": response.tokens_prompt, "completion": response.tokens_completion},
            model_used=response.model_used,
            duration_seconds=0.0,  # Would track this
        )
        aggregate.record_event(complete_event)
        
        # Persist events
        if event_store:
            await event_store.save_events([start_event, complete_event])
    
    async def _phase_decompose(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Decomposition phase using LLM port."""
        # Record phase started
        start_event = make_event(
            EventType.PHASE_STARTED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="decomposition",
        )
        aggregate.record_event(start_event)
        
        # Get LLM provider
        provider = self.router.get_provider_for_role("decomposition", self.preset_name)
        
        # Build messages
        from reasoner.phases import decomposition_prompt, DECOMPOSITION_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=DECOMPOSITION_SYSTEM),
            Message(role=MessageRole.USER, content=decomposition_prompt(state)),
        ]
        
        # Call LLM
        config = LLMConfig(max_tokens=get_token_budget("decomposition"), temperature=PHASE_TEMPERATURES["decomposition"])
        response = await provider.complete(messages, config)
        
        # Parse result
        import json
        from reasoner.parsing import extract_json
        
        try:
            result = extract_json(response.content)
            state.decomposition = result
        except Exception as e:
            logger.warning(f"Decomposition parse error: {e}")
            state.decomposition = {}
        
        # Record phase completed
        complete_event = make_event(
            EventType.PHASE_COMPLETED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="decomposition",
            result=state.decomposition,
            tokens={"prompt": response.tokens_prompt, "completion": response.tokens_completion},
            model_used=response.model_used,
        )
        aggregate.record_event(complete_event)
        
        if event_store:
            await event_store.save_events([start_event, complete_event])
    
    async def _phase_context_vetting(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Context vetting phase with search."""
        # Record phase started
        start_event = make_event(
            EventType.PHASE_STARTED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="context_vetting",
        )
        aggregate.record_event(start_event)
        
        # Perform search
        from reasoner.core.search import get_discovery_client
        
        client = await get_discovery_client(source_type=self.source_type)
        
        search_results = await client.search(
            query=state.problem,
            domain=self.domain,
        )
        
        state.web_discovery_results = search_results
        
        # Record context fetched event
        fetched_event = make_event(
            EventType.CONTEXT_FETCHED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            source_type=self.source_type,
            query=state.problem,
            result_count=len(search_results),
        )
        aggregate.record_event(fetched_event)
        
        if event_store:
            await event_store.save_events([start_event, fetched_event])
    
    async def _run_multi_perspective(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Multi-perspective method with parallel generation."""
        from reasoner.phases import perspective_prompt, PERSPECTIVE_SYSTEMS
        from reasoner.models import PerspectiveType
        
        perspectives = [
            PerspectiveType.CONSTRUCTIVE,
            PerspectiveType.DESTRUCTIVE,
            PerspectiveType.SYSTEMIC,
            PerspectiveType.MINIMALIST,
        ]
        
        if self.parallel:
            # Run perspectives in parallel
            tasks = [
                self._generate_perspective(p, state, aggregate, event_store)
                for p in perspectives
            ]
            await asyncio.gather(*tasks)
        else:
            # Run sequentially
            for p in perspectives:
                await self._generate_perspective(p, state, aggregate, event_store)
    
    async def _generate_perspective(
        self,
        perspective: str,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Generate single perspective."""
        # Record phase started
        start_event = make_event(
            EventType.PHASE_STARTED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="perspective",
        )
        aggregate.record_event(start_event)
        
        # Get LLM provider
        provider = self.router.get_provider_for_role("perspective", self.preset_name)
        
        # Build messages
        from reasoner.phases import perspective_prompt, PERSPECTIVE_SYSTEMS
        
        system_prompt = PERSPECTIVE_SYSTEMS.get(perspective, PERSPECTIVE_SYSTEMS["constructive"])
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            Message(role=MessageRole.USER, content=perspective_prompt(state, perspective)),
        ]
        
        # Call LLM
        config = LLMConfig(max_tokens=get_token_budget("perspective"), temperature=PHASE_TEMPERATURES["perspective"])
        response = await provider.complete(messages, config)
        
        # Parse result
        import json
        from reasoner.parsing import extract_json
        
        try:
            result = extract_json(response.content)
            if not hasattr(state, 'perspectives') or not state.perspectives:
                state.perspectives = []
            state.perspectives.append(result)
        except Exception as e:
            logger.warning(f"Perspective parse error: {e}")
        
        # Record perspective generated event
        generated_event = make_event(
            EventType.PERSPECTIVE_GENERATED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            perspective_type=perspective,
            model_used=response.model_used,
        )
        aggregate.record_event(generated_event)
        
        if event_store:
            await event_store.save_events([start_event, generated_event])
    
    async def _run_debate(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """
        Debate method with opposing arguments and judge.
        
        Structure:
        1. Opening statements (2 sides)
        2. Rebuttals (2 rounds)
        3. Closing statements
        4. Judge decision
        """
        from reasoner.phases import debate_prompt, DEBATE_SYSTEMS
        
        # Get LLM providers for different roles
        pro_provider = self.router.get_provider_for_role("generator_1", self.preset_name)
        con_provider = self.router.get_provider_for_role("generator_2", self.preset_name)
        judge_provider = self.router.get_provider_for_role("meta_evaluator", self.preset_name)
        
        # Store debate state
        if not hasattr(state, 'debate_rounds'):
            state.debate_rounds = []
        
        # Opening statements
        self._log("DEBATE", "Opening statements", aggregate)
        
        pro_opening = await self._debate_argument(
            "pro", pro_provider, state, aggregate, event_store, round_num=0
        )
        con_opening = await self._debate_argument(
            "con", con_provider, state, aggregate, event_store, round_num=0
        )
        
        state.debate_rounds.append({
            "round": 0,
            "pro": pro_opening,
            "con": con_opening,
        })
        
        # Rebuttals (2 rounds)
        for round_num in range(1, 3):
            self._log("DEBATE", f"Rebuttal round {round_num}", aggregate)
            
            pro_rebuttal = await self._debate_rebuttal(
                "pro", pro_provider, state, aggregate, event_store,
                round_num=round_num,
                opponent_argument=con_opening if round_num == 1 else state.debate_rounds[-1]["con"]
            )
            con_rebuttal = await self._debate_rebuttal(
                "con", con_provider, state, aggregate, event_store,
                round_num=round_num,
                opponent_argument=pro_opening if round_num == 1 else state.debate_rounds[-1]["pro"]
            )
            
            state.debate_rounds.append({
                "round": round_num,
                "pro": pro_rebuttal,
                "con": con_rebuttal,
            })
        
        # Closing statements
        self._log("DEBATE", "Closing statements", aggregate)
        
        pro_closing = await self._debate_closing(
            "pro", pro_provider, state, aggregate, event_store
        )
        con_closing = await self._debate_closing(
            "con", con_provider, state, aggregate, event_store
        )
        
        # Judge decision
        self._log("DEBATE", "Judge evaluation", aggregate)
        
        judge_decision = await self._debate_judge(
            judge_provider, state, aggregate, event_store,
            pro_closing=pro_closing,
            con_closing=con_closing,
        )
        
        state.debate_result = judge_decision
    
    async def _debate_argument(
        self,
        side: str,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        round_num: int,
    ) -> str:
        """Generate opening argument for a side."""
        from reasoner.phases import debate_opening_prompt, DEBATE_OPENING_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=DEBATE_OPENING_SYSTEM.replace("{SIDE}", side)),
            Message(role=MessageRole.USER, content=debate_opening_prompt(state.problem, side)),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("perspective"), temperature=PHASE_TEMPERATURES["primary"])
        response = await provider.complete(messages, config)
        
        return response.content
    
    async def _debate_rebuttal(
        self,
        side: str,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        round_num: int,
        opponent_argument: str,
    ) -> str:
        """Generate rebuttal argument."""
        from reasoner.phases import debate_rebuttal_prompt, DEBATE_REBUTTAL_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=DEBATE_REBUTTAL_SYSTEM.replace("{SIDE}", side)),
            Message(role=MessageRole.USER, content=debate_rebuttal_prompt(
                state.problem, side, opponent_argument
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("perspective"), temperature=PHASE_TEMPERATURES["primary"])
        response = await provider.complete(messages, config)
        
        return response.content
    
    async def _debate_closing(
        self,
        side: str,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> str:
        """Generate closing statement."""
        from reasoner.phases import debate_closing_prompt, DEBATE_CLOSING_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=DEBATE_CLOSING_SYSTEM.replace("{SIDE}", side)),
            Message(role=MessageRole.USER, content=debate_closing_prompt(state.problem, side)),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("synthesis"), temperature=PHASE_TEMPERATURES["synthesis"])
        response = await provider.complete(messages, config)
        
        return response.content
    
    async def _debate_judge(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        pro_closing: str,
        con_closing: str,
    ) -> dict[str, Any]:
        """Judge the debate and make a decision."""
        from reasoner.phases import debate_judge_prompt, DEBATE_JUDGE_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=DEBATE_JUDGE_SYSTEM),
            Message(role=MessageRole.USER, content=debate_judge_prompt(
                state.problem, pro_closing, con_closing
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("scoring"), temperature=PHASE_TEMPERATURES["scoring"])
        response = await provider.complete(messages, config)
        
        # Parse judge decision
        import json
        from reasoner.parsing import extract_json
        
        try:
            result = extract_json(response.content)
            return result
        except Exception:
            return {"decision": response.content, "confidence": 0.5}
    
    async def _run_research(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """
        Research method with iterative search loops.
        
        Structure:
        1. Plan search queries
        2. Execute searches (multiple iterations)
        3. Analyze and synthesize findings
        4. Verify claims with additional searches
        """
        from reasoner.core.search import get_discovery_client
        
        # Initialize research state
        if not hasattr(state, 'research_iterations'):
            state.research_iterations = []
        
        # Get research provider
        research_provider = self.router.get_provider_for_role("primary", self.preset_name)
        
        # Iteration 1: Initial search
        self._log("RESEARCH", "Initial search planning", aggregate)
        
        search_plan = await self._research_plan_queries(
            research_provider, state, aggregate, event_store
        )
        
        # Execute searches
        all_results = []
        for query in search_plan.get('queries', [state.problem]):
            client = await get_discovery_client(source_type=self.source_type)
            results = await client.search(query=query, domain=self.domain)
            all_results.extend(results)
        
        state.research_iterations.append({
            "iteration": 1,
            "queries": search_plan.get('queries', []),
            "results_count": len(all_results),
        })
        
        # Record context fetched
        fetched_event = make_event(
            EventType.CONTEXT_FETCHED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            source_type=self.source_type,
            query=state.problem,
            result_count=len(all_results),
        )
        aggregate.record_event(fetched_event)
        
        # Iteration 2-3: Deep dive based on initial findings
        for iteration in range(2, 4):
            self._log("RESEARCH", f"Iteration {iteration}: Deep dive", aggregate)
            
            # Plan follow-up queries based on gaps
            follow_up_plan = await self._research_plan_followup(
                research_provider, state, aggregate, event_store,
                current_results=all_results,
            )
            
            if not follow_up_plan.get('needs_more_search', False):
                self._log("RESEARCH", "Sufficient information gathered", aggregate)
                break
            
            iteration_results = []
            for query in follow_up_plan.get('queries', []):
                client = await get_discovery_client(source_type=self.source_type)
                results = await client.search(query=query, domain=self.domain)
                iteration_results.extend(results)
            
            all_results.extend(iteration_results)
            
            state.research_iterations.append({
                "iteration": iteration,
                "queries": follow_up_plan.get('queries', []),
                "results_count": len(iteration_results),
            })
        
        # Store all research results
        state.web_discovery_results = all_results
        
        # Analyze findings
        self._log("RESEARCH", "Analyzing findings", aggregate)
        
        analysis = await self._research_analyze_findings(
            research_provider, state, aggregate, event_store,
            all_results=all_results,
        )
        
        state.research_analysis = analysis
    
    async def _research_plan_queries(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> dict[str, Any]:
        """Plan initial search queries."""
        from reasoner.phases import research_plan_prompt, RESEARCH_PLAN_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=RESEARCH_PLAN_SYSTEM),
            Message(role=MessageRole.USER, content=research_plan_prompt(state.problem)),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("research"), temperature=PHASE_TEMPERATURES["research"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            return extract_json(response.content)
        except Exception:
            return {"queries": [state.problem]}
    
    async def _research_plan_followup(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        current_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Plan follow-up queries based on gaps."""
        from reasoner.phases import research_followup_prompt, RESEARCH_FOLLOWUP_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=RESEARCH_FOLLOWUP_SYSTEM),
            Message(role=MessageRole.USER, content=research_followup_prompt(
                state.problem, current_results[:10]  # Limit context
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("research"), temperature=PHASE_TEMPERATURES["research"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            return extract_json(response.content)
        except Exception:
            return {"needs_more_search": False, "queries": []}
    
    async def _research_analyze_findings(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        all_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze and synthesize research findings."""
        from reasoner.phases import research_analyze_prompt, RESEARCH_ANALYZE_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=RESEARCH_ANALYZE_SYSTEM),
            Message(role=MessageRole.USER, content=research_analyze_prompt(
                state.problem, all_results[:20]  # Limit context
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("research"), temperature=PHASE_TEMPERATURES["research"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            return extract_json(response.content)
        except Exception:
            return {"summary": response.content, "key_findings": []}
    
    async def _run_socratic(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """
        Socratic method with maieutic questioning.
        
        Structure:
        1. Initial position statement
        2. Elenchus (cross-examination)
        3. Aporia (recognition of ignorance)
        4. Maieutics (midwifery - drawing out knowledge)
        5. Refined understanding
        """
        from reasoner.phases import socratic_prompt, SOCRATIC_SYSTEMS
        
        # Get Socratic provider
        socratic_provider = self.router.get_provider_for_role("primary", self.preset_name)
        
        # Initialize socratic state
        if not hasattr(state, 'socratic_dialogue'):
            state.socratic_dialogue = []
        
        # Step 1: Initial position
        self._log("SOCRATIC", "Eliciting initial position", aggregate)
        
        initial_position = await self._socratic_elicit_position(
            socratic_provider, state, aggregate, event_store
        )
        
        state.socratic_dialogue.append({
            "step": "initial_position",
            "content": initial_position,
        })
        
        # Step 2: Elenchus (cross-examination)
        self._log("SOCRATIC", "Cross-examination (elenchus)", aggregate)
        
        elenchus_questions = await self._socratic_generate_questions(
            socratic_provider, state, aggregate, event_store,
            position=initial_position,
        )
        
        state.socratic_dialogue.append({
            "step": "elenchus",
            "questions": elenchus_questions,
        })
        
        # Step 3: Aporia (recognition of ignorance)
        self._log("SOCRATIC", "Inducing aporia", aggregate)
        
        aporia = await self._socratic_induce_aporia(
            socratic_provider, state, aggregate, event_store,
            position=initial_position,
            questions=elenchus_questions,
        )
        
        state.socratic_dialogue.append({
            "step": "aporia",
            "content": aporia,
        })
        
        # Step 4: Maieutics (drawing out knowledge)
        self._log("SOCRATIC", "Maieutic dialogue", aggregate)
        
        maieutic_insights = await self._socratic_maieutics(
            socratic_provider, state, aggregate, event_store,
            aporia=aporia,
        )
        
        state.socratic_dialogue.append({
            "step": "maieutics",
            "insights": maieutic_insights,
        })
        
        # Step 5: Refined understanding
        self._log("SOCRATIC", "Synthesizing refined understanding", aggregate)
        
        refined_understanding = await self._socratic_synthesis(
            socratic_provider, state, aggregate, event_store,
            dialogue=state.socratic_dialogue,
        )
        
        state.socratic_result = refined_understanding
    
    async def _socratic_elicit_position(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> str:
        """Elicit initial position on the problem."""
        from reasoner.phases import socratic_position_prompt, SOCRATIC_POSITION_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SOCRATIC_POSITION_SYSTEM),
            Message(role=MessageRole.USER, content=socratic_position_prompt(state.problem)),
        ]
        
        config = LLMConfig(max_tokens=1024, temperature=PHASE_TEMPERATURES["perspective"])
        response = await provider.complete(messages, config)
        
        return response.content
    
    async def _socratic_generate_questions(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        position: str,
    ) -> list[str]:
        """Generate Socratic questions for cross-examination."""
        from reasoner.phases import socratic_questions_prompt, SOCRATIC_QUESTIONS_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SOCRATIC_QUESTIONS_SYSTEM),
            Message(role=MessageRole.USER, content=socratic_questions_prompt(position)),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("perspective"), temperature=PHASE_TEMPERATURES["primary"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            result = extract_json(response.content)
            return result.get('questions', [])
        except Exception:
            return [response.content[:500]]
    
    async def _socratic_induce_aporia(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        position: str,
        questions: list[str],
    ) -> str:
        """Induce recognition of ignorance (aporia)."""
        from reasoner.phases import socratic_aporia_prompt, SOCRATIC_APORIA_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SOCRATIC_APORIA_SYSTEM),
            Message(role=MessageRole.USER, content=socratic_aporia_prompt(
                state.problem, position, questions
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("decomposition"), temperature=PHASE_TEMPERATURES["decomposition"])
        response = await provider.complete(messages, config)
        
        return response.content
    
    async def _socratic_maieutics(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        aporia: str,
    ) -> list[str]:
        """Draw out knowledge through maieutic dialogue."""
        from reasoner.phases import socratic_maieutics_prompt, SOCRATIC_MAIEUTICS_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SOCRATIC_MAIEUTICS_SYSTEM),
            Message(role=MessageRole.USER, content=socratic_maieutics_prompt(aporia)),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("perspective"), temperature=PHASE_TEMPERATURES["primary"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            result = extract_json(response.content)
            return result.get('insights', [])
        except Exception:
            return [response.content[:500]]
    
    async def _socratic_synthesis(
        self,
        provider: LLMProvider,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
        dialogue: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Synthesize refined understanding from dialogue."""
        from reasoner.phases import socratic_synthesis_prompt, SOCRATIC_SYNTHESIS_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SOCRATIC_SYNTHESIS_SYSTEM),
            Message(role=MessageRole.USER, content=socratic_synthesis_prompt(
                state.problem, dialogue
            )),
        ]
        
        config = LLMConfig(max_tokens=get_token_budget("synthesis"), temperature=PHASE_TEMPERATURES["synthesis"])
        response = await provider.complete(messages, config)
        
        from reasoner.parsing import extract_json
        try:
            return extract_json(response.content)
        except Exception:
            return {"understanding": response.content, "key_insights": []}
    
    async def _phase_synthesis(
        self,
        state: Any,
        aggregate: PipelineAggregate,
        event_store: EventStore | None,
    ) -> None:
        """Synthesis phase."""
        # Record phase started
        start_event = make_event(
            EventType.PHASE_STARTED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="synthesis",
        )
        aggregate.record_event(start_event)
        
        # Get LLM provider
        provider = self.router.get_provider_for_role("synthesis", self.preset_name)
        
        # Build synthesis prompt
        from reasoner.phases import synthesis_prompt, SYNTHESIS_SYSTEM
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=SYNTHESIS_SYSTEM),
            Message(role=MessageRole.USER, content=synthesis_prompt(state)),
        ]
        
        # Call LLM
        config = LLMConfig(max_tokens=get_token_budget("synthesis"), temperature=PHASE_TEMPERATURES["synthesis"])
        response = await provider.complete(messages, config)
        
        # Parse result
        import json
        from reasoner.parsing import extract_json
        
        try:
            result = extract_json(response.content)
            state.synthesis = result
        except Exception as e:
            logger.warning(f"Synthesis parse error: {e}")
            state.synthesis = {"core_solution": response.content}
        
        # Record phase completed
        complete_event = make_event(
            EventType.PHASE_COMPLETED,
            aggregate_id=aggregate.aggregate_id,
            version=aggregate.version + 1,
            phase_name="synthesis",
            result=state.synthesis,
            tokens={"prompt": response.tokens_prompt, "completion": response.tokens_completion},
            model_used=response.model_used,
        )
        aggregate.record_event(complete_event)
        
        if event_store:
            await event_store.save_events([start_event, complete_event])
    
    def _get_method_from_preset(self) -> str:
        """Get method from preset name (delegates to shared utility)."""
        from reasoner.presets import get_method_from_preset as _get_method
        # NewARAPipeline uses snake_case for internal method dispatch
        return _get_method(self.preset_name or "").replace("-", "_")
    
    async def resume_from_phase(
        self,
        aggregate: PipelineAggregate,
        from_phase: str | None,
        event_store: EventStore | None,
    ) -> Any:
        """Resume pipeline from specific phase."""
        from reasoner.models import PipelineState
        
        # Rebuild state from aggregate
        state = PipelineState(
            problem=aggregate.state_data.problem,
            preset_name=aggregate.state_data.preset,
        )
        state.task_type = aggregate.state_data.task_type
        state.decomposition = aggregate.state_data.decomposition
        
        # Resume from phase
        last_phase = aggregate.get_last_phase()
        
        if last_phase == "classification" or from_phase == "decomposition":
            await self._phase_decompose(state, aggregate, event_store)
        
        # Continue with remaining phases...
        
        return state


# Need asyncio for parallel execution
import asyncio
