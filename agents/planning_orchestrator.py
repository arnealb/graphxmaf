"""agents/planning_orchestrator.py — Plan-then-Execute Orchestrator (V2).

Architecture:
1. PlannerAgent produces a structured JSON execution plan (LLM call, no tools)
2. Plan is validated and executed as a DAG (waves of parallel steps)
3. SynthesizerAgent produces a final answer from all step results (LLM call, no tools)

Academic references:
- HuggingGPT (Shen et al., NeurIPS 2023) — task planning + parallel execution + synthesis
- AOP (Zhang et al., ICLR 2025) — structured decomposition with depends_on DAG
- Least-to-Most (Zhou et al., ICLR 2023) — dependency injection into task descriptions
- ReAct (Yao et al., ICLR 2023) — reasoning traces in plan.reasoning field
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from agent_framework import Agent
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv

from agents.routing_trace import AgentInvocation, get_trace

load_dotenv()
log = logging.getLogger(__name__)

deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"

# ── Prompts ────────────────────────────────────────────────────────────────────

PLAN_SYSTEM_PROMPT = """You are a planning agent. Given a user query and a list of available agents,
produce a structured execution plan.

Respond ONLY with valid JSON — no markdown, no code fences, no explanation.

Output schema:
{
  "query": "<original user query>",
  "reasoning": "<brief explanation of why you chose these steps>",
  "steps": [
    {
      "id": 1,
      "agent": "<graph|salesforce|smartsales>",
      "task": "<self-contained description of what the agent must do>",
      "depends_on": []
    }
  ],
  "synthesis": "<instruction for combining the step results into a final answer>"
}

Rules:
- Use the MINIMUM number of steps necessary to answer the query.
- Only use agents listed as available.
- Set depends_on to [] unless a step genuinely requires the OUTPUT of a previous step.
- When a step needs data from a previous step, list the previous step id(s) in depends_on.
  The enriched task description will automatically include those results at execution time.
- Steps with no dependencies can run in parallel — design the plan accordingly.
- The "task" field must be a self-contained instruction the agent can execute directly.
- Do NOT add steps for formatting or summarizing — the synthesis instruction handles that.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are a synthesis agent. Given a user query, an execution plan, and
the results from each step, produce a clear and helpful final answer.

Style rules:
- Be concise and factual.
- Use bullet points or sections when presenting data from multiple sources.
- Clearly indicate which system each piece of information comes from
  (e.g. "From Microsoft 365: ..." / "From Salesforce: ..." / "From SmartSales: ...").
