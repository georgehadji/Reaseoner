"""Research phase mixin for ARAPipeline."""

from __future__ import annotations

import asyncio
import logging

from reasoner.core.constants import TRUNCATION
from reasoner.core.search import get_discovery_client
from reasoner.models import PipelineState
from reasoner.parsing import ParseError, extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class ResearchMixin(PipelineMixinProtocol):
    """Mixin providing research phase methods."""

    async def _phase_research_web_search(self, state: PipelineState) -> None:
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
                
            # LLM may return a string instead of a list — wrap it rather than drop it.
            _raw_q = data.get("queries", [])
            if isinstance(_raw_q, list):
                queries = _raw_q[:TRUNCATION.KEY_INSIGHTS]
            elif isinstance(_raw_q, str) and _raw_q.strip():
                queries = [_raw_q.strip()]
            else:
                queries = []
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
