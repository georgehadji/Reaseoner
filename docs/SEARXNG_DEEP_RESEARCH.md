# SearXNG — Deep Research Report

> Comprehensive understanding of SearXNG architecture, deployment, API, and integration with the Reasoner project.
> Generated: 2026-04-27

---

## Table of Contents

1. [What SearXNG Is](#1-what-searxng-is)
2. [Internal Architecture](#2-internal-architecture)
3. [Configuration (`settings.yml`)](#3-configuration-settingsyml)
4. [Docker Deployment](#4-docker-deployment)
5. [Search API](#5-search-api)
6. [Reasoner Integration Map](#6-reasoner-integration-map)
7. [Failure Modes & Mitigations](#7-failure-modes--mitigations)
8. [Value to the Reasoner](#8-value-to-the-reasoner)
9. [Appendix: All Touchpoints](#9-appendix-all-touchpoints)

---

## 1. What SearXNG Is

**SearXNG** is a privacy-respecting, self-hosted **metasearch engine**. It does not crawl the web itself. Instead, it acts as a **proxy and aggregator**, sending your query to ~200 supported upstream engines simultaneously, then merging, deduplicating, and ranking the combined results.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Privacy** | Each query appears to come from the SearXNG instance, not the end user. No tracking cookies, no query logs by default. |
| **Open Source** | GPL v3. Fully auditable, community-maintained at `github.com/searxng/searxng`. |
| **Modular Engines** | ~200 pluggable search engines, each with its own scraper or API adapter. |
| **No Single Point of Failure** | If Google blocks the instance, Bing and DuckDuckGo still respond. |
| **Machine API** | JSON/CSV/RSS output for downstream applications like Reasoner. |

### How It Differs from a Search Engine

| | Google | SearXNG |
|---|---|---|
| Crawls web? | Yes (index of billions of pages) | No |
| Sources | Own index | Aggregates 200+ upstream engines |
| Privacy | Tracks users | Proxy — upstreams see only the instance IP |
| Cost | Free (ad-supported) | Free (self-hosted) |
| Rate limits | Per-user quotas | Only upstream engine limits apply |
| Customization | None | Full control over engines, ranking, filters |

---

## 2. Internal Architecture

### Request Flow

```
User/Client
    |
    v
SearXNG Flask/FastAPI App (port 8080)
    |
    v
Engine Dispatcher
    |---------------------|---------------------|
    v                     v                     v
 Google               Bing               DuckDuckGo
    |                     |                     |
(scraped HTML)      (scraped HTML)        (scraped HTML)
    |---------------------|---------------------|
                          |
                          v
              Result Merger + Deduplicator
                          |
                          v
              Formatter (HTML / JSON / CSV / RSS)
```

### Engine Architecture

Each engine is a Python module in `searx/engines/` implementing:

| Attribute | Purpose |
|-----------|---------|
| `search_url` | URL template with `{query}`, `{pageno}`, `{safe_search}` |
| `response` | Parser extracting `(title, url, content)` from HTML/JSON |
| `timeout` | Per-engine timeout (default 3s, some need 10s+) |
| `disabled` | Whether active by default |
| `paging` | Supports pagination? |
| `categories` | Which tabs the engine appears under |

### Engine Categories

| Category | Example Engines |
|----------|----------------|
| `general` | Google, Bing, DDG, Startpage, Brave |
| `science` | arXiv, PubMed, Semantic Scholar, Google Scholar, CORE |
| `it` | GitHub, StackOverflow, MDN, Docker Hub, npm |
| `news` | Bing News, Reuters, DuckDuckGo News |
| `images` | Google Images, Bing Images, Flickr, Pexels |
| `videos` | YouTube (piped), Bing Videos, DuckDuckGo Videos |
| `files` | Library Genesis, Z-Library, SolidTorrents |
| `social media` | Reddit, HackerNews, Mastodon |

### Result Deduplication

SearXNG deduplicates by **normalized URL** before returning. The Reasoner applies a second deduplication layer (`_normalize_url()`) because SearXNG's normalization may miss query-parameter variants (e.g., `?utm_source=x` vs `?ref=y`).

---

## 3. Configuration (`settings.yml`)

The Reasoner mounts `.searxng-settings.yml` into the container at `/etc/searxng/settings.yml`.

### Key Sections

#### `general`

```yaml
general:
  debug: false
  instance_name: "Reasoner Search"
```

- `debug`: Flask debug mode. **NEVER enable in production** — exposes the Werkzeug interactive debugger, which allows remote code execution.
- `instance_name`: Display name in the UI footer.

#### `search` (CRITICAL)

```yaml
search:
  safe_search: 0
  autocomplete: ""
  default_lang: ""
  formats:
    - html
    - json
```

- **`formats`**: **This is the most critical setting for the Reasoner.** By default SearXNG only allows `html`. If `json` is not listed here, all API calls return **HTTP 403 Forbidden**.
- `safe_search`: 0=None, 1=Moderate, 2=Strict
- `autocomplete`: Query completion backend (Google, DDG, Wikipedia, etc.)
- `default_lang`: Language code or `"auto"` for browser detection

#### `server`

```yaml
server:
  port: 8888
  bind_address: "127.0.0.1"
  base_url: false
  secret_key: "ultrasecretkey"
  limiter: false
  public_instance: false
  method: "POST"
```

- **`secret_key`**: Flask session signing key. Used for cookies, CSRF tokens, and image proxy HMACs. If blank, some features break. **Must remain stable across restarts** if `image_proxy` is used — changing it invalidates all existing proxy URLs. Overridden by `$SEARXNG_SECRET_KEY` env var.
- **`limiter`**: Rate limiting + bot protection. **Requires Valkey** (Redis fork). The Reasoner sets `false` because it's a private instance.
- **`public_instance`**: Enables donation links, public metrics. Private instances should keep `false`.
- **`method`**: `POST` (default, hides query from URL/history) or `GET` (bookmarkable, easier for API clients).

#### `outgoing`

```yaml
outgoing:
  request_timeout: 3.0
  max_request_timeout: 10.0
  pool_connections: 100
  pool_maxsize: 20
  enable_http2: true
```

- `request_timeout`: How long to wait for each upstream engine. If Google doesn't respond in 3s, it's skipped and other engines' results are returned.
- `pool_connections`: Max concurrent connections across all engine requests.

#### `engines`

The Reasoner enables 8 engines:

```yaml
engines:
  - name: bing          shortcut: bi    enabled: true
  - name: duckduckgo    shortcut: ddg   enabled: true
  - name: google        shortcut: go    enabled: true
  - name: brave         shortcut: br    enabled: true
  - name: wikipedia     shortcut: wp    enabled: true
  - name: arxiv         shortcut: arx   enabled: true
  - name: github        shortcut: gh    enabled: true
  - name: stackoverflow shortcut: se    enabled: true
```

**Engine selection strategy:**

| Query Type | Primary Engines | Fallback |
|------------|-----------------|----------|
| General web | Bing, DDG, Brave | Startpage, Karmasearch |
| Academic | arXiv, Google Scholar | PubMed, Semantic Scholar, CORE |
| Code | GitHub, StackOverflow | GitLab, MDN, npm |
| News | Bing News, Reuters | DDG News |

**Note on Google**: Google aggressively blocks cloud/datacenter IP ranges. In CI environments, Google often returns CAPTCHA or 429 errors, causing engine suspension. The Reasoner's diverse engine list ensures queries still succeed via Bing/DDG/Brave.

---

## 4. Docker Deployment

### The Reasoner's Compose File

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    container_name: reasoner-searxng
    ports:
      - "8888:8080"          # Host:Container
    volumes:
      - searxng-data:/etc/searxng
      - ./.searxng-settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_BASE_URL=${SEARXNG_URL:-http://localhost:8888/}
      - SEARXNG_SECRET_KEY=${SEARXNG_SECRET_KEY}
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8080/ || exit 1"]
      interval: 5s
      timeout: 10s
      retries: 15
      start_period: 30s

volumes:
  searxng-data:
    name: reasoner-searxng-data
```

### Port Mapping

| Host | Container | Purpose |
|------|-----------|---------|
| `8888` | `8080` | SearXNG listens on 8080 inside the container; the host accesses it at `localhost:8888` |

### Volume Mounts

| Volume | Container Path | Purpose |
|--------|----------------|---------|
| `searxng-data` | `/etc/searxng` | Persistent config storage. On first boot, SearXNG initializes defaults here. |
| `.searxng-settings.yml` (bind mount) | `/etc/searxng/settings.yml` | **Overrides** default settings with Reasoner-specific config. Read-only (`:ro`). |

### First-Boot Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Image pull | 10-20s | Download `searxng/searxng:latest` layers |
| Container creation | 1-2s | Docker sets up volumes, network, env vars |
| Settings initialization | 5-10s | SearXNG reads mounted `settings.yml`, validates config |
| Engine preload | 3-5s | Loads engine definitions and checks connectivity |
| Server startup | 2-3s | Granian/Flask starts listening on port 8080 |
| **Total** | **20-40s** | Can be longer on slow CI runners |

### The CI Healthcheck Failure — Root Cause Analysis

**Original (broken) configuration:**
```yaml
healthcheck:
  test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

**Problem 1 — Wrong endpoint:** `/healthz` **does not exist** in SearXNG. Valid endpoints:

| Endpoint | Returns | Use Case |
|----------|---------|----------|
| `/` | Home page (HTML) | General availability check |
| `/search` | Search page | Functional test |
| `/search?format=json&q=test` | JSON results | API smoke test |
| `/stats` | Instance statistics | Monitoring |
| `/config` | Full configuration dump | Debugging |

**Problem 2 — Insufficient startup time:** `start_period: 10s` + `retries: 5` × `interval: 10s` = Docker gives up after ~35 seconds. But first boot takes 20-40s on CI runners.

**Fix applied:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:8080/ || exit 1"]
  interval: 5s
  timeout: 10s
  retries: 15
  start_period: 30s
```

Plus CI workflow polling loop:
```bash
for i in {1..30}; do
  if curl -sf http://localhost:8888/ > /dev/null; then break; fi
  sleep 2
done
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SEARXNG_URL` | Base URL for the instance | `http://localhost:8888` |
| `SEARXNG_SECRET_KEY` | Flask session signing key | (blank) |
| `SEARXNG_BASE_URL` | Public-facing URL for inbound links | `$SEARXNG_URL` |
| `SEARXNG_LIMITER` | Enable rate limiting | `false` |
| `SEARXNG_PUBLIC_INSTANCE` | Public instance features | `false` |

---

## 5. Search API

### JSON Endpoint

```bash
GET http://localhost:8888/search?q={query}&format=json&pageno=1
```

### Response Schema

```json
{
  "query": "quantum computing",
  "number_of_results": 10,
  "results": [
    {
      "title": "Quantum Computing - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Quantum_computing",
      "content": "Quantum computing is a type of computation that harnesses...",
      "engine": "wikipedia",
      "parsed_url": { "scheme": "https", "netloc": "en.wikipedia.org", ... },
      "publishedDate": "2024-01-15T00:00:00",
      "score": 1.0,
      "positions": [1, 2],
      "category": "general"
    }
  ],
  "answers": [],
  "corrections": [],
  "infoboxes": [],
  "suggestions": [],
  "unresponsive_engines": []
}
```

### Fields Consumed by Reasoner

| SearXNG Field | Reasoner Field | Usage |
|---------------|----------------|-------|
| `title` | `result["title"]` | Display heading |
| `url` | `result["url"]` | Link to source |
| `content` | `result["content"]` / `result["snippet"]` | Extract, truncated to 800 chars |
| `publishedDate` | `result["published_date"]` | Freshness scoring |
| `engine` | `result["source"]` | Which upstream engine provided it |
| `score` | (indirect) | SearXNG's internal ranking |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | **required** | Search query |
| `format` | string | `html` | Output format: `html`, `json`, `csv`, `rss` |
| `pageno` | int | `1` | Page number for pagination |
| `engines` | string | (all enabled) | Comma-separated engine names to query |
| `categories` | string | `general` | Comma-separated category names |
| `language` | string | `auto` | Language code (`en`, `en-US`, `de`, etc.) |
| `time_range` | string | (none) | `day`, `month`, `year` |
| `safesearch` | int | `0` | `0`=None, `1`=Moderate, `2`=Strict |
| `image_proxy` | bool | `false` | Proxy images through SearXNG |

### Example: Academic Search

```bash
curl 'http://localhost:8888/search?q=transformer+architecture&format=json&engines=arxiv,google_scholar&categories=science'
```

### Example: Code Search

```bash
curl 'http://localhost:8888/search?q=fastapi+authentication&format=json&engines=github,stackoverflow&categories=it'
```

---

## 6. Reasoner Integration Map

### Architecture Overview

```
Reasoner Pipeline
       |
       v
get_search_client() ──Factory──┐
                               |
         ┌─────────────────────┴─────────────────────┐
         |                                           |
         v                                           v
PerplexitySearchClient              DiscoveryClient (SearXNG)
(OpenRouter if key available)       (fallback)
         |                                           |
         v                                           v
  Perplexity Sonar API          SearXNG instance @ SEARXNG_URL
  (~$0.20-1.00/search)          (free, self-hosted)
```

### Layer 1: Core Search (`src/reasoner/core/search.py`)

#### `DiscoveryClient`

The primary SearXNG interface. ~120 lines of code handling:

```python
class DiscoveryClient:
    def __init__(self, base_url: str = DEFAULT_SEARXNG_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=TIMEOUTS.SEARCH_CLIENT)

    async def _fetch_page(self, query, pageno, num_results, categories, source_type):
        params = {"q": query, "format": "json", "pageno": pageno}
        if source_type and source_type != "general":
            engines = SOURCE_TYPE_ENGINES.get(source_type, [])
            if engines:
                params["engines"] = ",".join(engines)
        response = await self.client.get(f"{self.base_url}/search", params=params)
        data = response.json()
        raw = data.get("results", [])
        # Quality filtering, deduplication, freshness scoring
```

**Quality Pipeline per Result:**

1. **`_should_include_result()`** — Rejects:
   - File extensions: `.json`, `.xml`, `.csv`, `.zip`, `.pdf`
   - GitHub/GitLab raw blob URLs for data files
   - Very short snippets (< 50 chars)
   - Low-signal listicles ("Top 10...", "Ultimate Guide...")
   - NSFW content by keyword
   - Off-topic domains (Reddit, Twitter, Facebook, IMDb, etc.)

2. **`_normalize_url()`** — Deduplicates by stripping:
   - Protocol (`https://`)
   - `www.` prefix
   - Trailing slashes
   - URL fragments (`#section`)

3. **`_parse_freshness()`** — Scores recency:
   - `publishedDate` → days old → score in [0, 1]
   - Today = 1.0, 1 year = ~0.5, asymptotes to 0
   - Missing date = 0.5 (neutral, not penalized)

4. **`_bm25_score()`** — Relevance scoring:
   - Tokenizes query and result title/content
   - Title matches weighted 3× over content
   - Simplified BM25 without corpus IDF

#### `smart_search()`

High-level orchestrator (~90 lines):

1. **Query decomposition** — Uses lightweight LLM (`qwen3.5-9b` or `gemini-flash`) to break query into 2-3 focused sub-queries
2. **Parallel search** — Runs all sub-queries concurrently
3. **Cross-query deduplication** — Removes duplicates across sub-query results
4. **Composite scoring** — `0.8 × BM25 + 0.2 × freshness`
5. **Optional rerank** — If `COHERE_RERANK_ENABLED`, uses cross-encoder for higher precision

#### `get_search_client()` — Factory Pattern

```python
async def get_search_client(source_type=None):
    if settings.OPENROUTER_API_KEY:
        try:
            return PerplexitySearchClient(), source_type  # Premium path
        except ValueError:
            pass
    return await get_discovery_client(source_type=source_type)  # Free path
```

**Design rationale**: Perplexity when available (better synthesized answers), SearXNG as free, private, resilient fallback.

#### `PerplexitySearchClient`

Alternative search client using Perplexity Sonar via OpenRouter:
- Returns **synthesized answer** with citations, not raw links
- Single result per query (the synthesis)
- Cost: ~$0.20-1.00 per search depending on query complexity
- Better for: complex multi-step questions, when synthesis quality > source diversity

### Layer 2: Pipeline Mixins

#### `ArticlePipelineMixin._phase_article_retrieve()` (`article_pipeline.py`)

- Retrieves sources per subquestion from decomposition
- Uses `get_search_client()` (Perplexity-first, SearXNG-fallback)
- **Broad fallback**: If subquestions yield nothing, searches with the original `state.problem`
- Stores results in `state.writing_state["retrieved_sources"]`
- Gracefully degrades to knowledge-only synthesis if all retrieval fails

#### `ResearchMixin._phase_research_web_search()` (`research_mixin.py`)

- Deep iterative research (up to 3 iterations)
- Uses `get_discovery_client()` directly (SearXNG only)
- Each iteration: plan searches → execute → extract knowledge → synthesize
- LLM decides when to stop (`"done"` action)

#### `SearchMixin` (`search_mixin.py`)

- General search capabilities
- Deep Read: fetches full article content from retrieved URLs
- Fallback to general knowledge extraction when deep read fails

### Layer 3: API Routes

#### `src/reasoner/api/routes/context.py`

| Endpoint | Purpose | SearXNG Usage |
|----------|---------|---------------|
| `POST /context/vet` | Validate context relevance | Search for verifying claims |
| `POST /context/discover` | Discovery search | Direct SearXNG query |

#### `src/reasoner/api/__init__.py`

- Startup health validation includes SearXNG connectivity check
- Logs warning if SearXNG is unreachable

### Layer 4: Widgets

#### `src/reasoner/infrastructure/widgets/discover.py`

- Discover widget routes general queries through SearXNG
- Returns structured results for UI display

#### `src/reasoner/infrastructure/widgets/video_search.py` / `image_search.py`

- Video/image search widgets may use SearXNG with `categories=videos` or `categories=images`

### Layer 5: Sub-agents

#### `src/reasoner/subagents/search/gap_identifier.py`

- Compares retrieved sources against problem requirements
- Identifies knowledge gaps that need additional search

#### `src/reasoner/subagents/search/source_evaluator.py`

- Evaluates source quality, authority, and relevance
- Scores sources for downstream phases

### Layer 6: Configuration & Health

#### `src/reasoner/core/settings.py`

```python
SEARXNG_URL: str = "http://localhost:8888"
```

Configurable via `.env` file or environment variable.

#### `src/reasoner/core/constants.py`

```python
DEFAULT_SEARXNG_URL: str = "http://localhost:8888"
TIMEOUTS.SEARCH_CLIENT = 30.0  # HTTP timeout for search requests
```

#### `src/reasoner/core/health_validator.py`

- Startup check: `GET http://localhost:8888/` → expects 200 OK
- If unreachable, logs warning but does not block startup (Reasoner can still use Perplexity)

#### `src/reasoner/main.py`

- CLI flag: `--source-type` (`general`, `academic`, `social`, `news`, `code`)
- Controls which engine category SearXNG queries
- Direct search mode for standalone queries

#### `src/reasoner/start_all.py`

- Orchestrates full stack startup:
  1. SearXNG container (`docker compose -f docker-compose.searxng.yml up -d`)
  2. FastAPI backend (`uvicorn asgi:app`)
  3. Next.js frontend (`npm run dev`)

---

## 7. Failure Modes & Mitigations

| Failure | Symptom | Root Cause | Mitigation |
|---------|---------|------------|------------|
| **"ABORT — no sources found"** | Article pipeline stops | SearXNG down; all engines blocked; 403 Forbidden | `get_search_client()` Perplexity fallback; broad fallback search with original query |
| **HTTP 403 Forbidden** | API calls rejected | `json` not in `search.formats` in settings.yml | Add `json` to `.searxng-settings.yml` formats list |
| **Engine timeout / few results** | Low yield (< 3 results) | Google blocks cloud IP; DDG rate-limits | Diverse engines (Bing, Brave, Startpage); pagination to page 2 |
| **Container unhealthy in CI** | `docker compose up --wait` fails | Wrong healthcheck endpoint; short start_period | Fixed: `/` endpoint; `start_period: 30s`; CI polling loop |
| **SEARXNG_SECRET_KEY warning** | Log warning on startup | Env var not set | Optional for private instances; set for production |
| **All engines suspended** | Empty results for all queries | Previous errors caused auto-suspension | Restart container clears suspension state |
| **SearXNG unreachable** | Connection refused/timeout | Container not started; port conflict; firewall | Health validator detects; Perplexity fallback activates |

---

## 8. Value to the Reasoner

### Why SearXNG Is Essential

| Value | Explanation |
|-------|-------------|
| **Privacy** | User queries never hit Google/Bing directly. The SearXNG instance acts as a proxy, preventing IP-based tracking and query profiling. |
| **Resilience through Diversity** | If Google blocks the instance (common with cloud IPs), Bing + DDG + Brave + Startpage still respond. No single upstream failure can break the pipeline. |
| **Cost Control** | SearXNG is free. Perplexity Sonar costs ~$0.20-1.00 per search. For high-volume research pipelines processing 10-50 searches per run, SearXNG keeps costs near zero. |
| **Specialized Verticals** | Academic searches hit arXiv + Google Scholar + PubMed; code searches hit GitHub + StackOverflow. Hard to replicate with a single commercial API. |
| **Epistemic Diversity** | Different engines have different ranking algorithms and blind spots. Aggregating across them gives a more complete, less biased picture. |
| **No Rate Limits** | Unlike commercial APIs with tokens-per-minute caps, a private SearXNG instance handles hundreds of parallel queries (limited only by upstream engine tolerance). |
| **Self-Hosting = Control** | No API key management, no vendor lock-in, no service deprecation risk. The instance runs as long as Docker runs. |

### Configuration Best Practices

1. **Start from defaults**: Use `use_default_settings: true` in `settings.yml` and only override what you need. This ensures new engines and features are picked up automatically on upgrade.

2. **Pin the image tag**: Use `searxng/searxng:2026.4.24-...` instead of `latest` for reproducible deployments.

3. **Set a stable secret key**: Generate once with `openssl rand -hex 16` and persist it. Changing it invalidates image proxy HMACs.

4. **Keep `limiter: false`** for private instances. The limiter requires Valkey (Redis fork) — an unnecessary dependency for single-user or internal deployments.

5. **Never set `debug: true`** in production. It exposes the Werkzeug interactive debugger, a known remote code execution vector.

6. **Use `wget` for healthchecks**, not `curl`. The SearXNG Docker image is based on Alpine Linux, which includes `wget` but not `curl` by default.

7. **Engine naming**: Custom engine names must be lowercase and cannot contain underscores. SearXNG enforces this at load time with `sys.exit(1)` on fatal errors.

### When Perplexity Is Better

| Scenario | Winner | Reason |
|----------|--------|--------|
| Complex multi-step query | Perplexity | Synthesizes coherent answer with citations |
| No SearXNG instance running | Perplexity | Zero infrastructure requirement |
| Need synthesized summary | Perplexity | Returns prose, not raw links |
| High-stakes fact-checking | Perplexity | Better at cross-referencing and citing sources |
| Cost-insensitive premium tier | Perplexity | Higher quality, lower latency |
| Bulk source discovery | SearXNG | Free, parallel, 10-50 results per query |
| Privacy-critical deployment | SearXNG | No data leaves your infrastructure |
| Academic/code verticals | SearXNG | Specialized engines (arXiv, GitHub, StackOverflow) |
| Offline/air-gapped environments | SearXNG | Can run entirely on local network |

### The Optimal Architecture

The Reasoner's `get_search_client()` factory implements the correct priority:

1. **Try Perplexity first** (if `OPENROUTER_API_KEY` is set) — best quality
2. **Fall back to SearXNG** — free, private, resilient, diverse
3. **Pipeline handles empty results gracefully** — knowledge-only synthesis, no hard aborts

This gives users the best of both worlds without configuration complexity.

---

## 9. Appendix: All Touchpoints

### File-by-File Reference

| File | Lines | Role |
|------|-------|------|
| `src/reasoner/core/search.py` | 1-717 | **Primary interface.** `DiscoveryClient`, `PerplexitySearchClient`, `smart_search()`, `get_search_client()`, `get_discovery_client()`, query decomposition, BM25 ranking, freshness scoring, quality filtering. |
| `src/reasoner/application/mixins/article_pipeline.py` | ~308, ~367 | Article retrieval phase. Uses `get_search_client()` with broad fallback. |
| `src/reasoner/application/mixins/research_mixin.py` | ~28 | Deep research web search. Uses `get_discovery_client()` directly. |
| `src/reasoner/application/mixins/search_mixin.py` | ~183, ~431 | General search and deep read. Uses `get_discovery_client()`. |
| `src/reasoner/api/routes/context.py` | — | Context vetting and discovery endpoints. |
| `src/reasoner/api/__init__.py` | — | App factory; health validation includes SearXNG check. |
| `src/reasoner/api/serializers.py` | — | Response serialization for search results. |
| `src/reasoner/core/constants.py` | — | `DEFAULT_SEARXNG_URL`, `TIMEOUTS.SEARCH_CLIENT`. |
| `src/reasoner/core/settings.py` | — | `SEARXNG_URL` configuration from env. |
| `src/reasoner/core/health_validator.py` | — | Startup health check pings SearXNG. |
| `src/reasoner/core/aggregates/pipeline.py` | — | Pipeline aggregate root may reference search state. |
| `src/reasoner/infrastructure/widgets/discover.py` | — | Discover widget uses SearXNG. |
| `src/reasoner/infrastructure/widgets/video_search.py` | — | Video search widget. |
| `src/reasoner/infrastructure/widgets/image_search.py` | — | Image search widget. |
| `src/reasoner/infrastructure/widgets/registry.py` | — | Widget registry includes search widgets. |
| `src/reasoner/subagents/search/gap_identifier.py` | — | Identifies knowledge gaps in retrieved sources. |
| `src/reasoner/subagents/search/source_evaluator.py` | — | Evaluates source quality and authority. |
| `src/reasoner/main.py` | ~263 | CLI `--source-type` flag; direct search mode. |
| `src/reasoner/start_all.py` | — | Orchestrates SearXNG container startup. |
| `src/reasoner/server_check.py` | — | Server health checks. |
| `src/reasoner/pipeline.py` | ~54 | Imports `get_discovery_client` for web search. |
| `src/reasoner/phases/writing.py` | — | Writing phases may reference search results. |
| `src/reasoner/phases/_universal.py` | — | Universal phase utilities. |
| `src/reasoner/models.py` | — | `PipelineState` holds `web_discovery_results`. |
| `src/reasoner/domain/preset_registry.py` | — | Presets may configure search-heavy methods. |
| `docker-compose.searxng.yml` | — | SearXNG container definition. |
| `.searxng-settings.yml` | — | SearXNG configuration mount. |
| `.github/workflows/self-healing-ci.yml` | ~470 | CI SearXNG integration test job. |

### Environment Variables

| Variable | Set By | Used By |
|----------|--------|---------|
| `SEARXNG_URL` | `.env` | `core/settings.py`, `core/search.py` |
| `SEARXNG_SECRET_KEY` | `.env` | `docker-compose.searxng.yml` |
| `OPENROUTER_API_KEY` | `.env` | `get_search_client()` — triggers Perplexity path |

### Data Flow

```
User Request
    |
    v
HyperGate Agent ──decides──► needs web search?
    |                              |
    | no                           | yes
    |                              v
    |                      get_search_client()
    |                              |
                    ┌──────────────┴──────────────┐
                    |                             |
            OPENROUTER_API_KEY?            no key
                    |                             |
               yes  |                             |
                    v                             v
            PerplexitySearchClient      DiscoveryClient
                    |                             |
            Perplexity Sonar API        SearXNG @ SEARXNG_URL
                    |                             |
                    └──────────────┬──────────────┘
                                   |
                                   v
                         PipelineState.web_discovery_results
                                   |
                                   v
                    Article / Research / Search Mixins
                                   |
                                   v
                         Synthesis & Final Output
```

---

*End of report.*
