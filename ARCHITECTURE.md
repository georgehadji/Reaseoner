# Reasoner - Software Architecture

## Overview

Reasoner implements a **Hexagonal Architecture** (Ports & Adapters) combined with **Event Sourcing** and **CQRS** (Command Query Responsibility Segregation) patterns. This architecture provides:

- **Provider Independence**: LLM providers can be swapped without changing domain logic
- **Audit Trail**: Full event history for debugging and resume capability
- **Scalability**: Separate read/write models for optimized performance
- **Extensibility**: Plugin system for widgets and new features
- **Testability**: Mockable ports for isolated unit testing
- **Production-Ready**: PostgreSQL support, WebSocket real-time updates, snapshot optimization

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Web UI      │  │    CLI       │  │  WebSocket + REST    │  │
│  │  (vanilla JS)│  │  (main.py)   │  │  (FastAPI + SSE)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (CQRS)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Command/Query Handlers                       │   │
│  │  RunPipeline │ GetHistory │ ExecuteWidget │ HealthCheck   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Event Bus (Publish-Subscribe)                │   │
│  │  PhaseStarted │ PipelineCompleted │ WidgetExecuted       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Read Model Projections                       │   │
│  │  PipelineList │ PipelineStats │ WidgetCatalog            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Reasoning Core (Pure)                     │   │
│  │  7 Methods: Multi-Perspective, Debate, Jury, Research,    │   │
│  │  Scientific, Socratic, Iterative │ Pure Phase Functions   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               Event-Sourced Aggregates                    │   │
│  │  PipelineAggregate ← [28+ event types]                    │   │
│  │  WidgetAggregate ← [WidgetDetected, WidgetExecuted]       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Domain Events (28 types)                  │   │
│  │  Pipeline(6) + Context(3) + Method(9) + Widget(3) + ...   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Snapshot Strategy                         │   │
│  │  Version-based │ Time-based │ Phase-based                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ LLM Ports  │  │ Search     │  │ Memory   │  │ Widget     │  │
│  │ (11 prov.) │  │ (SearXNG)  │  │ (Neuro)  │  │ (6 types)  │  │
│  └────────────┘  └────────────┘  └──────────┘  └────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐  │
│  │ SQLite     │  │ PostgreSQL │  │ WebSocket + Event Bus    │  │
│  │ (default)  │  │ (prod)     │  │ (real-time streaming)    │  │
│  └────────────┘  └────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Domain Layer (Core)

### Domain Events

All state changes are represented as immutable events. Events are the source of truth for the system.

#### Event Types (18 Total)

```python
# Pipeline Lifecycle
EventType.PIPELINE_STARTED      # Pipeline execution started
EventType.PHASE_STARTED         # Phase execution started
EventType.PHASE_COMPLETED       # Phase completed successfully
EventType.PHASE_FAILED          # Phase execution failed
EventType.PIPELINE_COMPLETED    # Pipeline completed successfully
EventType.PIPELINE_FAILED       # Pipeline execution failed

# Context Management
EventType.CONTEXT_FETCHED       # Context fetched from external source
EventType.CONTEXT_VETTED        # Context vetting completed
EventType.SOURCE_ADDED          # New source added to context

# Method-Specific
EventType.PERSPECTIVE_GENERATED # Perspective solution generated
EventType.CANDIDATE_SCORED      # Candidate solution scored
EventType.STRESS_TEST_COMPLETED # Stress test completed

# Widget System
EventType.WIDGET_DETECTED       # Widget auto-detected from query
EventType.WIDGET_EXECUTED       # Widget executed successfully
EventType.WIDGET_FAILED         # Widget execution failed

# Memory (Neuro)
EventType.MEMORY_STORED         # Memory stored in Neuro system
EventType.MEMORY_RECALLED       # Memory recalled from Neuro system

# Error Handling
EventType.ERROR_OCCURRED        # Error occurred during execution
EventType.RETRY_ATTEMPTED       # Retry attempt for failed operation
```

#### Event Structure

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str           # UUID
    event_type: EventType   # Enum type
    timestamp: float        # Unix timestamp
    aggregate_id: str       # Aggregate this event belongs to
    version: int            # Event version for concurrency
    metadata: dict[str, Any] # Additional data
