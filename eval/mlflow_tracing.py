"""eval/mlflow_tracing.py — MLflow span tracing for the PlanningOrchestrator.

Instruments a PlanningOrchestrator instance so each internal phase emits its
own MLflow span with:
  - correct SpanType (LLM for planner/synthesizer, AGENT for execution steps)
  - inputs / outputs on every span
  - per-span token usage  ({"input_tokens": N, "output_tokens": N, "total_tokens": N})
    derived from the orchestrator's running _input_tokens / _output_tokens counters
  - per-step llm_turns and tool_calls list (read from RoutingTrace after each step)

The token usage makes MLflow's "Token usage" and "Cost breakdown" panels in the
Traces UI populate correctly.

Requirements:
    mlflow >= 2.13  (start_trace / start_span / SpanType)
"""

import time
from contextlib import asynccontextmanager, nullcontext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.planning_orchestrator import PlanningOrchestrator


# ── SpanType constants (graceful fallback) ────────────────────────────────────

try:
    from mlflow.entities import SpanType as _ST
    _SPAN_LLM   = _ST.LLM
    _SPAN_AGENT = _ST.AGENT
    _SPAN_CHAIN = _ST.CHAIN
except Exception:
    _SPAN_LLM = _SPAN_AGENT = _SPAN_CHAIN = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _span(name: str, span_type=None):
    """Return mlflow.start_span(...) or nullcontext() when unavailable."""
    try:
        import mlflow
        if hasattr(mlflow, "start_span"):
            kwargs: dict = {"name": name}
            if span_type is not None:
                kwargs["span_type"] = span_type
            return mlflow.start_span(**kwargs)
    except Exception:
        pass
    return nullcontext()


def _safe(fn, *args, **kwargs):
    """Call fn(*args, **kwargs), silently ignore any exception."""
    try:
        fn(*args, **kwargs)
    except Exception:
        pass


def _usage(orch, before: tuple[int, int]) -> dict:
    """Token delta between *before* snapshot and current orchestrator counters."""
    inp  = max(0, orch._input_tokens  - before[0])
    out  = max(0, orch._output_tokens - before[1])
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}


def _snap(orch) -> tuple[int, int]:
    """Snapshot current token counters."""
    return (orch._input_tokens, orch._output_tokens)


# ── Core context manager ──────────────────────────────────────────────────────

@asynccontextmanager
async def instrument_orchestrator(orchestrator: "PlanningOrchestrator"):
    """Async context manager — patches the three PlanningOrchestrator phases
    with MLflow child spans, per-phase timing, and per-phase token counts.

    Must be called inside an active mlflow.start_trace() context.

    Yields a *phase_timings* dict populated during execution:
        {
            "plan":     {"latency_s": 1.2,  "steps": 2,
                         "input_tokens": 320, "output_tokens": 180},
            "steps":    [{"step_id": 1, "agent": "graph",
                          "latency_s": 0.8,
                          "input_tokens": 210, "output_tokens": 95}, ...],
            "synthesis":{"latency_s": 0.9,
                         "input_tokens": 410, "output_tokens": 220},
        }
    """
    orig_create_plan  = orchestrator._create_plan
    orig_execute_step = orchestrator._execute_step
    orig_synthesize   = orchestrator._synthesize

    phase_timings: dict = {"plan": {}, "steps": [], "synthesis": {}}

    # ── plan_generation  (SpanType.LLM) ──────────────────────────────────────

    async def _plan(query: str, **kwargs) -> dict:
        before = _snap(orchestrator)
        with _span("plan_generation", _SPAN_LLM) as sp:
            _safe(sp.set_inputs, {"query": query[:500]}) if sp else None
            t0   = time.monotonic()
            plan = await orig_create_plan(query, **kwargs)
            elapsed = time.monotonic() - t0
            usage   = _usage(orchestrator, before)
            n       = len(plan.get("steps", []))
            phase_timings["plan"] = {
                "latency_s": round(elapsed, 3),
                "steps":     n,
                **usage,
            }
            if sp:
                _safe(sp.set_outputs, {
                    "n_steps":   str(n),
                    "reasoning": plan.get("reasoning", "")[:300],
                    "agents":    str([s["agent"] for s in plan.get("steps", [])]),
                    "usage":     usage,
                })
        return plan

    # ── step_{n}_{agent}  (SpanType.AGENT) ───────────────────────────────────

    async def _step(step: dict, task: str, **kwargs) -> str:
        from agents.routing_trace import get_trace
        before    = _snap(orchestrator)
        span_name = f"step_{step['id']}_{step['agent']}"
        with _span(span_name, _SPAN_AGENT) as sp:
            if sp:
                _safe(sp.set_inputs, {
                    "agent":      step["agent"],
                    "depends_on": str(step.get("depends_on", [])),
                    "task":       task[:400],
                })
            t0     = time.monotonic()
            result = await orig_execute_step(step, task, **kwargs)
            elapsed = time.monotonic() - t0
            usage   = _usage(orchestrator, before)

            # Read llm_turns and tool_calls recorded by _execute_step in routing trace.
            trace = get_trace()
            last_inv = (
                trace.invoked_agents[-1]
                if trace and trace.invoked_agents
                and trace.invoked_agents[-1].order == step["id"]
                else None
            )
            llm_turns    = last_inv.llm_turns  if last_inv else 0
            tool_calls   = last_inv.tool_calls if last_inv else []
            n_tool_calls = len(tool_calls)

            phase_timings["steps"].append({
                "step_id":     step["id"],
                "agent":       step["agent"],
                "latency_s":   round(elapsed, 3),
                "llm_turns":   llm_turns,
                "n_tool_calls": n_tool_calls,
                "tool_calls":  tool_calls,
                **usage,
            })
            if sp:
                _safe(sp.set_outputs, {
                    "result":       result[:400],
                    "llm_turns":    str(llm_turns),
                    "n_tool_calls": str(n_tool_calls),
                    "tool_calls":   str(tool_calls),
                    "usage":        usage,
                })
        return result

    # ── synthesis  (SpanType.LLM) ─────────────────────────────────────────────

    async def _synth(query: str, plan: dict, results: dict, **kwargs) -> str:
        before = _snap(orchestrator)
        with _span("synthesis", _SPAN_LLM) as sp:
            if sp:
                _safe(sp.set_inputs, {
                    "query":     query[:300],
                    "n_results": str(len(results)),
                })
            t0     = time.monotonic()
            answer = await orig_synthesize(query, plan, results, **kwargs)
            elapsed = time.monotonic() - t0
            usage   = _usage(orchestrator, before)
            phase_timings["synthesis"] = {
                "latency_s": round(elapsed, 3),
                **usage,
            }
            if sp:
                _safe(sp.set_outputs, {
                    "response": answer[:500],
                    "usage":    usage,
                })
        return answer

    # ── patch / yield / restore ───────────────────────────────────────────────

    orchestrator._create_plan  = _plan
    orchestrator._execute_step = _step
    orchestrator._synthesize   = _synth

    try:
        yield phase_timings
    finally:
        orchestrator._create_plan  = orig_create_plan
        orchestrator._execute_step = orig_execute_step
        orchestrator._synthesize   = orig_synthesize
