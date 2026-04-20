"""Search, vetting, and deep-read mixin for ARAPipeline.

Extracted from pipeline.py to reduce the God Object and make search logic
independently testable.  Requires `self._call_llm_cached` and `self._log`
from the host class.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

from reasoner.core.constants import TRUNCATION
from reasoner.core.search import get_discovery_client, _should_include_result
from reasoner.models import PipelineState
from reasoner.parsing import ParseError, extract_json, safe_list
from reasoner.sanitization import sanitize_for_prompt

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class SearchMixin(PipelineMixinProtocol):
    """Mixin providing search, vetting, and deep-read phase methods."""

    # ── Shared helpers ───────────────────────────────────────────────────

    @staticmethod
    def _enrich_query(query: str, problem: str) -> str:
        """Append disambiguation terms for known collision acronyms and ambiguous words."""
        problem_lower = problem.lower()
        query_lower = query.lower()
        # AGI disambiguation
        if "agi" in query_lower and (
            "artificial general intelligence" in problem_lower
            or "singularity" in problem_lower
            or "timeline" in problem_lower
        ):
            if "artificial general intelligence" not in query_lower:
                query += " artificial general intelligence"
        # Greek "ανάπτυξη" (development) disambiguation
        if "ανάπτυξη" in problem_lower or "ανάπτυξη" in query_lower:
            if any(
                k in problem_lower
                for k in ["ai", "agent", "software", "programming", "python", "τεχνητή νοημοσύνη", "πράκτορας"]
            ):
                if "παιδ" not in problem_lower and "child" not in problem_lower and "παιδαγωγ" not in problem_lower:
                    if "λογισμικού" not in query_lower and "software" not in query_lower and "προγραμματισμός" not in query_lower:
                        query += " λογισμικού προγραμματισμός"
        return query.strip()

    # ── Context vetting ──────────────────────────────────────────────────

    async def _phase_context_vetting(self, state: PipelineState, source_type: str = "general") -> None:
        """
        Iterative RAG Phase: Retrieves and vets external context using CoT to flag issues.
        Now uses an iterative loop where the LLM decides if more searches are needed.
        """
        self._log("VETTING", f"Starting iterative context gathering (source: {source_type})...", state)

        # Skip if already done by research method
        if state.web_discovery_results:
            self._log("VETTING", "Reusing existing web discovery results from research phase.", state)
            await self._vet_results(state, state.web_discovery_results)
            return

        # --- QUERY DISAMBIGUATION ---
        _AMBIGUOUS_PRONOUNS_RE = re.compile(
            r"\b(it|this|that|these|those|they|them|their|he|she|his|her|him)\b",
            re.IGNORECASE,
        )
        disambiguated_problem = state.problem
        if len(state.problem) < 120 and not _AMBIGUOUS_PRONOUNS_RE.search(state.problem):
            self._log("VETTING", "Query is short and unambiguous — skipping disambiguation.", state)
        else:
            try:
                raw_disam, _ = await self._call_llm_cached(
                    role="primary",
                    phase_key="disambiguation",
                    system_prompt=phases.DISAMBIGUATION_SYSTEM,
                    user_prompt=phases.disambiguation_prompt(
                        state.problem, state.task_type.value if state.task_type else None
                    ),
                    max_tokens=256,
                    state=state,
                )
                disam_data = extract_json(raw_disam) or {}
                if disam_data.get("was_ambiguous"):
                    disambiguated_problem = disam_data.get("rewritten_query", state.problem)
                    self._log(
                        "VETTING",
                        f"Disambiguated query: '{disambiguated_problem}' (was ambiguous: {disam_data.get('reasoning', '')})",
                        state,
                    )
                else:
                    self._log("VETTING", "Query is clear — no disambiguation needed.", state)
            except Exception as exc:
                self._log("VETTING", f"Disambiguation failed ({exc}) — using original problem.", state)

        max_iterations = 3
        current_results: list[dict] = []
        seen_urls: set[str] = set()

        try:
            client, _ = await get_discovery_client(source_type=source_type)
        except Exception as e:
            self._log("VETTING", f"Failed to initialize discovery client: {e}", state)
            state.errors.append(f"Vetting: Client init failed: {e}")
            return

        # Temporarily replace problem with disambiguated version for search
        original_problem = state.problem
        state.problem = disambiguated_problem

        # Iterative search loop
        for i in range(1, max_iterations + 1):
            self._log("VETTING", f"Iteration {i}/{max_iterations}: Planning searches...", state)

            raw_decision, _ = await self._call_llm_cached(
                role="primary",
                phase_key="research",
                system_prompt=phases.ITERATIVE_CONTEXT_SYSTEM,
                user_prompt=phases.iterative_context_prompt(state, current_results, i, max_iterations),
                state=state,
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

            # Guard: LLM occasionally returns "queries" as a bare string instead of a list
            _raw_q = decision_data.get("queries", [])
            if not isinstance(_raw_q, list):
                if isinstance(_raw_q, str) and _raw_q.strip():
                    queries = [_raw_q.strip()[:TRUNCATION.SNIPPET]]
                    self._log(
                        "VETTING",
                        f"LLM returned string query instead of list. Recovered: '{queries[0]}'",
                        state,
                    )
                else:
                    self._log(
                        "VETTING",
                        f"LLM returned malformed queries (type: {type(_raw_q).__name__}, value: {_raw_q!r}). Skipping this iteration.",
                        state,
                    )
                    state.errors.append(f"Vetting: LLM returned non-list queries: {_raw_q!r}")
                    continue
            else:
                queries = [q for q in _raw_q[:TRUNCATION.KEY_INSIGHTS] if isinstance(q, str) and q.strip()]

            if not queries:
                self._log("VETTING", "No valid queries to execute. Breaking search loop.", state)
                break

            self._log("VETTING", f"Executing queries: {queries}", state)

            # Execute searches concurrently with query enrichment
            enriched_queries = [self._enrich_query(q, disambiguated_problem) for q in queries]

            async def _search(q: str):
                try:
                    return await client.search(
                        q, num_results=5, source_type=source_type, domain=self.domain
                    )
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

            # Early-exit: if fewer than 3 results passed filtering after the first iteration,
            # stop burning tokens on useless searches and proceed with LLM-only analysis.
            if i == 1 and len(current_results) < 3:
                self._log(
                    "VETTING",
                    f"Only {len(current_results)} results passed filtering after first iteration. Aborting further searches.",
                    state,
                )
                break

        # Restore original problem
        state.problem = original_problem

        state.web_discovery_results = current_results
        self._log("VETTING", f"Iterative search complete. Total results: {len(current_results)}", state)

        # Apply CoT vetting to all results
        await self._vet_results(state, current_results)

    async def _vet_single(self, state: PipelineState, result: dict) -> dict:
        """Vet a single search result. Mutates and returns the result dict."""
        retrieved_text = result.get("snippet", "")
        if not retrieved_text:
            return result
        sanitized_text = sanitize_for_prompt(retrieved_text)[0]
        try:
            raw_flags, _ = await self._call_llm_cached(
                role="context_vetting",
                system_prompt=phases.COT_DETECTION_SYSTEM,
                user_prompt=phases.cot_detection_prompt(state, sanitized_text),
                max_tokens=512,
                state=state,
            )
            flags_data = extract_json(raw_flags)
            result["vetting_flags"] = flags_data.get("flags", [])
            if result["vetting_flags"]:
                self._log(
                    "VETTING",
                    f"Flagged issues in a retrieved snippet (source: {result.get('source')}).",
                    state,
                )
        except ParseError as e:
            self._log(
                "VETTING",
                f"CoT vetting parse error for snippet (source: {result.get('source')}): {e}",
                state,
            )
            result["vetting_flags"] = [
                {"statement": "(CoT vetting parse error)", "reasoning": str(e)}
            ]
        except Exception as e:
            self._log(
                "VETTING",
                f"CoT vetting failed for snippet (source: {result.get('source')}): {e}",
                state,
            )
            result["vetting_flags"] = [
                {"statement": "(CoT vetting failed)", "reasoning": str(e)}
            ]
        return result

    async def _vet_results(self, state: PipelineState, results: list[dict]) -> None:
        """Apply CoT vetting to search results in parallel (max 4 concurrent)."""
        self._log("VETTING", f"Applying CoT vetting to {len(results)} results...", state)

        semaphore = asyncio.Semaphore(4)

        async def _vet_with_limit(r: dict) -> dict:
            async with semaphore:
                return await self._vet_single(state, r)

        vetted_results = await asyncio.gather(*[_vet_with_limit(r) for r in results])

        # Compute context quality for synthesis circuit breaker
        if not vetted_results:
            state.context_quality = "missing"
        else:
            flagged_count = sum(1 for r in vetted_results if r.get("vetting_flags"))
            total = len(vetted_results)
            if flagged_count == total and total > 0:
                state.context_quality = "contaminated"
            elif flagged_count > total // 2:
                state.context_quality = "partial"
            else:
                state.context_quality = "good"
        self._log("VETTING", f"Context vetting complete. Quality: {state.context_quality}", state)
        state.vetted_context = vetted_results

    # ── Deep read ────────────────────────────────────────────────────────

    async def _phase_deep_read(self, state: PipelineState, max_sources: int = 3) -> None:
        """
        Deep Read Phase: Fetch full content from critical sources and extract
        structured summaries using an LLM.
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
                r.get("url") for r in state.vetted_context[:max_sources] if r.get("url")
            ]

        if not sources_to_scrape:
            self._log("DEEP_READ", "No sources available for deep reading. Attempting fallback search...", state)
            # Fallback: try a direct broad search with the problem
            try:
                client, _ = await get_discovery_client(source_type="general")
                fallback_results = await client.search(
                    state.problem, num_results=5, source_type="general", domain=self.domain
                )
                if fallback_results:
                    sources_to_scrape = [
                        r.get("url") for r in fallback_results[:max_sources] if r.get("url")
                    ]
                    # Add fallback results to web_discovery_results so vetting can use them
                    state.web_discovery_results.extend(fallback_results)
                    self._log("DEEP_READ", f"Fallback search found {len(sources_to_scrape)} sources.", state)
                else:
                    self._log("DEEP_READ", "Fallback search also found no sources.", state)
                    state.errors.append("Deep Read: no sources found for deep reading")
            except Exception as exc:
                self._log("DEEP_READ", f"Fallback search failed: {exc}", state)
                state.errors.append(f"Deep Read: fallback search failed: {exc}")
            if not sources_to_scrape:
                return

        self._log("DEEP_READ", f"Deep reading {len(sources_to_scrape)} sources...", state)

        # Feature flag for safety: set REASONER_DEEP_READ_LLM=0 to disable LLM extraction
        use_llm_extraction = os.getenv("REASONER_DEEP_READ_LLM", "1") != "0"

        async def _process_scraped(scraped: dict, matching_result: dict) -> None:
            """Process a single scraped result (success or failure path)."""
            url = scraped.get("url")
            title = scraped.get("title", "Unknown")

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
                            max_tokens=1024,
                            state=state,
                        )
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
                            max_tokens=512,
                            state=state,
                        )
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

        try:
            scraped_results = await scrape_urls(sources_to_scrape)

            # Build url -> result lookup (sequential, cheap)
            url_to_result = {r.get("url"): r for r in state.vetted_context if r.get("url")}

            tasks = []
            for scraped in scraped_results:
                matching_result = url_to_result.get(scraped.get("url"))
                if matching_result:
                    tasks.append(_process_scraped(scraped, matching_result))

            # Run LLM extractions in parallel (max 4 concurrent)
            semaphore = asyncio.Semaphore(4)

            async def _with_limit(task):
                async with semaphore:
                    return await task

            await asyncio.gather(*[_with_limit(t) for t in tasks])

            self._log("DEEP_READ", "Deep read complete.", state)

        except Exception as e:
            self._log("DEEP_READ", f"Deep read failed: {e}", state)
            state.errors.append(f"Deep read failed: {e}")

    # ── Evidence validation ──────────────────────────────────────────────

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
            vc
            for vc in (state.vetted_context or [])
            if (vc.get("summary") or "").strip() and vc.get("summary") != "INSUFFICIENT"
        ]

        if not summaries:
            self._log(
                "VALIDATION",
                f"No extracted evidence for {len(uncertain)} uncertain assumption(s). "
                "Proceeding with low-evidence synthesis.",
                state,
            )