- Present dates in a human-readable format (e.g. "15 April 2026").
- Never fabricate data — only report what the step results contain.
- If a step returned no useful result, say so briefly and continue.
"""


# ── PlanningOrchestrator ───────────────────────────────────────────────────────

class PlanningOrchestrator:
    """Plan-then-Execute orchestrator.

    1. PlannerAgent generates a JSON execution plan (no tools)
    2. Plan is executed as a DAG (topological waves, parallel within each wave)
    3. SynthesizerAgent combines all results into a final answer (no tools)
    """

    def __init__(
        self,
        planner: Agent,
        synthesizer: Agent,
        graph_agent: Optional[Agent] = None,
        sf_agent: Optional[Agent] = None,
        ss_agent: Optional[Agent] = None,
    ):
        self._planner = planner
        self._synthesizer = synthesizer
        self._graph_agent = graph_agent
        self._sf_agent = sf_agent
        self._ss_agent = ss_agent
        self._input_tokens: int = 0
        self._output_tokens: int = 0

    def _accumulate_usage(self, resp) -> None:
        """Add token counts from an agent response to the running totals."""
        usage = getattr(resp, "usage_details", None) or {}
        self._input_tokens  += usage.get("input_token_count",  0) or 0
        self._output_tokens += usage.get("output_token_count", 0) or 0

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run_sse(self, query: str, session=None) -> AsyncGenerator[dict, None]:
        """Async generator yielding SSE event dicts for one orchestrator run.

        Yields dicts with keys:
          {"type": "text", "chunk": str}
          {"type": "done", "tokens": {"input": int, "output": int, "total": int}}
          {"type": "error", "message": str}
        """
        self._input_tokens = 0
        self._output_tokens = 0
        yield {"type": "text", "chunk": "Planning query...\n"}

        # ── Phase 1: Planning ──────────────────────────────────────────────────
        try:
            plan = await self._create_plan(query)
        except Exception as exc:
            log.error("Planning failed: %s", exc, exc_info=True)
            yield {"type": "error", "message": f"Planning failed: {exc}"}
            return

        trace = get_trace()
        if trace is not None:
            trace.plan = plan

        steps = plan.get("steps", [])
        yield {"type": "text", "chunk": f"Plan: {len(steps)} stap(pen)\n"}

        # ── Phase 2: DAG execution ─────────────────────────────────────────────
        results: dict[int, str] = {}
        try:
            waves = self._topological_waves(steps)
            log.info("[run_sse] waves: %s", waves)
        except ValueError as exc:
            yield {"type": "error", "message": str(exc)}
            return

        for wave in waves:
            agent_names = []
            for s in wave:
                agent_names.append(s["agent"])
            agents_label = ", ".join(agent_names)
            yield {"type": "text", "chunk": f"️Executing ({agents_label})...\n"}

            step_inputs = [(s, self._enrich_task(s, results)) for s in wave]
            wave_start = datetime.now(timezone.utc).isoformat()
            coros = [self._execute_step(s, task) for s, task in step_inputs]
            wave_results = await asyncio.gather(*coros, return_exceptions=True)

            wave_end = datetime.now(timezone.utc).isoformat()

            # Resultaten verwerken — per index door beide lijsten lopen
            for i in range(len(step_inputs)):
                step, task_input = step_inputs[i]
                res = wave_results[i]

                # wel fout
                if isinstance(res, BaseException):
                    err_msg = str(res) or repr(res)
                    log.error("Step %d (%s) failed: %s", step["id"], step["agent"], err_msg, exc_info=res)

                    current_trace = get_trace()
                    if current_trace is not None:
                        invocation = AgentInvocation(
                            agent=step["agent"],
                            order=step["id"],
                            input=task_input,
                            started_at=wave_start,
                            ended_at=wave_end,
                            success=False,
                            error=err_msg,
                        )
                        current_trace.invoked_agents.append(invocation)

                    yield {
                        "type": "error",
                        "message": f"Step {step['id']} ({step['agent']}) failed: {err_msg}",
                    }
                    return

                # geen fout
                results[step["id"]] = res

                current_trace = get_trace()
                if current_trace is not None:
                    invocation = AgentInvocation(
                        agent=step["agent"],
                        order=step["id"],
                        input=task_input,
                        started_at=wave_start,
                        ended_at=wave_end,
                        success=True,
                        error=None,
                    )
                    current_trace.invoked_agents.append(invocation)

        # ── Phase 3: Synthesis ─────────────────────────────────────────────────
        yield {"type": "text", "chunk": "Synthesizing...\n"}
        try:
            answer = await self._synthesize(query, plan, results)
        except Exception as exc:
            log.error("Synthesis failed: %s", exc, exc_info=True)
            yield {"type": "error", "message": f"Synthesis failed: {exc}"}
            return

        yield {"type": "text", "chunk": answer}
        total = self._input_tokens + self._output_tokens
        yield {
            "type": "done",
            "tokens": {
                "input":  self._input_tokens,
                "output": self._output_tokens,
                "total":  total,
            },
        }

    # ── Internal: Planning ─────────────────────────────────────────────────────

    async def _create_plan(self, query: str) -> dict:
        """Call the planner agent, parse + validate the JSON plan. Retries once."""
        available = self._available_agents_description()
        prompt = f"Available agents: {available}\n\nUser query: {query}"

        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(2):
            try:
                resp = await self._planner.run(prompt)
                self._accumulate_usage(resp)
                raw = resp.text
                if raw is None:
                    raw = ""
                raw = raw.strip()

                # markdown stuff weghalen
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    # Eerste regel (opening fence) weggooien
                    lines = lines[1:]
                    # Laatste regel weggooien als die een closing fence is
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    raw = "\n".join(lines)


                plan = json.loads(raw)
                self._validate_plan(plan)
                log.info("Generated plan:\n%s", json.dumps(plan, indent=2, ensure_ascii=False))
                return plan
            except (json.JSONDecodeError, KeyError, ValueError, AssertionError) as exc:
                last_exc = exc
                log.warning("Plan attempt %d failed: %s", attempt + 1, exc)

        raise RuntimeError(f"Failed to produce a valid plan after 2 attempts: {last_exc}")

    def _validate_plan(self, plan: dict) -> None:
        assert "steps" in plan, "Missing 'steps' key"
        assert isinstance(plan["steps"], list), "'steps' must be a list"
        assert len(plan["steps"]) > 0, "'steps' must not be empty"
        valid_agents = {
            name
            for name, agent in [
                ("graph", self._graph_agent),
                ("salesforce", self._sf_agent),
                ("smartsales", self._ss_agent),
            ]
            if agent is not None
        }
        step_ids: set = set()
        for step in plan["steps"]:
            assert "id" in step, f"Step missing 'id': {step}"
            assert step["id"] not in step_ids, f"Duplicate step id: {step['id']}"
            step_ids.add(step["id"])
            assert "agent" in step, f"Step missing 'agent': {step}"
            assert "depends_on" in step, f"Step missing 'depends_on': {step}"
            assert isinstance(step["depends_on"], list), f"'depends_on' must be a list in step {step['id']}"
            assert step["agent"] in valid_agents, (
                f"Unknown agent '{step['agent']}' in step {step['id']}. "
                f"Valid: {valid_agents}"
            )
        for step in plan["steps"]:
            for dep_id in step["depends_on"]:
                assert dep_id in step_ids, (
                    f"Step {step['id']} depends_on unknown step id {dep_id}"
                )

    def _available_agents_description(self) -> str:
        agents = []
        if self._graph_agent is not None:
            agents.append("graph (Microsoft 365: emails, calendar, OneDrive, contacts)")
        if self._sf_agent is not None:
            agents.append("salesforce (CRM: accounts, contacts, leads, opportunities)")
        if self._ss_agent is not None:
            agents.append("smartsales (locations, catalog items)")
        return ", ".join(agents)

    # ── Internal: DAG execution ────────────────────────────────────────────────

    def _topological_waves(self, steps: list[dict]) -> list[list[dict]]:
        """Group steps into sequential waves of parallel-executable steps."""
        completed: set[int] = set()
        waves: list[list[dict]] = []
        remaining = list(steps)

        while remaining:
            wave = []
            for step in remaining:
                dependencies_done = True
                for dep in step["depends_on"]:
                    if dep not in completed:
                        dependencies_done = False
                        break
                if dependencies_done:
                    wave.append(step)

            if not wave:
                remaining_ids = []
                for step in remaining:
                    remaining_ids.append(step["id"])
                raise ValueError(
                    f"Circular dependency detected in plan steps: {remaining_ids}"
                )

            waves.append(wave)
            for step in wave:
                completed.add(step["id"])

            new_remaining = []
            for step in remaining:
                if step not in wave:
                    new_remaining.append(step)
            remaining = new_remaining

        return waves

    def _enrich_task(self, step: dict, results: dict) -> str:
        """Inject results of dependency steps into the task description."""
        deps = step.get("depends_on", [])
        if not deps:
            return step["task"]
        context_parts = [
            f"[Result from step {d}]:\n{results[d]}"
            for d in deps
            if d in results
        ]
        if not context_parts:
            return step["task"]
        context = "\n\n".join(context_parts)
        return f"{context}\n\n[Task]:\n{step['task']}"

    async def _execute_step(self, step: dict, task: str) -> str:
        """Execute a single plan step by calling the appropriate sub-agent."""
        agent_map = {
            "graph": self._graph_agent,
            "salesforce": self._sf_agent,
            "smartsales": self._ss_agent,
        }
        agent = agent_map.get(step["agent"])
        if agent is None:
            raise ValueError(f"Agent '{step['agent']}' is not available in this session")
        resp = await agent.run(task)
        self._accumulate_usage(resp)
        return resp.text or ""

    # ── Internal: Synthesis ────────────────────────────────────────────────────

    async def _synthesize(self, query: str, plan: dict, results: dict) -> str:
        """Call the synthesizer agent to combine all step results."""
        parts = [
            f"User query: {query}",
            f"\nSynthesis instruction: {plan.get('synthesis', 'Combine all results into a clear answer.')}",
            "\nStep results:",
        ]
        for step in plan.get("steps", []):
            sid = step["id"]
            agent = step["agent"]
            result = results.get(sid, "(no result)")
            parts.append(f"\n[Step {sid} — {agent}]:\n{result}")

        context = "\n".join(parts)
        resp = await self._synthesizer.run(context)
        self._accumulate_usage(resp)
        return resp.text or ""


# ── Factory ────────────────────────────────────────────────────────────────────

def create_planning_orchestrator(
    graph_agent: Optional[Agent] = None,
    sf_agent: Optional[Agent] = None,
    ss_agent: Optional[Agent] = None,
) -> PlanningOrchestrator:
    """Create a PlanningOrchestrator with planner + synthesizer agents."""
    client_kwargs = dict(
        deployment_name=deployment,
        endpoint=endpoint,
        api_key=subscription_key,
        api_version=api_version,
    )

    planner = Agent(
        client=AzureOpenAIChatClient(**client_kwargs),
        name="PlannerAgent",
        description="Produces a structured JSON execution plan for the given query",
        instructions=PLAN_SYSTEM_PROMPT,
        tools=[],
    )

    synthesizer = Agent(
        client=AzureOpenAIChatClient(**client_kwargs),
        name="SynthesizerAgent",
        description="Synthesizes sub-agent results into a final answer",
        instructions=SYNTHESIS_SYSTEM_PROMPT,
        tools=[],
    )

    return PlanningOrchestrator(
        planner=planner,
        synthesizer=synthesizer,
        graph_agent=graph_agent,
        sf_agent=sf_agent,
        ss_agent=ss_agent,
    )
