"""eval/mlflow_eval.py — MLflow benchmark for the PlanningOrchestrator.

Runs a curated benchmark suite through the PlanningOrchestrator, scores each
response with an LLM-as-a-Judge, and logs all results (metrics, routing traces,
plan artefacts) to a local MLflow tracking server.

Each batch run becomes a parent MLflow run with one nested child run per test
case. The --version tag lets you distinguish baseline from later iterations so
the MLflow comparison UI gives you a clear before/after view.

Install:
    pip install "mlflow>=2.12.0"

Usage (from project root):
    python eval/mlflow_eval.py --version baseline
    python eval/mlflow_eval.py --version v1 --experiment thesis-eval
    mlflow ui   →  http://localhost:5000

Flags:
    --version      Version label (e.g. baseline, v1, prompt-v2)   [required]
    --experiment   MLflow experiment name  [default: graphxmaf-eval]
    --category     Filter: email | calendar | identity | locations | crm | cross-system
    --difficulty   Filter: simple | medium | hard
    --dry-run      Print prompts without running any agents
    --skip-graph   Skip Microsoft Graph authentication
    --skip-sf      Skip Salesforce authentication

  # Installeer
  pip install "mlflow>=2.13.0"

  # Baseline meting
  python eval/mlflow_eval.py --version baseline

  # Na verbetering (bijv. betere system prompt)
  python eval/mlflow_eval.py --version v1

  # Alleen cross-system vragen testen
  python eval/mlflow_eval.py --version baseline --category cross-system

  # UI openen (vergelijk baseline vs v1)
  mlflow ui --backend-store-uri sqlite:///mlflow.db   # → http://localhost:5000

  In de MLflow UI:
    - Runs tab     → metrics/params/artifacts per test case
    - Traces tab   → plan_generation / step_N_agent / synthesis spans met tijdlijn
    - Compare runs → selecteer baseline + v1 → zie alle metrics naast elkaar
"""

import sys
import os

# Ensure the project root (parent of eval/) is on sys.path so that
# 'agents', 'graph', 'salesforce', 'smartsales', and 'main' are importable
# regardless of how this script is invoked (python eval/mlflow_eval.py or
# python -m eval.mlflow_eval).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import asyncio
import configparser
import json
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import mlflow
from typing import Callable
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from agent_framework import MCPStreamableHTTPTool
from agents.graph_agent import create_graph_agent
from agents.planning_orchestrator import create_planning_orchestrator
from agents.routing_trace import start_trace
from agents.salesforce_agent import create_salesforce_agent
from agents.smartsales_agent import create_smartsales_agent
from eval.score import evaluate, evaluate_routing

load_dotenv()

mlflow.openai.autolog()


# ── Token auth helper ─────────────────────────────────────────────────────────

class RefreshingBearerAuth(httpx.Auth):
    """Calls token_fn() on startup and again on 401/403 to refresh the token."""

    def __init__(self, token_fn: Callable[[], str]):
        self._token_fn = token_fn
        self._token = token_fn()

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self._token}"
        response = yield request
        if response.status_code in (401, 403):
            self._token = self._token_fn()
            request.headers["Authorization"] = f"Bearer {self._token}"
            yield request


# ── Benchmark prompts ─────────────────────────────────────────────────────────

@dataclass
class BenchmarkPrompt:
    text: str
    category: str           # email | calendar | identity | locations | crm | cross-system | ...
    difficulty: str         # simple | medium | hard
    expected_answer: str    # what a correct response should contain (for LLM judge)
    tags: list[str] = field(default_factory=list)
    expected_agents: list[str] = field(default_factory=list)  # for routing precision/recall


def _load_prompts(path: str | None = None) -> list[BenchmarkPrompt]:
    """Load benchmark prompts from eval/prompts.json."""
    json_path = path or str(Path(__file__).parent / "prompts.json")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return [BenchmarkPrompt(**p) for p in data]


BENCHMARK_PROMPTS: list[BenchmarkPrompt] = _load_prompts()


# ── Orchestrator runner ───────────────────────────────────────────────────────

