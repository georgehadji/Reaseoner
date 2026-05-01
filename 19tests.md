$ pytest -s tests/test_methods_audit.py
========================================= test session starts =========================================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\Documents\Vibe-Coding\Reasoner
configfile: pytest.ini
plugins: anyio-4.13.0, dash-4.0.0, langsmith-0.7.25, asyncio-0.24.0, cov-7.0.0, mock-3.15.1, timeout-2.4.0, xdist-3.8.0
asyncio: mode=Mode.AUTO, default_loop_scope=session
collecting ... [DEBUG] api/__init__.py: Logger setup
[DEBUG] api/__init__.py: Logging filter added
[DEBUG] api/__init__.py: Sentry initialized
[DEBUG] api/__init__.py: Initializing security...
[DEBUG] api/__init__.py: Security initialized
[DEBUG] api/__init__.py: Importing rate limiter and auth managers...
[DEBUG] reasoner/rate_limiter.py: Top of file
[DEBUG] reasoner/rate_limiter.py: Before metrics import
[DEBUG] api/__init__.py: Rate limiter and auth managers imported
[DEBUG] api/__init__.py: Creating FastAPI app...
[DEBUG] api/__init__.py: FastAPI app created
[DEBUG] api/__init__.py: Initializing rate limiter...
[DEBUG] reasoner/rate_limiter.py: Instantiating RateLimiter
[DEBUG] api/__init__.py: Rate limiter initialized
[DEBUG] api/__init__.py: Initializing auth manager...
[DEBUG] api/__init__.py: Auth manager initialized
[DEBUG] api/__init__.py: Initializing neuro router...
[DEBUG] neuro/config.py: load_config started
[DEBUG] neuro/config.py: checking default config paths
[DEBUG] neuro/config.py: checking neuro.yaml
[DEBUG] neuro/config.py: checking neuro.yml
[DEBUG] neuro/config.py: checking C:\Users\tesse\.config\neuro\neuro.yaml
[DEBUG] neuro/config.py: checking \etc\neuro\neuro.yaml
[DEBUG] neuro/config.py: no config file found, using defaults
[DEBUG] api/__init__.py: Neuro router initialized
[DEBUG] api/__init__.py: Before new architecture integration block
[DEBUG] api/__init__.py: After new architecture integration block
[DEBUG] api/__init__.py: Before widget integrations block
[DEBUG] api/__init__.py: After widget integrations block
[DEBUG] api/__init__.py: Before run state manager import
[DEBUG] api/__init__.py: After run state manager import
[DEBUG] api/__init__.py: Before cache imports
[DEBUG] api/__init__.py: After cache imports
[DEBUG] api/__init__.py: Before schemas imports
[DEBUG] api/__init__.py: After schemas imports
[DEBUG] api/__init__.py: Before serializers imports
[DEBUG] api/__init__.py: After serializers imports
[DEBUG] api/__init__.py: Before streaming imports
collected 19 items

tests\test_methods_audit.py

