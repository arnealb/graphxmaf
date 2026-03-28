"""agents/routing_trace.py — Lightweight routing observability for the OrchestratorAgent.

Each orchestrator run gets a RoutingTrace instance stored in a ContextVar so that
the FunctionTool closures can append to it without changing their signatures or
return values.

Usage in eval/script.py:
    from agents.routing_trace import start_trace, get_trace

    trace = start_trace(prompt.text)          # before agent.run()
    response = await orchestrator.run(prompt.text)
    data = get_trace().to_dict()              # after agent.run()
"""
import json
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentInvocation:
    """A single sub-agent call recorded during one orchestrator run."""
    agent: str                  # "graph" | "salesforce" | "smartsales"
    order: int                  # 1-based invocation order within this run
    input: str                  # query string sent to the sub-agent
    started_at: str             # ISO-8601 UTC timestamp
    ended_at: str               # ISO-8601 UTC timestamp
    success: bool               # True unless the sub-agent raised an exception
    error: Optional[str]        # exception message when success=False, else None


@dataclass
class RoutingTrace:
    """Routing metadata for one orchestrator run."""
    user_query: str
    invoked_agents: list[AgentInvocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_query": self.user_query,
            "invoked_agents": [asdict(inv) for inv in self.invoked_agents],
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)


# ── ContextVar — async-safe, isolated per asyncio task ────────────────────────
#
# ContextVar.set() in a coroutine affects the current task's context copy.
# All coroutines awaited (not spawned as new tasks) share that context, so
# the tool closures called by agent_framework see the same RoutingTrace object.
# If agent_framework internally uses asyncio.create_task(), the spawned tasks
# still receive a copy that points to the SAME RoutingTrace instance, so
# mutations from inside closures are always visible to the caller.

_CURRENT_TRACE: ContextVar[Optional[RoutingTrace]] = ContextVar(
    "routing_trace", default=None
)


def start_trace(user_query: str) -> RoutingTrace:
    """Create a fresh RoutingTrace and bind it to the current async context.

    Call this once per orchestrator invocation, before agent.run().
    Returns the trace object so callers can hold a direct reference.
    """
    trace = RoutingTrace(user_query=user_query)
    _CURRENT_TRACE.set(trace)
    return trace


def get_trace() -> Optional[RoutingTrace]:
    """Return the RoutingTrace bound to the current async context, or None.

    Returns None when called outside of a start_trace() scope (e.g. when
    running non-orchestrator agents directly).
    """
    return _CURRENT_TRACE.get()