```

### Aggregates

Aggregates are event-sourced state containers. State is derived by applying events sequentially.

#### PipelineAggregate

```python
class PipelineAggregate(Aggregate):
    """
    Event-sourced aggregate for pipeline execution.
    
    State is reconstructed from events:
    - PipelineStarted → status = "running"
    - PhaseCompleted → add to phase_results, update tokens
    - PipelineCompleted → status = "completed", set solution
    """
    
    def apply(self, event: DomainEvent) -> None:
        if isinstance(event, PipelineStarted):
            self._apply_pipeline_started(event)
        elif isinstance(event, PhaseCompleted):
            self._apply_phase_completed(event)
        # ... handle all event types
    
    def can_resume(self) -> bool:
        """Check if pipeline can be resumed."""
        return self._state_data.status in ("running", "pending")
    
    def get_last_phase(self) -> str | None:
        """Get last completed phase for resume."""
        if not self._state_data.phase_results:
            return None
        return self._state_data.phase_results[-1]['phase']
```

#### Aggregate Base Class

```python
class Aggregate:
    """Base class for all aggregates."""
    
    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self.version = 0
        self._pending_events: list[DomainEvent] = []
    
    def apply(self, event: DomainEvent) -> None:
        """Apply event to update state."""
        # Version check for optimistic concurrency
        if event.version != self.version + 1:
            raise ValueError("Version mismatch")
        self._apply_event(event)
        self.version = event.version
    
    def record_event(self, event: DomainEvent) -> None:
        """Record new event for persistence."""
        self._pending_events.append(event)
        self.apply(event)
    
    def load_from_history(self, history: list[DomainEvent]) -> None:
        """Rebuild state from event history."""
        for event in sorted(history, key=lambda e: e.version):
            self.apply(event)
```

---

## Application Layer (CQRS)

### Commands (Write Operations)

Commands represent intentions to change state. They produce domain events.

```python
# Pipeline Commands
RunPipelineCommand        # Run reasoning pipeline
ResumePipelineCommand     # Resume paused/failed pipeline
StopPipelineCommand       # Stop running pipeline
ClearPipelineCacheCommand # Clear pipeline cache

# Widget Commands
ExecuteWidgetCommand      # Execute a widget
RefreshWidgetCommand      # Refresh widget data

# Memory Commands
StoreMemoryCommand        # Store conversation in memory
ClearMemoryCommand        # Clear memory

# History Commands
DeleteHistoryCommand      # Delete history entry
ClearHistoryCommand       # Clear all history
```

### Queries (Read Operations)

Queries return read-optimized DTOs (not domain models).

```python
# Pipeline Queries
GetPipelineStatusQuery    # Get pipeline execution status
GetPipelineHistoryQuery   # Get pipeline event history
ListPipelinesQuery        # List recent pipelines

# Widget Queries
GetWidgetStateQuery       # Get widget state
ListAvailableWidgetsQuery # List available widgets

# History Queries
GetHistoryQuery           # Get search history
GetHistoryEntryQuery      # Get specific history entry

# System Queries
ListPresetsQuery          # List available presets
ListModelsQuery           # List available models
HealthCheckQuery          # Check system health
```

### Event Bus

The event bus distributes domain events to subscribers for async processing.

```python
class EventBus:
    """Publish-subscribe event distribution."""
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to specific event type."""
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events."""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish event to all subscribers (concurrent execution)."""
```

#### Example Subscribers

```python
@handle_event(EventType.PHASE_COMPLETED)
async def on_phase_completed(event: DomainEvent):
    """Log phase completion."""
    logger.info(f"Phase {event.phase_name} completed")

@handle_all_events()
async def track_all_events(event: DomainEvent):
    """Track metrics for all events."""
    metrics.increment(f"events.{event.event_type.value}")
```

---

## Infrastructure Layer

### LLM Provider Ports

The LLM port defines the interface that all providers must implement.

```python
@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers (Hexagonal Port)."""
    
    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Complete a conversation."""
    
    async def complete_stream(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream completion."""
