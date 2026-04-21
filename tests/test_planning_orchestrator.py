"""tests/test_planning_orchestrator.py — unit tests voor PlanningOrchestrator.

Geen echte MCP servers of Azure OpenAI nodig: alle agents zijn gemockt.

Run:
    python -m pytest tests/test_planning_orchestrator.py -v
"""
import asyncio
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.planning_orchestrator import PlanningOrchestrator


# ── Mock helpers ──────────────────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.usage_details = {}


class FakeAgent:
    """Agent die altijd een vaste tekst teruggeeft."""
    def __init__(self, reply: str = "ok", delay: float = 0.0):
        self._reply = reply
        self._delay = delay

    async def run(self, prompt, **kwargs):
        if self._delay:
            await asyncio.sleep(self._delay)
        return FakeResponse(self._reply)


class FailingAgent:
    """Agent die altijd een exception gooit."""
    async def run(self, prompt, **kwargs):
        raise RuntimeError("agent unavailable")


class PlannerAgent:
    """Geeft een hardgecodeerd plan terug als JSON."""
    def __init__(self, plan: dict):
        self._plan = plan

    async def run(self, prompt, **kwargs):
        return FakeResponse(json.dumps(self._plan))


def _make_orchestrator(plan: dict, graph=None, sf=None, ss=None, step_timeout=5.0):
    planner = PlannerAgent(plan)
    synthesizer = FakeAgent(reply="Synthesized answer.")
    return PlanningOrchestrator(
        planner=planner,
        synthesizer=synthesizer,
        graph_agent=graph,
        sf_agent=sf,
        ss_agent=ss,
        step_timeout=step_timeout,
    )


async def collect(orchestrator, query="test"):
    """Collect all SSE events from run_sse into a dict."""
    events = []
    async for event in orchestrator.run_sse(query):
        events.append(event)
    texts  = [e["chunk"]   for e in events if e["type"] == "text"]
    errors = [e["message"] for e in events if e["type"] == "error"]
    done   = next((e for e in events if e["type"] == "done"), None)
    return {"texts": texts, "errors": errors, "done": done}


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_happy_path():
    """Beide agents slagen → synthesis + done event."""
    plan = {
        "query": "test",
        "reasoning": "test",
        "steps": [
            {"id": 1, "agent": "graph",      "task": "get emails",   "depends_on": []},
            {"id": 2, "agent": "salesforce", "task": "get accounts", "depends_on": []},
        ],
        "synthesis": "combine",
    }
    orch = _make_orchestrator(plan, graph=FakeAgent("emails"), sf=FakeAgent("accounts"))
    result = await collect(orch)
    assert result["errors"] == []
    assert result["done"] is not None
    assert any("Synthesized" in t for t in result["texts"])


@pytest.mark.asyncio
async def test_partial_failure_continues_to_synthesis():
    """Issue 4: één agent faalt → error event, maar synthesis loopt wél door."""
    plan = {
        "query": "test",
        "reasoning": "test",
        "steps": [
            {"id": 1, "agent": "graph",      "task": "get emails",   "depends_on": []},
            {"id": 2, "agent": "salesforce", "task": "get accounts", "depends_on": []},
        ],
        "synthesis": "combine",
    }
    orch = _make_orchestrator(plan, graph=FailingAgent(), sf=FakeAgent("accounts"))
    result = await collect(orch)

    # Er is een error voor graph
    assert any("graph" in e for e in result["errors"])
    # Maar synthesis heeft wél gedraaid
    assert result["done"] is not None
    assert any("Synthesized" in t for t in result["texts"])


@pytest.mark.asyncio
async def test_step_timeout():
    """Issue 7: agent duurt langer dan timeout → TimeoutError als step-fout, synthesis draait door."""
    plan = {
        "query": "test",
        "reasoning": "test",
        "steps": [
            {"id": 1, "agent": "smartsales", "task": "get locations", "depends_on": []},
        ],
        "synthesis": "combine",
    }
    slow_agent = FakeAgent(reply="locations", delay=10.0)
    orch = _make_orchestrator(plan, ss=slow_agent, step_timeout=0.1)
    result = await collect(orch)

    assert any("smartsales" in e for e in result["errors"])
    assert result["done"] is not None  # synthesis draait door


@pytest.mark.asyncio
async def test_session_forwarded():
    """Issue 6: session wordt doorgegeven aan agent.run()."""
    received_kwargs = {}

    class SessionCapturingAgent:
        async def run(self, prompt, **kwargs):
            received_kwargs.update(kwargs)
            return FakeResponse("ok")

    plan = {
        "query": "test",
        "reasoning": "test",
        "steps": [{"id": 1, "agent": "graph", "task": "do something", "depends_on": []}],
        "synthesis": "combine",
    }
    orch = _make_orchestrator(plan, graph=SessionCapturingAgent())

    class FakeSession:
        pass

    fake_session = FakeSession()
    async for _ in orch.run_sse("test", session=fake_session):
        pass

    assert received_kwargs.get("session") is fake_session


@pytest.mark.asyncio
async def test_dag_parallel_waves():
    """Stappen zonder afhankelijkheid lopen in dezelfde wave (parallel)."""
    order = []

    class OrderTrackingAgent:
        def __init__(self, name):
            self.name = name
        async def run(self, prompt, **kwargs):
            order.append(self.name)
            return FakeResponse(f"result-{self.name}")

    plan = {
        "query": "test",
        "reasoning": "test",
        "steps": [
            {"id": 1, "agent": "graph",      "task": "a", "depends_on": []},
            {"id": 2, "agent": "salesforce", "task": "b", "depends_on": []},
            {"id": 3, "agent": "smartsales", "task": "c", "depends_on": [1, 2]},
        ],
        "synthesis": "combine",
    }
    orch = _make_orchestrator(
        plan,
        graph=OrderTrackingAgent("graph"),
        sf=OrderTrackingAgent("salesforce"),
        ss=OrderTrackingAgent("smartsales"),
    )
    result = await collect(orch)
    assert result["errors"] == []
    # stap 3 (smartsales) moet na 1 en 2 komen
    assert order.index("smartsales") > order.index("graph")
    assert order.index("smartsales") > order.index("salesforce")
