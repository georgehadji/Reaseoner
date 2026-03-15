# Reasoner - Implementation Guide

## Overview

This document provides detailed implementation information for the Reasoner architecture, including all reasoning methods, persistence options, and real-time features.

---

## Table of Contents

1. [Reasoning Methods](#reasoning-methods)
2. [Event Store Implementation](#event-store-implementation)
3. [WebSocket Integration](#websocket-integration)
4. [Snapshot Strategy](#snapshot-strategy)
5. [CQRS Read Models](#cqrs-read-models)
6. [Usage Examples](#usage-examples)

---

## Reasoning Methods

### 1. Multi-Perspective Method

**File:** `infrastructure/llm/new_pipeline.py`

**Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│                  Multi-Perspective Flow                      │
├─────────────────────────────────────────────────────────────┤
│  1. Classification (task type, language)                    │
│  2. Decomposition (causal chain, assumptions)               │
│  3. Context Vetting (search, verify sources)                │
│  4. Perspective Generation (PARALLEL):                       │
│     - Constructive (build strongest solution)               │
│     - Destructive (find every flaw)                         │
│     - Systemic (second/third-order effects)                 │
│     - Minimalist (simplest 80% solution)                    │
│  5. Critique & Scoring (evaluate all perspectives)          │
│  6. Stress Testing (edge cases, scenarios)                  │
│  7. Synthesis (final answer with meta-audit)                │
└─────────────────────────────────────────────────────────────┘
```

**Code Example:**
```python
async def _run_multi_perspective(self, state, aggregate, event_store):
    perspectives = [
        PerspectiveType.CONSTRUCTIVE,
        PerspectiveType.DESTRUCTIVE,
        PerspectiveType.SYSTEMIC,
        PerspectiveType.MINIMALIST,
    ]
    
    if self.parallel:
        # Run perspectives concurrently
        tasks = [
            self._generate_perspective(p, state, aggregate, event_store)
            for p in perspectives
        ]
        await asyncio.gather(*tasks)
    else:
        # Run sequentially
        for p in perspectives:
            await self._generate_perspective(p, state, aggregate, event_store)
```

**Events Generated:**
- `PhaseStarted` (perspective)
- `PerspectiveGenerated` (×4)
- `CandidateScored`
- `StressTestCompleted`

---

### 2. Debate Method

**Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│                      Debate Flow                             │
├─────────────────────────────────────────────────────────────┤
│  Round 0: Opening Statements                                 │
│    - Pro: Argument for position                              │
│    - Con: Argument against position                          │
│                                                              │
│  Round 1: Rebuttals                                          │
│    - Pro: Rebut con's opening                                │
│    - Con: Rebut pro's opening                                │
│                                                              │
│  Round 2: Rebuttals                                          │
│    - Pro: Rebut con's round 1                                │
│    - Con: Rebut pro's round 1                                │
│                                                              │
│  Closing Statements                                          │
│    - Pro: Final summary                                      │
│    - Con: Final summary                                      │
│                                                              │
│  Judge Decision                                              │
│    - Evaluate arguments                                      │
│    - Assign confidence score                                 │
│    - Declare winner                                          │
└─────────────────────────────────────────────────────────────┘
```

**Code Example:**
```python
async def _run_debate(self, state, aggregate, event_store):
    # Get providers for different roles
    pro_provider = self.router.get_provider_for_role("generator_1", ...)
    con_provider = self.router.get_provider_for_role("generator_2", ...)
    judge_provider = self.router.get_provider_for_role("meta_evaluator", ...)
    
    # Opening statements
    pro_opening = await self._debate_argument("pro", pro_provider, ...)
    con_opening = await self._debate_argument("con", con_provider, ...)
    
    # Rebuttals (2 rounds)
    for round_num in range(1, 3):
        pro_rebuttal = await self._debate_rebuttal("pro", pro_provider, ...)
        con_rebuttal = await self._debate_rebuttal("con", con_provider, ...)
    
    # Closing statements
    pro_closing = await self._debate_closing("pro", pro_provider, ...)
    con_closing = await self._debate_closing("con", con_provider, ...)
    
    # Judge decision
    judge_decision = await self._debate_judge(
        judge_provider, pro_closing, con_closing
    )
    
    state.debate_result = judge_decision
```

**Events Generated:**
- `DebateArgument` (opening ×2)
- `DebateRebuttal` (×4)
- `DebateClosing` (×2)
- `DebateJudgeDecision`

---

### 3. Research Method

**Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│                     Research Flow                            │
├─────────────────────────────────────────────────────────────┤
│  Iteration 1: Initial Search                                 │
│    - Plan search queries                                     │
│    - Execute searches (SearXNG)                              │
│    - Record results                                          │
│                                                              │
│  Iteration 2: Deep Dive                                      │
│    - Analyze gaps in current knowledge                       │
│    - Plan follow-up queries                                  │
│    - Execute targeted searches                               │
│                                                              │
│  Iteration 3: Verification                                   │
│    - Verify key claims                                       │
│    - Cross-reference sources                                 │
│    - Final analysis                                          │
│                                                              │
│  Synthesis                                                   │
│    - Analyze all findings                                    │
│    - Generate evidence-grounded answer                       │
└─────────────────────────────────────────────────────────────┘
```

**Code Example:**
```python
async def _run_research(self, state, aggregate, event_store):
    all_results = []
    
    # Iteration 1: Initial search
    search_plan = await self._research_plan_queries(...)
    
    for query in search_plan.get('queries', [state.problem]):
        client = await get_discovery_client(source_type=self.source_type)
        results = await client.search(query=query, domain=self.domain)
        all_results.extend(results)
    
    # Iterations 2-3: Deep dive
    for iteration in range(2, 4):
        follow_up_plan = await self._research_plan_followup(
            current_results=all_results
        )
        
        if not follow_up_plan.get('needs_more_search', False):
            break
        
        for query in follow_up_plan.get('queries', []):
            results = await client.search(query=query)
            all_results.extend(results)
    
    # Analyze findings
    analysis = await self._research_analyze_findings(all_results)
    state.research_analysis = analysis
```

**Events Generated:**
- `ResearchPlan`
- `ResearchIteration` (×3)
- `ResearchAnalysis`
- `ContextFetched` (×N)

---

### 4. Socratic Method

**Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Socratic Flow                             │
├─────────────────────────────────────────────────────────────┤
│  1. Initial Position                                         │
│     "What is your position on X?"                            │
│                                                              │
│  2. Elenchus (Cross-Examination)                             │
│     - Generate probing questions                             │
│     - Expose contradictions                                  │
│     - Challenge assumptions                                  │
│                                                              │
│  3. Aporia (Recognition of Ignorance)                        │
│     - Acknowledge gaps in understanding                      │
│     - Recognize complexity                                   │
│                                                              │
│  4. Maieutics (Midwifery)                                    │
│     - Draw out deeper insights                               │
│     - Build new understanding                                │
│                                                              │
│  5. Refined Understanding                                    │
│     - Synthesize insights                                    │
│     - Nuanced conclusion                                     │
└─────────────────────────────────────────────────────────────┘
```

**Code Example:**
```python
async def _run_socratic(self, state, aggregate, event_store):
    # Step 1: Initial position
    initial_position = await self._socratic_elicit_position(...)
    
    # Step 2: Elenchus
    elenchus_questions = await self._socratic_generate_questions(
        position=initial_position
    )
    
    # Step 3: Aporia
    aporia = await self._socratic_induce_aporia(
        position=initial_position,
        questions=elenchus_questions,
    )
    
    # Step 4: Maieutics
    maieutic_insights = await self._socratic_maieutics(aporia=aporia)
    
    # Step 5: Refined understanding
    refined = await self._socratic_synthesis(
        dialogue=state.socratic_dialogue
    )
    
    state.socratic_result = refined
```

**Events Generated:**
- `SocraticPosition`
- `SocraticQuestions`
- `SocraticAporia`
- `SocraticInsights`
- `SocraticUnderstanding`

---

## Event Store Implementation

### SQLite (Default)

**File:** `infrastructure/persistence/event_store.py`

**Schema:**
```sql
-- Events table (append-only)
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    payload JSONB NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Aggregates table (current state)
CREATE TABLE aggregates (
    aggregate_id TEXT PRIMARY KEY,
    current_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    problem TEXT,
    preset TEXT,
    method TEXT
);

-- Snapshots table (performance)
CREATE TABLE snapshots (
    aggregate_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    state JSONB NOT NULL
);
```

**Usage:**
```python
from infrastructure.persistence import get_event_store

event_store = get_event_store()

# Save events
await event_store.save_events([event1, event2])

# Get events for aggregate
events = await event_store.get_events("pipeline-123")

# List pipelines
pipelines = await event_store.list_pipelines(limit=50, status="completed")
```

### PostgreSQL (Production)

**File:** `infrastructure/persistence/postgres_store.py`

**Configuration:**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/reasoner
USE_POSTGRES=true
POSTGRES_POOL_SIZE=20
USE_READ_REPLICA=true
READ_REPLICA_URL=postgresql://user:pass@replica:5432/reasoner
```

**Features:**
- Table partitioning by aggregate type
- Full-text search on event payloads
- Read replica support
- Connection pooling (asyncpg)

**Usage:**
```python
from infrastructure.persistence import initialize_postgres_store

event_store = await initialize_postgres_store(
    connection_string="postgresql://...",
    pool_size=20,
)

# Full-text search
results = await event_store.search_events("AI reasoning", limit=50)
```

---

## WebSocket Integration

**File:** `infrastructure/websocket/manager.py`

### Connection

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Or connect to specific pipeline
const ws = new WebSocket('ws://localhost:8000/ws/pipeline/pipeline-123');
```

### Messages

**Client → Server:**
```javascript
// Subscribe to pipeline
ws.send(JSON.stringify({
    type: 'subscribe',
    pipeline_id: 'pipeline-123'
}));

// Unsubscribe
ws.send(JSON.stringify({
    type: 'unsubscribe',
    pipeline_id: 'pipeline-123'
}));

// Ping (heartbeat)
ws.send(JSON.stringify({ type: 'ping' }));
```

**Server → Client:**
```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
        case 'event':
            // Domain event (phase completed, etc.)
            console.log('Event:', msg.data);
            break;
        case 'progress':
            // Phase progress update
            console.log('Progress:', msg.data.phase, msg.data.status);
            break;
        case 'complete':
            // Pipeline finished
            console.log('Result:', msg.data.result);
            break;
        case 'error':
            // Error occurred
            console.error('Error:', msg.data.error);
            break;
        case 'pong':
            // Heartbeat response
            break;
    }
};
```

### API Endpoint

```python
@app.websocket("/ws")
async def websocket_connect(websocket: WebSocket, pipeline_id: str = None):
    await websocket_endpoint(websocket, pipeline_id)
```

---

## Snapshot Strategy

**File:** `infrastructure/persistence/snapshots.py`

### Configuration

```python
from infrastructure.persistence import SnapshotStrategy

strategy = SnapshotStrategy(
    version_interval=10,        # Snapshot every 10 events
    time_interval_seconds=60,   # Or every 60 seconds
    phase_based=True,           # Or after each phase
    event_threshold=100,        # Or when events > 100
)
```

### Performance Comparison

| Scenario | Without Snapshot | With Snapshot |
|----------|-----------------|---------------|
| Events to replay | 100 | 10 (last 10 since snapshot) |
| Reconstruction time | 500ms | 50ms |
| Memory usage | High | Low |

### Usage

```python
from infrastructure.persistence import SnapshotManager

snapshot_manager = SnapshotManager(event_store)

# Create snapshot
await snapshot_manager.strategy.create_snapshot(aggregate, event_store)

# Load with snapshot
aggregate = await snapshot_manager.load_aggregate_with_snapshot("pipeline-123")
```

---

## CQRS Read Models

**File:** `infrastructure/persistence/snapshots.py`

### Read Model Projections

```python
from infrastructure.persistence import ReadModelProjection

projection = ReadModelProjection(event_store)

# Project pipeline list
await projection.project_pipeline_list()

# Project statistics
await projection.project_pipeline_stats()
```

### Query Read Models

```python
# Get cached pipeline list
pipeline_list = await projection.get_pipeline_list(limit=50, offset=0)

# Get cached statistics
stats = await projection.get_pipeline_stats()
```

### Event-Driven Updates

```python
from application.event_bus import handle_event
from core.events.domain_events import EventType

@handle_event(EventType.PIPELINE_COMPLETED)
async def update_on_completion(event):
    """Auto-update read models when pipeline completes."""
    await projection.project_pipeline_list()
    await projection.project_pipeline_stats()
```

---

## Usage Examples

### Run Pipeline with New Architecture

```python
from infrastructure.llm.new_pipeline import NewARAPipeline
from infrastructure.persistence import get_event_store
from llm import ProviderRouter

# Initialize components
router = ProviderRouter()
event_store = get_event_store()

# Create pipeline
pipeline = NewARAPipeline(
    router=router,
    preset_name="max-quality",
    top_k=2,
    parallel=True,
)

# Create aggregate
from core.aggregates.pipeline import PipelineAggregate
import uuid

aggregate = PipelineAggregate(aggregate_id=str(uuid.uuid4()))

# Run pipeline
state = await pipeline.run_with_aggregate(
    problem="What is the best approach for X?",
    aggregate=aggregate,
    event_store=event_store,
)
```

### Execute Widget

```python
from infrastructure.widgets import get_widget_registry

registry = get_widget_registry()

# Auto-detect and execute
results = await registry.auto_execute("weather in Athens")

if results:
    print(f"Weather: {results[0].data}")
```

### WebSocket Client (Python)

```python
import asyncio
import websockets

async def listen_to_pipeline():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        # Subscribe
        await ws.send('{"type": "subscribe", "pipeline_id": "xxx"}')
        
        # Listen for events
        async for message in ws:
            data = json.loads(message)
            print(f"Received: {data['type']}", data.get('data'))

asyncio.run(listen_to_pipeline())
```

---

## Testing

### Run Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Specific modules
python -m pytest tests/test_domain_events.py -v
python -m pytest tests/test_aggregates.py -v
python -m pytest tests/test_event_bus.py -v
python -m pytest tests/test_widgets.py -v
```

### Test Fixtures

```python
@pytest.fixture
def sample_pipeline_state():
    return {"problem": "Test", "preset": "test", "method": "test"}

@pytest.fixture
def sample_llm_messages():
    return [
        Message(role=MessageRole.SYSTEM, content="You are helpful."),
        Message(role=MessageRole.USER, content="Hello"),
    ]
```

---

## Migration from Legacy

### Step 1: Use New Pipeline

```python
# Old
from pipeline import ARAPipeline
pipeline = ARAPipeline(router, preset_name)
state = await pipeline.run(problem)

# New
from infrastructure.llm.new_pipeline import NewARAPipeline
from core.aggregates.pipeline import PipelineAggregate

pipeline = NewARAPipeline(router, preset_name)
aggregate = PipelineAggregate(aggregate_id="xxx")
state = await pipeline.run_with_aggregate(problem, aggregate, event_store)
```

### Step 2: Enable Event Persistence

```python
# Add to api.py startup
from infrastructure.persistence import get_event_store

event_store = get_event_store()
```

### Step 3: Add WebSocket Support

```python
# Frontend
const ws = new WebSocket('ws://localhost:8000/ws');
```

---

## Performance Tuning

### SQLite Optimization

```python
# Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;

# Increase cache size
PRAGMA cache_size=-64000;  # 64MB
```

### PostgreSQL Optimization

```python
# Use connection pooling
event_store = await initialize_postgres_store(
    pool_size=20,
    use_read_replica=True,
)
```

### Snapshot Tuning

```python
# Adjust based on your workload
strategy = SnapshotStrategy(
    version_interval=5,     # More frequent for long pipelines
    time_interval_seconds=30,  # Or time-based
    phase_based=True,       # Always snapshot after phases
)
```

---

## Troubleshooting

### Event Store Issues

```python
# Check event store stats
stats = await event_store.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Total pipelines: {stats['total_aggregates']}")

# Delete problematic pipeline
await event_store.delete_aggregate("pipeline-xxx")
```

### WebSocket Connection Issues

```python
# Check WebSocket stats
from infrastructure.websocket import get_websocket_manager

manager = get_websocket_manager()
print(f"Active connections: {manager.get_connection_count()}")
print(f"Subscriptions: {manager.subscriptions}")
```

### Snapshot Issues

```python
# Force snapshot
await snapshot_manager.strategy.create_snapshot(aggregate, event_store)

# Check snapshot
version, state = await snapshot_manager.strategy.load_snapshot(
    aggregate.aggregate_id, event_store
)
```

---

## SRE Bug Fix Log (2026-03-15)

Two SRE passes were run against the `security-fixes-implementation` branch. All findings fixed and pushed.

### Pass 1 — `pipeline.py`, `models.py`, `phases.py`, `main.py`

| ID | Severity | File | Root Cause | Fix |
|----|----------|------|-----------|-----|
| BUG-001 | Critical | `pipeline.py` | 5 `asyncio.gather()` calls without `return_exceptions=True` — any single LLM failure silently emptied the entire phase result list | Added `return_exceptions=True` + per-task exception handling to all 5 gather sites |
| BUG-002 | Critical | `models.py` | `CritiqueScore` missing `confidence_vs_accuracy_penalty` field present in LLM prompt — `TypeError` on every phase-3 run | Added `confidence_vs_accuracy_penalty: float = 0.0` |
| BUG-003 | High | `pipeline.py` | `SolutionCandidate(content=data.get("core_analysis"))` — `None` propagates to `c.content[:400]` | `data.get(...) or ""` and `data.get(...) or []` |
| BUG-004 | High | `pipeline.py` | `_phase_debate_rebuttal` indexed `statements[0/1]` without length guard — `IndexError` when opening partial | Early-return guard if `len(statements) < 2` |
| BUG-005 | High | `phases.py` | `CROSS_VERIFICATION_SYSTEM` + `cross_verification_prompt()` called from pipeline but undefined — recovery feature dead | Added both to `phases.py` |
| BUG-006 | High | `pipeline.py` | Missing `import json` + `from dataclasses import asdict`; `.to_dict()` on plain dataclass | Added imports; replaced `.to_dict()` with `asdict()` |
| BUG-007 | Critical | `main.py` | 7 unterminated f-string/string literals — `SyntaxError` on import, CLI completely broken | Fixed with `\n` escape sequences |

### Pass 2 — `api.py`, `renderer.py`

| ID | Severity | File | Root Cause | Fix |
|----|----------|------|-----------|-----|
| BUG-008 | Critical | `api.py` | `_cancel_flag: bool` global shared across all concurrent SSE generators | Per-run `_cancelled_runs: dict[str, bool]` keyed by `uuid4()` |
| BUG-009 | High | `renderer.py` | TOCTOU: `.get("key")` check then `["key"]` subscript — 4 locations in Scientific/Socratic renderers | Stored `.get()` result in local variable before iterating |

### Pass 3 — `api.py`, `core/search.py`, `llm.py`

| ID | Severity | File | Root Cause | Fix |
|----|----------|------|-----------|-----|
| BUG-010 | High | `api.py` | `_load_cache` uncaught `JSONDecodeError` on corrupt files; `_save_cache` non-atomic `write_text()` could leave truncated files on crash | Added try/except + corrupt-file deletion for reads; `.tmp` write + `Path.replace()` atomic rename for writes |
| BUG-011 | Medium | `core/search.py` | `reset_discovery_client()` nulled global reference without calling `aclose()`, leaking httpx connection pool and file descriptors | Save old client before nulling; schedule `aclose()` on running loop (or `asyncio.run()` fallback for sync callers) |
| BUG-012 | High | `llm.py` | `build_provider()` accepted empty string from `os.environ.get(key, "")` as valid API key; error only surfaced at first SDK call with opaque auth message | Added early `ValueError` if `key` is empty and provider is not `is_local`; Ollama exempt |