async def run_and_collect(orchestrator, query: str) -> dict:
    """Run a query through the PlanningOrchestrator and collect all results."""
    trace = start_trace(query)
    t0 = time.monotonic()

    chunks: list[str] = []
    tokens: dict = {}
    errors: list[str] = []

    try:
        async for event in orchestrator.run_sse(query):
            if event["type"] == "text":
                chunks.append(event["chunk"])
            elif event["type"] == "done":
                tokens = event.get("tokens", {})
            elif event["type"] == "error":
                errors.append(event["message"])
    except Exception as exc:
        errors.append(str(exc))

    return {
        "response": "".join(chunks),
        "latency_s": time.monotonic() - t0,
        "tokens": tokens,
        "routing_trace": trace.to_dict(),
        "plan": trace.plan or {},
        "errors": errors,
        "success": len(errors) == 0,
    }


def compute_plan_stats(plan: dict) -> dict:
    """Extract planning-efficiency metrics from a plan dict.

    Replicates the topological wave decomposition of PlanningOrchestrator to
    compute the critical path length and maximum parallelism in a plan.
    """
    steps = plan.get("steps", [])
    if not steps:
        return {
            "plan_steps": 0,
            "parallel_ratio": 0.0,
            "critical_path_length": 0,
            "max_parallel_steps": 0,
        }

    completed: set = set()
    waves: list[list] = []
    remaining = list(steps)

    while remaining:
        wave = [
            s for s in remaining
            if all(d in completed for d in s.get("depends_on", []))
        ]
        if not wave:
            break
        waves.append(wave)
        for s in wave:
            completed.add(s["id"])
        remaining = [s for s in remaining if s not in wave]

    n = len(steps)
    max_wave = max(len(w) for w in waves) if waves else 1

    return {
        "plan_steps": n,
        "parallel_ratio": round(max_wave / n, 3) if n else 0.0,
        "critical_path_length": len(waves),
        "max_parallel_steps": max_wave,
    }


# ── MLflow artifact helper ────────────────────────────────────────────────────