```

### Provider Adapters

| Adapter | Provider | Models |
|---------|----------|--------|
| `AnthropicAdapter` | Anthropic | Claude 3/4 Opus, Sonnet, Haiku |
| `OpenAIAdapter` | OpenAI | GPT-4o, GPT-4 Turbo, GPT-3.5 |
| `XAIAdapter` | xAI | Grok |
| `DeepSeekAdapter` | DeepSeek | DeepSeek Chat |
| `QwenAdapter` | Alibaba | Qwen Plus |
| `KimiAdapter` | Moonshot | Kimi |
| `GLMAdapter` | ZhipuAI | GLM-4 |
| `MiniMaxAdapter` | MiniMax | ABAB |
| `GoogleAdapter` | Google | Gemini 2.0 Flash, 1.5 Pro/Flash |
| `PerplexityAdapter` | Perplexity | Sonar, Sonar Pro, Deep Research |
| `OllamaAdapter` | Ollama | Local LLMs (llama3, mistral, etc.) |

### Widget System

Widgets are plugins that auto-detect and execute based on user queries.

#### Widget Protocol

```python
@runtime_checkable
class Widget(Protocol):
    """Protocol for widgets (Hexagonal Port)."""
    
    name: str
    widget_type: WidgetType
    trigger_patterns: list[re.Pattern]
    description: str
    
    async def detect(self, query: str) -> bool:
        """Detect if widget should activate."""
    
    async def execute(self, params: dict[str, Any]) -> WidgetResult:
        """Execute widget logic."""
```

#### Widget Registry

```python
class WidgetRegistry:
    """Central registry for all widgets."""
    
    def register(self, widget: Widget) -> None:
        """Register a widget."""
    
    async def detect_widgets(self, query: str) -> list[WidgetDetectionResult]:
        """Detect widgets for a query."""
    
    async def execute_widget(
        self,
        widget_name: str,
        params: dict[str, Any],
    ) -> WidgetResult:
        """Execute a widget by name."""
```

#### Available Widgets

| Widget | Type | API | Trigger Patterns |
|--------|------|-----|------------------|
| `WeatherWidget` | WEATHER | Open-Meteo | "weather in Athens" |
| `StockWidget` | STOCKS | Yahoo Finance | "stock price AAPL", "$TSLA" |
| `CalculatorWidget` | CALCULATOR | mathjs | "2+2", "calculate 5*7" |
| `DiscoverWidget` | DISCOVER | SearXNG News | "trending in tech" |
| `ImageSearchWidget` | IMAGE_SEARCH | SearXNG Images | "show images of cats" |
| `VideoSearchWidget` | VIDEO_SEARCH | SearXNG Videos | "search videos python" |

---

## Design Patterns

### 1. Hexagonal Architecture (Ports & Adapters)

**Purpose**: Decouple domain logic from external dependencies.

**Implementation**:
- **Ports**: `LLMProvider`, `Widget`, `SearchClient` protocols
- **Adapters**: `AnthropicAdapter`, `WeatherWidget`, `SearXNGAdapter`
- **Benefit**: Swap providers without changing domain code

### 2. Event Sourcing

**Purpose**: Full audit trail, temporal queries, resume capability.

**Implementation**:
- All state changes are immutable events
- Aggregates rebuild state from event history
- Event store persists all events

**Benefits**:
- Debug: Replay events to reproduce bugs
- Resume: Restart pipeline from any phase
- Audit: Complete history of every decision

### 3. CQRS (Command Query Responsibility Segregation)

**Purpose**: Optimize read and write operations separately.

**Implementation**:
- **Commands**: Write operations that produce events
- **Queries**: Read operations that return DTOs
- **Handlers**: Separate logic for commands vs queries

**Benefits**:
- Optimized read models (denormalized)
- Independent scaling
- Clear separation of concerns

### 4. Plugin System

**Purpose**: Extensible widget architecture.

**Implementation**:
- `Widget` protocol defines interface
- `WidgetRegistry` manages lifecycle
- Auto-detection via regex patterns

**Benefits**:
- Add widgets without core changes
- Third-party widget development
- Runtime widget registration

---

## Testing Strategy

### Test Pyramid

```
        ┌─────────────┐
        │   E2E       │  Few tests (full pipeline)
       ─┼─────────────┼─
      / │ Integration │ \  More tests (adapters)
     ───┼─────────────┼───
    /   │   Unit      │   \  Most tests (pure functions)
   ─────┴─────────────┴─────
