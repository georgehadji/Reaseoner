"""
ARA v2.0 Pipeline — Entry Point
Adaptive Reasoning Architecture

================================================================
USAGE — PRESETS (recommended)
================================================================
# List all available presets + key status:
python main.py --list-presets

# Run with a named preset:
python main.py --problem "..." --preset multi-perspective-budget
python main.py --problem "..." --preset multi-perspective-premium
python main.py --problem "..." --preset research-budget
python main.py --problem "..." --preset research-premium
python main.py --problem "..." --preset debate-budget
python main.py --problem "..." --preset debate-premium

================================================================
USAGE — CUSTOM ROUTING
================================================================
# Fully custom routing (JSON dict, must include "primary"):
python main.py --problem "..." --routing '{
  "primary":       "deepseek-v3",
  "constructive":  "kimi-k2",
  "destructive":   "qwen3-max",
  "scoring":       "sonar-pro",
  "synthesis":     "glm-5"
}'

================================================================
USAGE — MODEL DISCOVERY
================================================================
# List all available model IDs grouped by ecosystem:
python main.py --list-models

================================================================
USAGE — I/O OPTIONS
================================================================
python main.py --problem-file problem.txt --preset multi-perspective-budget
python main.py --problem "..." --preset research-budget --output result.json
python main.py --problem "..." --preset multi-perspective-premium --sequential --quiet
python main.py --problem "..." --preset research-premium --top-k 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reasoner.pipeline import ARAPipeline
from reasoner.renderer import export_to_json, render_pipeline_result
from reasoner.llm import ProviderRouter, list_models
from reasoner.core.settings import settings  # triggers dotenv load
from reasoner.core.constants import DEFAULT_CLI_PRESET
from reasoner.presets import (
    PRESETS,
    build_custom_router,
    get_preset,
    is_valid_preset_name,
    print_presets_summary,
    resolve_preset_name,
)
from reasoner.gate_agent import GateAgent  # kept for backward compat
from reasoner.hypergate import HyperGateAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# ROUTER BUILDER
# ─────────────────────────────────────────────────────────────────────

def build_router(args: argparse.Namespace) -> ProviderRouter:
    """
    Resolve router from CLI args.
    Priority: --routing > --preset > default (multi-perspective-budget)
    """
    if args.routing:
        try:
            routing_dict: dict[str, str] = json.loads(args.routing)
        except json.JSONDecodeError as exc:
            print(f"[ERROR] --routing is not valid JSON: {exc}")
            sys.exit(1)
        if "primary" not in routing_dict:
            print("[ERROR] --routing JSON must include a 'primary' key.")
            sys.exit(1)
        router = build_custom_router(routing_dict)
        print(f"\n[Custom routing] primary={routing_dict['primary']}")
        for role, mid in routing_dict.items():
            if role != "primary":
                print(f"  {role:18s} -> {mid}")
        return router

    preset_name = args.preset or DEFAULT_CLI_PRESET
    preset = get_preset(preset_name)

    missing = preset.missing_keys()
    if missing:
        print(f"\n[WARNING] Preset '{preset_name}' requires API keys that are not set:")
        for key in missing:
            print(f"  • {key}")
        print("  Affected phases will fail. Set keys or choose a different preset.\n")

    router = preset.build_router()
    print(f"\n[Preset: {preset.name}]")
    print(f"  {preset.description}")
    routing_info = router.describe()
    for role, model in routing_info.items():
        print(f"  {role:22s} -> {model}")
    return router


# ─────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────

def cmd_list_models() -> None:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    groups = list_models()
    console = Console()

    for ecosystem, model_ids in sorted(groups.items()):
        if not model_ids:
            continue
        table = Table(
            title=f"[cyan]{ecosystem.upper()}[/cyan]",
            box=box.SIMPLE,
            show_header=False,
            min_width=40,
        )
        table.add_column("Model ID", style="white")
        for mid in sorted(model_ids):
            table.add_row(mid)
        console.print(table)


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    if args.list_presets:
        print_presets_summary()
        return

    if args.list_models:
        cmd_list_models()
        return

    # Handle resume from saved state
    if args.resume:
        from reasoner.models import PipelineState
        state_path = Path(args.resume)
        if not state_path.exists():
            print(f"[ERROR] State file not found: {args.resume}")
            sys.exit(1)
        try:
            state = PipelineState.load(args.resume)
            print(f"\n{'='*60}")
            print(f"  ARA v2.0 — Resumed from saved state")
            print(f"{'='*60}")
            print(f"  Problem: {state.problem[:120]}...")
            print(f"  Resumed at: {state.task_type.value if state.task_type else 'start'}")
            print(f"{'='*60}\n")
            render_pipeline_result(state)
            problem = state.problem # Initialize problem for continued pipeline run
        except Exception as exc:
            print(f"[ERROR] Failed to load state: {exc}")
            sys.exit(1)
    else: # If not resuming, load problem normally
        # Load problem
        if args.problem_file:
            problem_path = Path(args.problem_file)
            if not problem_path.exists():
                print(f"[ERROR] File not found: {args.problem_file}")
                sys.exit(1)
            problem = problem_path.read_text(encoding="utf-8").strip()
        else:
            problem = args.problem.strip()

    if not problem:
        print("[ERROR] No problem provided. Use --problem or --problem-file.")
        print("        Run 'python main.py --help' for usage.")
        sys.exit(1)

    router = build_router(args)

    # Determine initial_state for the pipeline
    initial_state = None
    if args.resume:
        try:
            initial_state = PipelineState.load(args.resume)
        except Exception as exc:
            print(f"[ERROR] Failed to load initial state for pipeline: {exc}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  ARA v2.0 — Adaptive Reasoning Architecture")
    print(f"{'='*60}")
    short_problem = problem[:120] + ("..." if len(problem) > 120 else "")
    print(f"  Problem: {short_problem}")
    print(f"  Top-K candidates: {args.top_k}")
    print(f"  Parallel perspectives: {not args.sequential}")
    print(f"{'='*60}\n")

    # SECURITY: Prompt-injection defense for CLI input
    from reasoner.sanitization import sanitize_for_prompt
    problem, _ = sanitize_for_prompt(problem)

    # ── Gate Agent: decide direct answer vs full pipeline ──
    if not args.force_pipeline:
        gate = HyperGateAgent(router)
        decision = await gate.decide(problem)
        if decision.action == "direct":
            print("  [Gate] Direct answer selected.\n")
            response, _ = await router.call(
                role="primary",
                system_prompt="You are an analytical assistant. Provide a clear, concise answer.",
                user_prompt=problem,
                max_tokens=2048,
                temperature=0.7,
            )
            print(response)
            return
        if decision.action == "web_search":
            print("  [Gate] Web search selected.\n")
            from reasoner.core.search import get_discovery_client
            try:
                client, _ = await get_discovery_client(source_type="general")
                results = await client.search(problem, num_results=10, source_type="general")
            except Exception as exc:
                logger.warning("Web search failed: %s", exc)
                results = []
            if not results:
                print("No relevant web search results were found for your query.")
                return
            print("### Web Search Results\n")
            for i, r in enumerate(results, 1):
                title = r.get("title") or "Untitled"
                url = r.get("url") or ""
                snippet = r.get("snippet") or r.get("content") or ""
                print(f"{i}. [{title}]({url})")
                if snippet:
                    print(f"   > {snippet}")
                print()
            return
        else:
            print(f"  [Gate] Pipeline selected ({decision.method or 'multi_perspective'}).\n")

    pipeline = ARAPipeline(
        router=router,
        initial_state=initial_state, # Pass the loaded state
        top_k=args.top_k,
        parallel_perspectives=not args.sequential,
        verbose=not args.quiet,
        preset_name=args.preset or "multi-perspective-budget",
        source_type=args.source_type,
        domain=args.domain or None,
        enhance_prompt=args.enhance_prompt,
    )

    state = await pipeline.run(problem)

    render_pipeline_result(state)

    if args.output:
        export_to_json(state, args.output)
        print(f"\n[OK] Full state exported -> {args.output}")

    if args.save_state:
        state.save(args.save_state)
        print(f"\n[OK] State saved -> {args.save_state}")


# ─────────────────────────────────────────────────────────────────────
# CLI ARGS
# ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    # Build preset choices dynamically
    preset_choices = sorted(PRESETS.keys())

    def _preset_arg(value: str) -> str:
        if not value:  # Allow empty string to pass through (will use default)
            return value
        if not is_valid_preset_name(value):
            raise argparse.ArgumentTypeError(
                f"Unknown preset {value!r}. Choices: {', '.join(preset_choices)}"
            )
        return resolve_preset_name(value)

    parser = argparse.ArgumentParser(
        description="ARA v2.0 — Adaptive Reasoning Architecture Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Problem input
    input_group = parser.add_argument_group("Problem Input")
    input_group.add_argument(
        "--problem", "-p",
        type=str, default="",
        help="Problem statement (wrap in quotes)",
    )
    input_group.add_argument(
        "--problem-file",
        type=str, default="",
        metavar="PATH",
        help="Path to .txt file containing the problem statement",
    )

    # ── Model/Routing selection
    routing_group = parser.add_argument_group("Model Selection (mutually exclusive)")
    routing_ex = routing_group.add_mutually_exclusive_group()
    routing_ex.add_argument(
        "--preset",
        type=_preset_arg,
        default="",
        metavar="PRESET_ID",
        help=(
            "Named routing preset. Choices: "
            + ", ".join(preset_choices)
            + " (default: multi-perspective-budget)"
        ),
    )
    routing_ex.add_argument(
        "--routing",
        type=str,
        default="",
        metavar="JSON",
        help=(
            'Custom JSON routing dict. Must include "primary". '
            'Example: \'{"primary":"deepseek-v3","scoring":"sonar-pro"}\''
        ),
    )

    # ── Pipeline options
    pipeline_group = parser.add_argument_group("Pipeline Options")
    pipeline_group.add_argument(
        "--top-k",
        type=int, default=2,
        help="Number of candidates to keep after pruning (default: 2)",
    )
    pipeline_group.add_argument(
        "--sequential",
        action="store_true",
        help="Run Phase 2 perspectives sequentially (for rate-limited providers)",
    )
    pipeline_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress phase-by-phase logging",
    )
    pipeline_group.add_argument(
        "--force-pipeline",
        action="store_true",
        help="Bypass the GateAgent and always run the full multi-phase pipeline",
    )
    pipeline_group.add_argument(
        "--source-type",
        type=str, default="general",
        choices=["general", "academic", "social", "news", "code"],
        help="Source type for iterative RAG: general, academic, social, news, code (default: general)",
    )
    pipeline_group.add_argument(
        "--domain",
        type=str, default="",
        metavar="DOMAIN",
        help="Limit search to specific domain (e.g., github.com, stackoverflow.com)",
    )

    # ── Output
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--output", "-o",
        type=str, default="",
        metavar="PATH",
        help="Export full pipeline state to JSON file",
    )
    output_group.add_argument(
        "--save-state",
        type=str, default="",
        metavar="PATH",
        help="Save pipeline state to file for later resume",
    )

    # ── State Management
    state_group = parser.add_argument_group("State Management")
    state_group.add_argument(
        "--resume",
        type=str, default="",
        metavar="PATH",
        help="Resume pipeline from saved state file",
    )

    # ── Discovery
    info_group = parser.add_argument_group("Discovery")
    info_group.add_argument(
        "--list-presets",
        action="store_true",
        help="List all available presets with API key status, then exit",
    )
    info_group.add_argument(
        "--list-models",
        action="store_true",
        help="List all available model IDs grouped by ecosystem, then exit",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