def _log_text_artifact(content: str, filename: str) -> None:
    """Write content to a temp file and log it as an MLflow artifact."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=f"_{filename}", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp = f.name
    try:
        mlflow.log_artifact(tmp)
    finally:
        os.unlink(tmp)


# ── Per-case benchmark ────────────────────────────────────────────────────────

async def run_benchmark_case(
    orchestrator,
    prompt: BenchmarkPrompt,
    scorer_client: AsyncAzureOpenAI,
    scorer_deployment: str,
    version: str,
    case_idx: int,
) -> dict:
    """Run one test case and log all results to a nested MLflow child run.

    Logged per child run:
        params  — query, expected_answer, expected_agents
        metrics — llm_score, routing_score, latency_s, tokens, plan_stats,
                  routing_precision, routing_recall
        tags    — version, category, difficulty, llm_rationale, routing_rationale
        artifacts — response.txt, routing_trace.json, plan.json, errors.txt
    Also creates an MLflow Trace (visible in the Traces tab) with child spans
    per phase: plan_generation, step_{n}_{agent}, synthesis.
    """
    from eval.mlflow_tracing import instrument_orchestrator

    run_name = f"tc{case_idx:02d}_{prompt.category}_{prompt.difficulty}"

    with mlflow.start_run(run_name=run_name, nested=True) as child_run:
        # ── Tags & params ─────────────────────────────────────────────────────
        mlflow.set_tags({
            "version": version,
            "category": prompt.category,
            "difficulty": prompt.difficulty,
            "expected_agents": ",".join(prompt.expected_agents),
        })
        mlflow.log_params({
            "query": prompt.text[:250],
            "expected_answer": prompt.expected_answer[:250],
            "expected_agents": ",".join(prompt.expected_agents),
        })

        # ── Run orchestrator (with MLflow trace) ──────────────────────────────
        print(f"  [{case_idx:02d}] [{prompt.category}/{prompt.difficulty}] {prompt.text[:70]!r}")

        phase_timings: dict = {}
        try:
            _trace_ctx = (
                mlflow.start_trace(name=run_name)
                if hasattr(mlflow, "start_trace")
                else __import__("contextlib").nullcontext()
            )
            with _trace_ctx:
                async with instrument_orchestrator(orchestrator) as _pt:
                    result = await run_and_collect(orchestrator, prompt.text)
                phase_timings = _pt
        except Exception as _te:
            print(f"       [trace unavailable: {_te}]")
            result = await run_and_collect(orchestrator, prompt.text)

        plan_stats = compute_plan_stats(result["plan"])

        # ── Score answer quality (LLM-as-a-Judge) ────────────────────────────
        llm_score, llm_rationale, llm_comments = await evaluate(
            scorer_client, scorer_deployment,
            question=prompt.text,
            expected_answer=prompt.expected_answer,
            actual_response=result["response"],
            success=result["success"],
        )

        # ── Score routing accuracy (LLM-as-a-Judge) ──────────────────────────
        routing_score, routing_rationale = await evaluate_routing(
            scorer_client, scorer_deployment,
            question=prompt.text,
            routing_trace_json=json.dumps(result["routing_trace"]),
        )

        # ── Compute routing precision / recall ────────────────────────────────
        invoked = {
            inv["agent"]
            for inv in result["routing_trace"].get("invoked_agents", [])
        }
        expected = set(prompt.expected_agents)
        routing_precision = len(invoked & expected) / len(invoked) if invoked else 0.0
        routing_recall = len(invoked & expected) / len(expected) if expected else 0.0

        # ── Log metrics ───────────────────────────────────────────────────────
        metrics: dict[str, float] = {
            "llm_score":        float(llm_score or 0),
            "routing_score":    float(routing_score or 0),
            "latency_s":        round(result["latency_s"], 3),
            "input_tokens":     float(result["tokens"].get("input", 0) or 0),
            "output_tokens":    float(result["tokens"].get("output", 0) or 0),
            "total_tokens":     float(result["tokens"].get("total", 0) or 0),
            "success":          1.0 if result["success"] else 0.0,
            "routing_precision": round(routing_precision, 3),
            "routing_recall":    round(routing_recall, 3),
        }
        metrics.update({k: float(v) for k, v in plan_stats.items()})
        mlflow.log_metrics(metrics)

        # ── Log rationale as tags (searchable in MLflow UI) ───────────────────
        mlflow.set_tag("llm_rationale", llm_rationale[:250])
        mlflow.set_tag("routing_rationale", routing_rationale[:250])
        if llm_comments:
            mlflow.set_tag("llm_comments", llm_comments[:250])

        # ── Artifacts ─────────────────────────────────────────────────────────
        _log_text_artifact(result["response"], "response.txt")
        _log_text_artifact(
            json.dumps(result["routing_trace"], indent=2, ensure_ascii=False),
            "routing_trace.json",
        )
        if result["plan"]:
            _log_text_artifact(
                json.dumps(result["plan"], indent=2, ensure_ascii=False),
                "plan.json",
            )
        if phase_timings:
            _log_text_artifact(
                json.dumps(phase_timings, indent=2),
                "phase_timings.json",
            )
        if result["errors"]:
            _log_text_artifact("\n".join(result["errors"]), "errors.txt")

        print(
            f"       llm={llm_score}/5  routing={routing_score}/5"
            f"  latency={result['latency_s']:.1f}s"
            f"  tokens={result['tokens'].get('total', 0)}"
            f"  steps={plan_stats['plan_steps']}"
            f"  parallel={plan_stats['parallel_ratio']:.0%}"
        )

        return {
            "category": prompt.category,
            "difficulty": prompt.difficulty,
            "llm_score": llm_score,
            "routing_score": routing_score,
            "latency_s": result["latency_s"],
            "total_tokens": result["tokens"].get("total", 0) or 0,
            "plan_steps": plan_stats["plan_steps"],
            "run_id": child_run.info.run_id,
        }


# ── Agent / MCP server setup ──────────────────────────────────────────────────

def setup_agents(
    config: configparser.ConfigParser,
    skip_graph: bool,
    skip_sf: bool,
):
    """Authenticate, start MCP servers, and return (orchestrator, procs).

    Reuses authentication helpers from main.py to avoid duplication.
    """
    from main import (  # noqa: PLC0415  (local import to avoid circular deps)
        authenticate,
        _is_local_url,
        _start_graph_mcp_server,
        _start_salesforce_mcp_server,
        _start_smartsales_mcp_server,
        _resolve_ss_session,
        _resolve_sf_session,
    )

    procs = []
    azure = config["azure"]
    sf_section = config["salesforce"] if config.has_section("salesforce") else {}
    ss_section = config["smartsales"] if config.has_section("smartsales") else {}

    graph_agent = sf_agent = None

    # ── SmartSales (always) ───────────────────────────────────────────────────
    ss_url = ss_section.get("mcpServerUrl", "http://localhost:8002/mcp")
    ss_env = os.environ.copy()
    ss_env["MCP_RESOURCE_URI"] = (
        f"{urlparse(ss_url).scheme}://{urlparse(ss_url).netloc}"
    )
    if _is_local_url(ss_url):
        procs.append(_start_smartsales_mcp_server(ss_env, ss_url))
    ss_mcp = MCPStreamableHTTPTool(
        name="smartsales",
        url=ss_url,
        http_client=httpx.AsyncClient(
            auth=RefreshingBearerAuth(lambda: _resolve_ss_session(ss_url)),
            timeout=httpx.Timeout(120.0),
        ),
    )
    ss_agent = create_smartsales_agent(smartsales_mcp=ss_mcp)

    # ── Microsoft Graph ────────────────────────────────────────────
    if not skip_graph:
        mcp_url = azure.get("mcpServerUrl", "http://localhost:8000/mcp")
        print(f"[authenticate graph] mcp_url {mcp_url}")
        graph_env = os.environ.copy()
        graph_env["MCP_RESOURCE_URI"] = (
            f"{urlparse(mcp_url).scheme}://{urlparse(mcp_url).netloc}"
        )
        try:
            token = authenticate(
                client_id=azure["clientId"],
                tenant_id=azure["tenantId"],
                scopes=azure["graphUserScopes"].split(),
                client_secret=azure.get(
                    "clientSecret", os.environ.get("CLIENT_SECRET", "")
                ),
            )
            if _is_local_url(mcp_url):
                procs.append(_start_graph_mcp_server(graph_env, mcp_url))
            graph_mcp = MCPStreamableHTTPTool(
                name="graph",
                url=mcp_url,
                http_client=httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=httpx.Timeout(120.0),
                ),
            )
            graph_agent = create_graph_agent(graph_mcp=graph_mcp)
        except Exception as exc:
            print(f"WARNING: Microsoft Graph unavailable ({exc}). Graph prompts will score 1.")
            print("         Use --skip-graph to suppress this warning.")

    # ── Salesforce ─────────────────────────────────────────────────
    if not skip_sf:
        sf_url = sf_section.get("mcpServerUrl", "http://localhost:8001/mcp")
        sf_env = os.environ.copy()
        sf_env["MCP_RESOURCE_URI"] = (
            f"{urlparse(sf_url).scheme}://{urlparse(sf_url).netloc}"
        )
        try:
            if _is_local_url(sf_url):
                procs.append(_start_salesforce_mcp_server(sf_env, sf_url))
            sf_token = _resolve_sf_session(sf_url)
            sf_mcp = MCPStreamableHTTPTool(
                name="salesforce",
                url=sf_url,
                http_client=httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {sf_token}"},
                    timeout=httpx.Timeout(120.0),
                ),
            )
            sf_agent = create_salesforce_agent(salesforce_mcp=sf_mcp)
        except Exception as exc:
            print(f"WARNING: Salesforce unavailable ({exc}). CRM prompts will score 1.")
            print("         Use --skip-sf to suppress this warning.")

    orchestrator = create_planning_orchestrator(
        graph_agent=graph_agent,
        sf_agent=sf_agent,
        ss_agent=ss_agent,
    )
    return orchestrator, procs


# ── Main ──────────────────────────────────────────────────────────────────────

async def main_async(args: argparse.Namespace) -> None:
    config = configparser.ConfigParser()
    config.read("config.cfg")

    # ── Load + filter prompts ─────────────────────────────────────────────────
    prompts = _load_prompts(args.prompts) if args.prompts else list(BENCHMARK_PROMPTS)
    if args.category:
        prompts = [p for p in prompts if p.category == args.category]
    if args.difficulty:
        prompts = [p for p in prompts if p.difficulty == args.difficulty]

    if args.dry_run:
        print(f"DRY RUN — {len(prompts)} prompts:\n")
        for i, p in enumerate(prompts):
            print(f"  [{i:02d}] [{p.category}/{p.difficulty}] {p.text}")
            print(f"        expected_agents : {p.expected_agents}")
            print(f"        expected_answer : {p.expected_answer[:80]}")
            print()
        return

    # ── MLflow setup ──────────────────────────────────────────────────────────
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment(args.experiment)

    # ── Build agents ──────────────────────────────────────────────────────────
    orchestrator, procs = setup_agents(config, args.skip_graph, args.skip_sf)

    # ── Scorer ────────────────────────────────────────────────────────────────
    scorer_client = AsyncAzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version="2024-12-01-preview",
    )
    scorer_deployment = os.environ["deployment"]

    # ── Batch parent run ──────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parent_run_name = f"{args.version}_{timestamp}"

    try:
        with mlflow.start_run(run_name=parent_run_name) as parent:
            mlflow.set_tags({
                "version": args.version,
                "orchestrator": "planning",
                "n_prompts": str(len(prompts)),
                "skip_graph": str(args.skip_graph),
                "skip_sf": str(args.skip_sf),
                "tracing": "on",
            })

            print(f"\n{'─' * 64}")
            print(f"  Experiment : {args.experiment}")
            print(f"  Version    : {args.version}")
            print(f"  Parent run : {parent_run_name}")
            print(f"  Prompts    : {len(prompts)}")
            print(f"  Tracing    : on (plan/execute/synthesis spans)")
            print(f"{'─' * 64}\n")

            all_results = []
            for i, prompt in enumerate(prompts):
                result = await run_benchmark_case(
                    orchestrator, prompt,
                    scorer_client, scorer_deployment,
                    version=args.version,
                    case_idx=i,
                )
                all_results.append(result)

            # ── Aggregate metrics on parent run ───────────────────────────────
            def _mean(lst: list) -> float:
                return sum(lst) / len(lst) if lst else 0.0

            def _p95(lst: list) -> float:
                s = sorted(lst)
                return s[max(0, int(len(s) * 0.95) - 1)] if s else 0.0

            llm_scores  = [r["llm_score"]     for r in all_results if r["llm_score"]     is not None]
            r_scores    = [r["routing_score"] for r in all_results if r["routing_score"] is not None]
            latencies   = [r["latency_s"]     for r in all_results]
            tok_totals  = [r["total_tokens"]  for r in all_results]

            mlflow.log_metrics({
                "avg_llm_score":     round(_mean(llm_scores), 3),
                "avg_routing_score": round(_mean(r_scores), 3),
                "avg_latency_s":     round(_mean(latencies), 3),
                "p95_latency_s":     round(_p95(latencies), 3),
                "avg_total_tokens":  round(_mean(tok_totals), 1),
                "n_prompts":         float(len(prompts)),
                "n_scored":          float(len(llm_scores)),
            })

            print(f"\n{'─' * 64}")
            print(f"  avg llm score     : {_mean(llm_scores):.2f} / 5   (n={len(llm_scores)})")
            print(f"  avg routing score : {_mean(r_scores):.2f} / 5   (n={len(r_scores)})")
            print(f"  avg latency       : {_mean(latencies):.1f} s")
            print(f"  p95 latency       : {_p95(latencies):.1f} s")
            print(f"  avg total tokens  : {_mean(tok_totals):.0f}")
            print(f"  MLflow run ID     : {parent.info.run_id}")
            print(f"{'─' * 64}")
            print(f"\n  To view results: mlflow ui   →  http://localhost:5000")
            print(f"  Experiment      : {args.experiment}")
            print(f"  Compare runs    : select multiple runs → Compare in the MLflow UI\n")

    finally:
        for proc in procs:
            proc.terminate()
            proc.wait()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MLflow benchmark for the PlanningOrchestrator"
    )
    parser.add_argument(
        "--version", required=True,
        help="Version label for this run (e.g. baseline, v1, prompt-v2)",
    )
    parser.add_argument(
        "--experiment", default="graphxmaf-eval",
        help="MLflow experiment name  [default: graphxmaf-eval]",
    )
    parser.add_argument(
        "--prompts",
        help="Path to a custom prompts JSON file  [default: eval/prompts.json]",
    )
    parser.add_argument(
        "--category",
        help="Only run prompts in this category (e.g. email, calendar, cross-system, accounts, ...)",
    )
    parser.add_argument(
        "--difficulty",
        choices=["simple", "medium", "hard"],
        help="Only run prompts of this difficulty level",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print prompts without running any agents",
    )
    parser.add_argument(
        "--skip-graph", action="store_true",
        help="Skip Microsoft Graph authentication (Graph prompts will score 1)",
    )
    parser.add_argument(
        "--skip-sf", action="store_true",
        help="Skip Salesforce authentication (CRM prompts will score 1)",
    )
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