```

### Test Categories

| Category | Location | Coverage |
|----------|----------|----------|
| **Unit Tests** | `tests/test_domain_events.py` | Events, immutability, factory |
| **Unit Tests** | `tests/test_aggregates.py` | Event sourcing, version tracking |
| **Unit Tests** | `tests/test_event_bus.py` | Pub-sub, error isolation |
| **Unit Tests** | `tests/test_widgets.py` | Protocol, registry, detection |
| **Integration** | `tests/integration/` | Adapter tests (LLM, Search) |
| **E2E** | `tests/e2e/` | Full pipeline execution |

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

@pytest.fixture
def mock_llm_response():
    return LLMResponse(
        content="Mock response",
        model_used="test-model",
        tokens_prompt=50,
        tokens_completion=100,
    )
```

---

## Data Flow

### Pipeline Execution Flow

```
User Input (CLI/Web/API)
    ↓
[API Controller] ──→ Create RunPipelineCommand
    ↓
[Command Handler]
    ↓
[PipelineAggregate] ──→ Record PipelineStarted event
    ↓
[Phase Executor] ──→ LLM Provider Port
    ↓
[LLM Adapter] ──→ External API (Anthropic/OpenAI/etc.)
    ↓
[Phase Executor] ──→ Record PhaseCompleted event
    ↓
[Event Bus] ──→ Notify subscribers
    ↓
[PipelineAggregate] ──→ Record PipelineCompleted event
    ↓
[Event Store] ──→ Persist events
    ↓
[Projection] ──→ Update read models
    ↓
SSE Stream → Client (UI/CLI)
```

### Widget Auto-Detection Flow

```
User Query: "What's the weather in Athens?"
    ↓
[WidgetRegistry.detect_widgets()]
    ↓
[Pattern Matching] ──→ Match "weather in (.+)"
    ↓
[WeatherWidget] ──→ confidence = 0.85
    ↓
[WidgetRegistry.execute_widget()]
    ↓
[WeatherWidget._execute_impl()]
    ↓
[Open-Meteo API] ──→ HTTP GET
    ↓
[WidgetResult] ──→ {temperature: 25, condition: "Sunny"}
    ↓
[UI Renderer] ──→ Render weather widget
```

---

## Configuration

### Environment Variables

```bash
# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
XAI_API_KEY=...
DEEPSEEK_API_KEY=...
DASHSCOPE_API_KEY=...      # Qwen
MOONSHOT_API_KEY=...       # Kimi
ZHIPUAI_API_KEY=...        # GLM
MINIMAX_API_KEY=...

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434

# SearXNG (widgets)
SEARXNG_API_URL=http://localhost:8080
```

### Dependency Injection

```python
# Provider Router (Factory Pattern)
class ProviderRouter:
    def get_provider(self, model_id: str) -> LLMProvider:
        """Factory method to create provider instance."""
        entry = _REGISTRY.get(model_id)
        return build_provider(entry)

# Widget Registry (Singleton Pattern)
_registry: WidgetRegistry | None = None

def get_widget_registry() -> WidgetRegistry:
    """Get or create global registry instance."""
    global _registry
    if _registry is None:
        _registry = WidgetRegistry()
        _register_default_widgets(_registry)
    return _registry
```

---

## Performance Considerations

### Caching Strategy

1. **L1 Cache**: In-memory (fastest, per-request)
2. **L2 Cache**: Redis/shared (fast, cross-request)
3. **L3 Cache**: File system/SQLite (persistent)

### Async Execution

- All I/O operations are async (LLM calls, HTTP requests, file I/O)
- Event handlers execute concurrently
- Widget detection runs in parallel

### Rate Limiting

- Token bucket algorithm for API rate limits
- Circuit breaker pattern for fault tolerance
- Exponential backoff with jitter for retries

