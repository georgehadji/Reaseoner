# /hypergate — Inspect HyperGate Routing

HyperGate pre-routes every request before any pipeline runs.

**Architecture:**
```
Problem → [LanguageDetector, ComplexityEstimator, DirectDetector, WebSearchDetector, MethodClassifier]
                                          ↓ (parallel, fail-safe)
                                      TieBreaker
                                          ↓
                  DIRECT | WEB_SEARCH | PIPELINE (method auto-selected)
```

**Key files:**
- [`src/reasoner/hypergate/hyperagent.py`](../src/reasoner/hypergate/hyperagent.py) — orchestrator
- [`src/reasoner/hypergate/sub_agents/`](../src/reasoner/hypergate/sub_agents/) — 5 sub-agents + tie-breaker

**Security note:** Real method names are never exposed to LLMs — only opaque letters (B–Q) appear in sub-agent prompts.

**Thresholds** (in `core/constants.py`):
- Complexity score → triggers multi-phase pipeline vs. direct answer
- Web search score → routes to SearXNG + Perplexity
- Direct score → instant response, skips all phases

**To inspect sub-agent routing decisions for a specific problem:**
```bash
python -c "
import asyncio
from src.reasoner.hypergate.hyperagent import HyperGateAgent
agent = HyperGateAgent()
result = asyncio.run(agent.route('YOUR PROBLEM HERE'))
print(result)
"
```