>>> TESTING PRESET: multi-perspective-budget
>>> PROBLEM: Should I bootstrap or raise VC for my AI startup?
>>> FAILED: multi-perspective-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: debate-budget
>>> PROBLEM: Is remote work more productive than in-office work? Debate the merits.
>>> FAILED: debate-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: jury-budget
>>> PROBLEM: Evaluate the potential impact of universal basic income on the global economy.
>>> FAILED: jury-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: research-budget
>>> PROBLEM: Provide a deep research report on the current state of solid-state battery technology.
>>> FAILED: research-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: scientific-budget
>>> PROBLEM: Hypothesize why the rate of obesity is increasing despite increased health awareness.
>>> FAILED: scientific-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: socratic-budget
>>> PROBLEM: What is justice? Help me understand the concept through questioning.
>>> FAILED: socratic-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: pre-mortem-budget
>>> PROBLEM: Our new SaaS product launch is in 3 months. What could go wrong?
>>> FAILED: pre-mortem-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: bayesian-budget
>>> PROBLEM: What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.
{"timestamp": "2026-05-01T00:02:01.793628Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' opened after 3 failures", "correlation_id": "2596d132", "extra": {"extra": {"circuit": "searxng", "state": "open", "consecutive_failures": 3}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: bayesian-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: dialectical-budget
>>> PROBLEM: Explore the tension between individual privacy and national security.
{"timestamp": "2026-05-01T00:07:03.098090Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "2145fc82", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:07:33.103803Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "3cb07985", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: dialectical-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: analogical-budget
>>> PROBLEM: How is building a software project like building a house?
{"timestamp": "2026-05-01T00:11:25.821372Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "663aa50f", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:11:55.828637Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "77456233", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: analogical-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: delphi-budget
>>> PROBLEM: What will be the most significant technological breakthrough of the 2030s?
{"timestamp": "2026-05-01T00:15:15.483447Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "fce720c9", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:15:16.897918Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' CLOSED after recovery", "correlation_id": "fb60a8c5", "extra": {"extra": {"circuit": "searxng", "state": "closed"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: delphi-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: cove-budget
>>> PROBLEM: List 5 facts about the Roman Empire and verify each one.
>>> FAILED: cove-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: sot-budget
>>> PROBLEM: Outline the steps to create a successful marketing campaign for a new consumer app.
{"timestamp": "2026-05-01T00:25:33.476588Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' opened after 3 failures", "correlation_id": "35e1ca79", "extra": {"extra": {"circuit": "searxng", "state": "open", "consecutive_failures": 3}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: sot-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: tot-budget
>>> PROBLEM: Solve the following riddle: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?
{"timestamp": "2026-05-01T00:29:05.898277Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "f97b471e", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:29:05.899313Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "f97b471e", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: tot-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: pot-budget
>>> PROBLEM: Calculate the 10th Fibonacci number using Python code.
{"timestamp": "2026-05-01T00:31:19.043965Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "2b2fac5e", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:31:49.049882Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "877bb46f", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: pot-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: self-discover-budget
>>> PROBLEM: How can I optimize my morning routine for maximum productivity and well-being?
{"timestamp": "2026-05-01T00:34:18.148027Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "dc5fb574", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:34:48.154877Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "42cb4de4", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: self-discover-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

>>> TESTING PRESET: writing-budget
>>> PROBLEM: Write a research-backed article about the history and future of synthetic biology.
{"timestamp": "2026-05-01T00:38:05.294427Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "5db303d4", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:38:35.306518Z", "level": "WARNING", "source": "llm", "message": "Circuit 'searxng' reopened after half-open failure", "correlation_id": "05b26aa8", "extra": {"extra": {"circuit": "searxng", "state": "open"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: writing-budget with error: 'str' object has no attribute 'get'
F

>>> TESTING PRESET: coding-budget
>>> PROBLEM: Generate a complete Python script for a web scraper that extracts news headlines from a given URL.
{"timestamp": "2026-05-01T00:40:28.155287Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' transitioning to HALF_OPEN", "correlation_id": "f0f32730", "extra": {"extra": {"circuit": "searxng", "state": "half_open"}}, "user_id": null, "tier": null, "preset": null}
{"timestamp": "2026-05-01T00:40:58.170382Z", "level": "INFO", "source": "llm", "message": "Circuit 'searxng' CLOSED after recovery", "correlation_id": "819f9b47", "extra": {"extra": {"circuit": "searxng", "state": "closed"}}, "user_id": null, "tier": null, "preset": null}
>>> FAILED: coding-budget with error: 'TruncationLimits' object is not subscriptable
F

>>> TESTING PRESET: brainstorming-budget
>>> PROBLEM: Brainstorm 10 innovative ways to reduce plastic waste in urban environments.
>>> FAILED: brainstorming-budget with error: 'PipelineState' object has no attribute 'synthesis'
F

============================================== FAILURES ===============================================
__ test_method_execution[multi-perspective-budget-Should I bootstrap or raise VC for my AI startup?] __

preset_name = 'multi-perspective-budget', problem = 'Should I bootstrap or raise VC for my AI startup?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'multi-perspective-budget', problem = 'Should I bootstrap or raise VC for my AI startup?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'systemic' provider 'z-ai/glm-4.7-flash' timed out after 45s — retrying with fallback 'qwen/qwen3.5-plus-02-15'
ERROR    reasoner.infrastructure.llm.router:router.py:141 Role 'systemic' fallback 'qwen/qwen3.5-plus-02-15' timed out after 45s; returning degraded response
ERROR    reasoner.infrastructure.llm.executor:executor.py:249 LLM degraded for role=systemic: qwen/qwen3.5-plus-02-15 timed out
_ test_method_execution[debate-budget-Is remote work more productive than in-office work? Debate the merits.] _

preset_name = 'debate-budget'
problem = 'Is remote work more productive than in-office work? Debate the merits.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'debate-budget'
problem = 'Is remote work more productive than in-office work? Debate the merits.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[jury-budget-Evaluate the potential impact of universal basic income on the global economy.] _

preset_name = 'jury-budget'
problem = 'Evaluate the potential impact of universal basic income on the global economy.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'jury-budget'
problem = 'Evaluate the potential impact of universal basic income on the global economy.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'generator_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'generator_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'generator_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'critic_1' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[research-budget-Provide a deep research report on the current state of solid-state battery technology.] _

preset_name = 'research-budget'
problem = 'Provide a deep research report on the current state of solid-state battery technology.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'research-budget'
problem = 'Provide a deep research report on the current state of solid-state battery technology.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.scraper:scraper.py:201 HTTP error scraping https://www.nature.com/subjects/solid-state-batteries: Client error '404 Not Found' for url 'https://www.nature.com/subjects/solid-state-batteries'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
WARNING  reasoner.infrastructure.llm.router:router.py:173 Role 'systemic' provider 'z-ai/glm-4.7-flash' failed (Empty response from z-ai/glm-4.7-flash for role=systemic) — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[scientific-budget-Hypothesize why the rate of obesity is increasing despite increased health awareness.] _

preset_name = 'scientific-budget'
problem = 'Hypothesize why the rate of obesity is increasing despite increased health awareness.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'scientific-budget'
problem = 'Hypothesize why the rate of obesity is increasing despite increased health awareness.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[socratic-budget-What is justice? Help me understand the concept through questioning.] _

preset_name = 'socratic-budget'
problem = 'What is justice? Help me understand the concept through questioning.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'socratic-budget'
problem = 'What is justice? Help me understand the concept through questioning.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[pre-mortem-budget-Our new SaaS product launch is in 3 months. What could go wrong?] _

preset_name = 'pre-mortem-budget'
problem = 'Our new SaaS product launch is in 3 months. What could go wrong?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'pre-mortem-budget'
problem = 'Our new SaaS product launch is in 3 months. What could go wrong?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[bayesian-budget-What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.] _

preset_name = 'bayesian-budget'
problem = 'What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'bayesian-budget'
problem = 'What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  llm:logging_utils.py:225 Circuit 'searxng' opened after 3 failures
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'destructive' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[dialectical-budget-Explore the tension between individual privacy and national security.] _

preset_name = 'dialectical-budget'
problem = 'Explore the tension between individual privacy and national security.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'dialectical-budget'
problem = 'Explore the tension between individual privacy and national security.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"data collection methods" "national security" "privacy impli'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"encryption" "government access" "international law"'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"whistleblower" "surveillance programs" "public discourse"'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"expert opinions" "privacy vs security trade-offs" 2020-2024'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"impact of § privacy legislation § national security" case s'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"ethical considerations" "mass surveillance" "democratic soc'
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[analogical-budget-How is building a software project like building a house?] __

preset_name = 'analogical-budget', problem = 'How is building a software project like building a house?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'analogical-budget', problem = 'How is building a software project like building a house?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'software development lifecycle phases vs construction projec'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'role of requirements gathering in software development and h'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'impact of design changes in software projects vs constructio'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'expert analysis software development as construction metapho'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'articles discussing agile software development vs traditiona'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'case studies comparing software project failures to construc'
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:173 Role 'systemic' provider 'z-ai/glm-4.7-flash' failed (Empty response from z-ai/glm-4.7-flash for role=systemic) — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:173 Role 'systemic' provider 'z-ai/glm-4.7-flash' failed (Empty response from z-ai/glm-4.7-flash for role=systemic) — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[delphi-budget-What will be the most significant technological breakthrough of the 2030s?] _

preset_name = 'delphi-budget'
problem = 'What will be the most significant technological breakthrough of the 2030s?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'delphi-budget'
problem = 'What will be the most significant technological breakthrough of the 2030s?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"AI advancements" "2030s" "transformative capabilities" "spe'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"biotechnology breakthroughs" "2030s" "DNA editing" "persona'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"quantum computing" "progress" "2030s" "potential applicatio'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"scientific journals" "major technological innovations" "203'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"leading research institutions" "foresight reports" "key eme'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"World Economic Forum" "McKinsey" "Gartner" "technology tren'
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'expert_3' provider 'z-ai/glm-4.5-air' timed out after 45s — retrying with fallback 'qwen/qwen3.5-plus-02-15'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'expert_2' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'z-ai/glm-4.5-air'
ERROR    reasoner.infrastructure.llm.router:router.py:141 Role 'expert_3' fallback 'qwen/qwen3.5-plus-02-15' timed out after 45s; returning degraded response
ERROR    reasoner.infrastructure.llm.executor:executor.py:249 LLM degraded for role=expert_3: qwen/qwen3.5-plus-02-15 timed out
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'expert_2' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'z-ai/glm-4.5-air'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'expert_2' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'z-ai/glm-4.5-air'
_____ test_method_execution[cove-budget-List 5 facts about the Roman Empire and verify each one.] _____

preset_name = 'cove-budget', problem = 'List 5 facts about the Roman Empire and verify each one.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'cove-budget', problem = 'List 5 facts about the Roman Empire and verify each one.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.scraper:scraper.py:204 Error scraping https://www.britannica.com/place/Roman-Empire: Event loop is closed
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'cove_verify' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[sot-budget-Outline the steps to create a successful marketing campaign for a new consumer app.] _

preset_name = 'sot-budget'
problem = 'Outline the steps to create a successful marketing campaign for a new consumer app.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'sot-budget'
problem = 'Outline the steps to create a successful marketing campaign for a new consumer app.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  llm:logging_utils.py:225 Circuit 'searxng' opened after 3 failures
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'sot_solve' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'sot_solve' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'sot_solve' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'sot_solve' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
_ test_method_execution[tot-budget-Solve the following riddle: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?] _

preset_name = 'tot-budget'
problem = 'Solve the following riddle: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'tot-budget'
problem = 'Solve the following riddle: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed: Event loop is closed
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'common riddles with abstract personification of natural phen'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'riddles about elements that are intangible and moved by air'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'answer to riddle speak without mouth hear without ears no bo'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'metaphorical meanings of speaking without a mouth and hearin'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'riddles involving wind as a life-giving or animating force'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'authoritative interpretations of common riddles about nature'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'linguistic analysis of riddles personifying inanimate object'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for "origin of the riddle 'I speak without a mouth and hear witho"
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'solve following riddle speak without'
______ test_method_execution[pot-budget-Calculate the 10th Fibonacci number using Python code.] _______

preset_name = 'pot-budget', problem = 'Calculate the 10th Fibonacci number using Python code.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'pot-budget', problem = 'Calculate the 10th Fibonacci number using Python code.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'python function for fibonacci series with example'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'best practices python fibonacci implementation'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'performance comparison iterative recursive fibonacci python'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'python official documentation fibonacci sequence'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'interview questions fibonacci implementation python'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'advanced python fibonacci techniques'
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[self-discover-budget-How can I optimize my morning routine for maximum productivity and well-being?] _

preset_name = 'self-discover-budget'
problem = 'How can I optimize my morning routine for maximum productivity and well-being?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'self-discover-budget'
problem = 'How can I optimize my morning routine for maximum productivity and well-being?'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"chronotype" "morning productivity" impact'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"mindfulness" "meditation" "morning routine" benefits resear'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'effective "sleep hygiene" "morning alertness"'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"expert advice" "habit formation" "morning routine" "behavio'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"productivity coaches" "morning routine" "peak performance" '
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"health and wellness" "long term" "morning routine success" '
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'sd_adapt' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'post_synthesis_verify' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[writing-budget-Write a research-backed article about the history and future of synthetic biology.] _

preset_name = 'writing-budget'
problem = 'Write a research-backed article about the history and future of synthetic biology.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_methods_audit.py:51: in test_method_execution
    state = await pipeline.run(problem)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\reasoner\pipeline.py:447: in run
    await step.fn(state)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <reasoner.pipeline.ReasonerPipeline object at 0x0000019135454C20>
state = PipelineState(problem='Write a research-backed article about the history and future of synthetic biology.', enhanced_p... conversation_id='', turn_number=1, previous_synthesis='', agent_model=None), attachments=[], _MAX_PENDING_EVENTS=1000)

    async def _phase_article_synthesize(self, state: PipelineState) -> None:
        """Synthesize article using SoT (Skeleton-of-Thought): skeleton → parallel sections → assemble."""
        self._log("ARTICLE", "SoT Synthesis: generating skeleton...", state)
        claims = state.writing_state.get("claims", [])
        verifications = state.writing_state.get("verifications", [])

        # Filter to verified + weak claims only (no conflicted)
        verified_ids = {v["claim_id"] for v in verifications if v.get("status") in ("VERIFIED", "WEAK")}
        usable_claims = [c for c in claims if c.get("id", "") in verified_ids]

        # ── Evidence Gate ──
        retrieved_sources = state.writing_state.get("retrieved_sources", [])
        if not usable_claims and len(retrieved_sources) < ARTICLE_MIN_SOURCE_COUNT:
            self._log("ARTICLE", "EVIDENCE GATE: No usable claims and insufficient sources. Halting synthesis.", state)
            diagnostics = state.writing_state.get("retrieval_diagnostics", {})
            queries = diagnostics.get("queries_executed", 0)
            fallback_attempts = [f for f in diagnostics.get("fallback_attempts", []) if f]
            article_text = (
                f"# Insufficient Evidence\n\n"
                f"No authoritative sources could be retrieved for this topic.\n\n"
                f"## What was attempted\n"
                f"- {queries} search queries executed against the decomposition\n"
            )
            if fallback_attempts:
                article_text += f"- Fallback attempts: {', '.join(fallback_attempts)}\n"
            else:
                article_text += "- No fallback attempts succeeded\n"
            article_text += (
                f"\n## Recommendations\n"
                f"- Try a more specific query with named entities, dates, or events\n"
                f"- Check that the search backend (SearXNG or Perplexity) is reachable\n"
                f"- For rapidly evolving topics, try again in a few minutes\n"
            )
            state.writing_state["article"] = article_text
            state.writing_state["sections"] = []
            state.writing_state["abstract"] = "Insufficient evidence to produce a verified article."
            state.writing_state["title"] = "Insufficient Evidence"
            state.writing_state["gaps_noted"] = ["No sources retrieved", "No claims extracted"]
            state.writing_state["insufficient_evidence"] = True
            state.pending_events.append({
                "type": "phase_warning",
                "message": "Evidence gate triggered: no sources or verified claims available. Output is a failure report, not a research article.",
            })
            return

        if not usable_claims:
            self._log("ARTICLE", "No usable claims — falling back to knowledge-only synthesis", state)
            if not retrieved_sources:
                state.pending_events.append({
                    "type": "phase_warning",
                    "message": "No sources or verified claims available. Output will rely on model knowledge only — treat as unverified.",
                })
            await self._phase_article_synthesize_monolithic(state, "[]")
            return

        claims_json = json.dumps(usable_claims, indent=2, ensure_ascii=False)

        # ── Step 1: Generate skeleton ──
        doc_type = state.writing_state.get("document_type", "article")
        is_academic = doc_type in ("paper", "thesis")
        raw_skeleton, _ = await self._call_llm_cached(
            role="article_sot_skeleton",
            system_prompt=phases.ACADEMIC_SOT_SYSTEM if is_academic else phases.ARTICLE_SOT_SYSTEM,
            user_prompt=(
                phases.academic_sot_skeleton_prompt(state, claims_json)
                if is_academic
                else phases.article_sot_skeleton_prompt(state, claims_json)
            ),
            state=state,
        )
        try:
            skeleton_data = extract_json(raw_skeleton)
            skeleton_sections = skeleton_data.get("sections", [])
        except Exception as exc:
            self._log("ARTICLE", f"SoT skeleton parse error: {exc}", state)
            state.errors.append(f"Article SoT skeleton: parse error: {exc}")
            # Fallback: generate article monolithically
            await self._phase_article_synthesize_monolithic(state, claims_json)
            return

        if not skeleton_sections:
            self._log("ARTICLE", "No skeleton sections — falling back to monolithic", state)
            await self._phase_article_synthesize_monolithic(state, claims_json)
            return

        state.writing_state["sot_skeleton"] = skeleton_sections
        self._log("ARTICLE", f"SoT skeleton: {len(skeleton_sections)} sections", state)

        # ── Step 2: Parallel section writing ──
        semaphore = asyncio.Semaphore(4)

        async def _write_one(section: dict) -> dict:
            async with semaphore:
                # Filter claims relevant to this section
                section_claim_ids = section.get("claim_ids", [])
                section_claims = [c for c in usable_claims if c.get("id", "") in section_claim_ids]
                if not section_claims:
                    section_claims = usable_claims  # fallback: use all claims
                section_claims_json = json.dumps(section_claims, indent=2, ensure_ascii=False)

                raw_sec, _ = await self._call_llm_cached(
                    role="article_sot_solve",
                    system_prompt=(
                        phases.ACADEMIC_SOT_SOLVE_SYSTEM if is_academic else phases.ARTICLE_SOT_SOLVE_SYSTEM
                    ),
                    user_prompt=(
                        phases.academic_sot_solve_prompt(state, section, section_claims_json)
                        if is_academic
                        else phases.article_sot_solve_prompt(state, section, section_claims_json)
                    ),
                    state=state,
                )
                try:
                    sec_data = extract_json(raw_sec)
                except Exception as exc:
                    self._log("ARTICLE", f"SoT section parse error: {exc}", state)
                    return {"heading": section.get("heading", ""), "content": "", "error": str(exc)}

                return {
                    "heading": section.get("heading", ""),
                    "content": sec_data.get("content", ""),
                    "word_count": sec_data.get("word_count", 0),
                }

        tasks = [_write_one(sec) for sec in skeleton_sections]
        section_results = await asyncio.gather(*tasks, return_exceptions=True)

        written_sections: list[dict] = []
        for i, result in enumerate(section_results):
            if isinstance(result, Exception):
                self._log("ARTICLE", f"Section {i} failed: {result}", state)
>               heading = skeleton_sections[i].get("heading", f"Section {i+1}") if i < len(skeleton_sections) else f"Section {i+1}"
                          ^^^^^^^^^^^^^^^^^^^^^^^^
E               AttributeError: 'str' object has no attribute 'get'

src\reasoner\application\mixins\article_pipeline.py:934: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"synthetic biology" future trends research directions 2030s '
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"synthetic biology" advancements in gene editing CRISPR appl'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"synthetic biology" commercialization challenges regulatory '
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"synthetic biology" Nobel laureates contributions seminal pa'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'National Academies of Sciences "synthetic biology" reports f'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for '"synthetic biology" advancements in bioremediation pharmaceu'
WARNING  llm:logging_utils.py:225 Circuit 'searxng' reopened after half-open failure
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
ERROR    reasoner.scraper:scraper.py:204 Error scraping https://www.nature.com/articles/nrmicro3239: Event loop is closed
ERROR    reasoner.scraper:scraper.py:201 HTTP error scraping https://hudsonlabautomation.com/a-brief-history-of-synthetic-biology/: Client error '403 Forbidden' for url 'https://hudsonlabautomation.com/a-brief-history-of-synthetic-biology/'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'article_cove_revise' provider 'z-ai/glm-4.5-air' timed out after 45s — retrying with fallback 'google/gemini-2.5-flash-lite'
_ test_method_execution[coding-budget-Generate a complete Python script for a web scraper that extracts news headlines from a given URL.] _

preset_name = 'coding-budget'
problem = 'Generate a complete Python script for a web scraper that extracts news headlines from a given URL.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_methods_audit.py:51: in test_method_execution
    state = await pipeline.run(problem)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\reasoner\pipeline.py:447: in run
    await step.fn(state)
src\reasoner\application\mixins\coding_pipeline.py:27: in _phase_coding_spec
    user_prompt=phases.coding_spec_prompt(state),
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

state = PipelineState(problem='Generate a complete Python script for a web scraper that extracts news headlines from a given U... conversation_id='', turn_number=1, previous_synthesis='', agent_model=None), attachments=[], _MAX_PENDING_EVENTS=1000)

    def coding_spec_prompt(state: PipelineState) -> str:
>       problem = _wrap_user_input(state.problem[:TRUNCATION["problem"]])
                                                  ^^^^^^^^^^^^^^^^^^^^^
E       TypeError: 'TruncationLimits' object is not subscriptable

src\reasoner\phases\coding.py:52: TypeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'BeautifulSoup find_all find methods for specific tags'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'handling dynamic content web scraping Python BeautifulSoup'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'Python requests get response status code error handling'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'ethical web scraping best practices'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'respecting robots.txt Python scraping'
WARNING  reasoner.core.search:search.py:362 SearXNG circuit breaker OPEN — skipping search for 'web scraping legal considerations terms of service'
ERROR    reasoner.core.search:search.py:415 Web discovery failed:
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'context_vetting' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
_ test_method_execution[brainstorming-budget-Brainstorm 10 innovative ways to reduce plastic waste in urban environments.] _

preset_name = 'brainstorming-budget'
problem = 'Brainstorm 10 innovative ways to reduce plastic waste in urban environments.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

            assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
            assert len(state.synthesis) > 100, f"Synthesis too short for {preset_name}"
            assert not state.errors, f"Errors in pipeline run for {preset_name}: {state.errors}"

            print(f">>> SUCCESS: {preset_name}")
        except Exception as e:
            print(f">>> FAILED: {preset_name} with error: {str(e)}")
>           raise e

tests\test_methods_audit.py:60:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

preset_name = 'brainstorming-budget'
problem = 'Brainstorm 10 innovative ways to reduce plastic waste in urban environments.'

    @pytest.mark.parametrize("preset_name, problem", TEST_CASES)
    @pytest.mark.asyncio
    async def test_method_execution(preset_name, problem):
        print(f"\n\n>>> TESTING PRESET: {preset_name}")
        print(f">>> PROBLEM: {problem}")

        preset = get_preset(preset_name)
        router = preset.build_router()

        pipeline = ReasonerPipeline(
            router=router,
            preset_name=preset_name,
            verbose=True,
        )

        try:
            state = await pipeline.run(problem)

>           assert state.synthesis is not None, f"Synthesis is missing for {preset_name}"
                   ^^^^^^^^^^^^^^^
E           AttributeError: 'PipelineState' object has no attribute 'synthesis'

tests\test_methods_audit.py:53: AttributeError
------------------------------------------ Captured log call ------------------------------------------
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:66 Role 'fusion' not found in routing table — falling back to primary 'google/gemini-2.5-flash-lite'. Check preset routing configuration.
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'brainstorm_generate' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'brainstorm_generate' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
WARNING  reasoner.infrastructure.llm.router:router.py:150 Role 'brainstorm_generate' provider 'qwen/qwen3.6-plus' timed out after 45s — retrying with fallback 'deepseek/deepseek-v3.2'
======================================== slowest 10 durations =========================================
378.13s call     tests/test_methods_audit.py::test_method_execution[delphi-budget-What will be the most significant technological breakthrough of the 2030s?]
332.35s call     tests/test_methods_audit.py::test_method_execution[bayesian-budget-What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.]
309.61s call     tests/test_methods_audit.py::test_method_execution[pre-mortem-budget-Our new SaaS product launch is in 3 months. What could go wrong?]
299.42s call     tests/test_methods_audit.py::test_method_execution[brainstorming-budget-Brainstorm 10 innovative ways to reduce plastic waste in urban environments.]
262.59s call     tests/test_methods_audit.py::test_method_execution[dialectical-budget-Explore the tension between individual privacy and national security.]
241.83s call     tests/test_methods_audit.py::test_method_execution[sot-budget-Outline the steps to create a successful marketing campaign for a new consumer app.]
231.01s call     tests/test_methods_audit.py::test_method_execution[self-discover-budget-How can I optimize my morning routine for maximum productivity and well-being?]
229.52s call     tests/test_methods_audit.py::test_method_execution[analogical-budget-How is building a software project like building a house?]
228.33s call     tests/test_methods_audit.py::test_method_execution[multi-perspective-budget-Should I bootstrap or raise VC for my AI startup?]
217.78s call     tests/test_methods_audit.py::test_method_execution[research-budget-Provide a deep research report on the current state of solid-state battery technology.]
======================================= short test summary info =======================================
FAILED tests/test_methods_audit.py::test_method_execution[multi-perspective-budget-Should I bootstrap or raise VC for my AI startup?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[debate-budget-Is remote work more productive than in-office work? Debate the merits.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[jury-budget-Evaluate the potential impact of universal basic income on the global economy.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[research-budget-Provide a deep research report on the current state of solid-state battery technology.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[scientific-budget-Hypothesize why the rate of obesity is increasing despite increased health awareness.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[socratic-budget-What is justice? Help me understand the concept through questioning.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[pre-mortem-budget-Our new SaaS product launch is in 3 months. What could go wrong?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[bayesian-budget-What is the probability that a coin flip comes up heads if it has come up heads 10 times in a row? Explain using Bayesian reasoning.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[dialectical-budget-Explore the tension between individual privacy and national security.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[analogical-budget-How is building a software project like building a house?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[delphi-budget-What will be the most significant technological breakthrough of the 2030s?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[cove-budget-List 5 facts about the Roman Empire and verify each one.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[sot-budget-Outline the steps to create a successful marketing campaign for a new consumer app.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[tot-budget-Solve the following riddle: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[pot-budget-Calculate the 10th Fibonacci number using Python code.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[self-discover-budget-How can I optimize my morning routine for maximum productivity and well-being?] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
FAILED tests/test_methods_audit.py::test_method_execution[writing-budget-Write a research-backed article about the history and future of synthetic biology.] - AttributeError: 'str' object has no attribute 'get'
FAILED tests/test_methods_audit.py::test_method_execution[coding-budget-Generate a complete Python script for a web scraper that extracts news headlines from a given URL.] - TypeError: 'TruncationLimits' object is not subscriptable
FAILED tests/test_methods_audit.py::test_method_execution[brainstorming-budget-Brainstorm 10 innovative ways to reduce plastic waste in urban environments.] - AttributeError: 'PipelineState' object has no attribute 'synthesis'
=================================== 19 failed in 4091.56s (1:08:11) =============