---

## Security

### Input Validation

- Pydantic models for request validation
- Field validators for complex constraints
- Sanitization for logging

### API Security

- CORS middleware with restrictive origins
- Security headers (HSTS, X-Frame-Options, CSP)
- Rate limiting per IP/user

### Data Isolation

- Agent IDs for tenant isolation in Neuro
- Encrypted storage for sensitive data
- API key management via environment variables

---

## Migration Guide

### From Legacy to New Architecture

1. **Phase 1**: Create domain events and aggregates
2. **Phase 2**: Implement LLM provider ports
3. **Phase 3**: Create CQRS command/query handlers
4. **Phase 4**: Migrate pipeline to use ports
5. **Phase 5**: Implement event persistence
6. **Phase 6**: Add widget plugin system

### Backward Compatibility

- Legacy `llm.py` remains functional during migration
- New adapters coexist with legacy providers
- Gradual migration path for each component

---

## Reliability Invariants (enforced as of 2026-03-15)

These invariants were established after an SRE audit on branch `security-fixes-implementation`. Any future code must uphold them:

### Concurrency
- **All `asyncio.gather()` calls use `return_exceptions=True`** and iterate results with `isinstance(r, Exception)` guards. A single failed task must never silently drop the entire batch or raise unhandled.
- **Pipeline cancellation is per-run, not global.** `api.py` uses `_cancelled_runs: dict[str, bool]` keyed by `uuid4()`. The `POST /api/stop` endpoint targets only `_active_run_id`. A global boolean flag is forbidden.

### Data Integrity
- **Dataclass fields must match LLM prompt schemas.** If a prompt instructs the LLM to output a field (e.g. `confidence_vs_accuracy_penalty`), that field must exist in the corresponding dataclass with an appropriate default. Missing fields cause `TypeError` at construction time.
- **`dict.get()` results must be stored before use.** The pattern `if d.get(k)` followed by `d[k]` is a TOCTOU bug. Store: `val = d.get(k) or default; if val: use(val)`.
- **Optional string/list fields must default to `""` / `[]`, not `None`.** Fields typed as `str` or `list[T]` must not hold `None`; downstream slice/iteration will raise `TypeError`.

### Error Handling
- **All phase prompt functions referenced from `pipeline.py` must exist in `phases.py`** before the call site is added. Use `hasattr(phases, "fn_name")` in tests if needed.
- **Recovery paths must have all symbols defined** before they are wired up. Dead code that calls undefined symbols must be completed or removed.

### CLI / Entry Point
- **No string/f-string literals may contain literal newlines.** Use `\n` escape sequences. Literal newlines inside quotes are a `SyntaxError` in Python 3.12+ that breaks the CLI on startup.

### API Keys & Providers
- **`build_provider()` must raise immediately if a required API key is empty.** `os.environ.get(key, "")` silently returns an empty string; an empty key passes to SDK constructors without error but fails at first call. Guard: `if not key and not cfg.get("is_local"): raise ValueError(...)`.
- **Local providers (Ollama) are exempt from the key guard** — they accept any dummy key string.

### Cache / Persistence
- **All cache reads must catch `JSONDecodeError`** and delete the corrupt file to allow regeneration.
- **All cache writes must be atomic.** Write to a `.tmp` sibling file, then rename with `Path.replace()` (wraps `os.replace()`, atomic on both POSIX and Windows NTFS). Never write directly to the target path — a crash mid-write leaves a truncated/corrupt file.

### Resource Lifecycle
- **`httpx.AsyncClient` instances must be closed before their reference is dropped.** When resetting a global client, save the old reference, null the global, then schedule `aclose()` on the event loop (or run it synchronously as fallback). Nulling the reference alone leaks the connection pool.

---

## Future Enhancements

1. **Event Persistence**: SQLite/PostgreSQL event store
2. **Snapshotting**: Aggregate state snapshots for faster reconstruction
3. **Saga Pattern**: Distributed transaction management
4. **GraphQL API**: Alternative query interface
5. **WebSocket Support**: Real-time bidirectional communication
6. **Plugin Marketplace**: Third-party widget distribution
