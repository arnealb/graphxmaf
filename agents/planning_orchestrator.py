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

Avoiding over-planning (same-agent queries):
- If a query only involves one system, use ONE step unless the second call genuinely requires
  specific IDs or values returned by the first (e.g. search → fetch details by ID).
- When related data can be included in a single call (e.g. opportunities WITH their account's
  billing country), ask for everything in one task description. Do NOT split "fetch" and
  "enrich" into two same-agent steps when the agent can return all needed fields in one call.

Handling dependent steps with potentially empty parents:
- When a step depends on a previous step that may return no results, write the task so the
  agent can handle the empty case. Example: "Using the account names from step 1 (if any),
  check for matching calendar events. If step 1 returned no results, state that and skip
  the calendar lookup."

Document and policy queries:
- Questions about internal company rules, procedures, HR policies, expense reimbursement,
  onboarding, contracts, or how-to questions about internal processes should route to the
  graph agent with a task to search OneDrive for the relevant document.
- These queries do NOT require salesforce or smartsales unless they also ask for CRM or
  location data.
- Examples: "what is the expense policy?", "how do I request leave?", "what are the support
  terms with client X?", "what should I do if my car breaks down on the way to work?"

Entity-centric and 360° view queries:
- When the user asks for a "full picture", "overview", "briefing", "360 view", "everything
  about", or "what do we know about" a specific company, person, or topic — use ALL available
  agents. Do not wait for the user to name the individual systems.
- These queries are about a named entity (e.g. a company name, a person's name) and the goal
  is to aggregate what each system knows about that entity. Each agent should search for that
  entity by name within its own domain.
- Similarly, when the user asks about a relationship ("what is our relationship with X",
  "how do we work with X") or a status ("what is the current situation with X"), treat this
  as a 360° query and involve all agents.
- For person-centric queries ("who is X", "tell me about contact X"): use graph to find emails
  and calendar events involving that person, salesforce to look up CRM contacts/leads, and
  smartsales for any linked locations.
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
        step_timeout: float = 120.0,
    ):
        self._planner = planner
        self._synthesizer = synthesizer
        self._graph_agent = graph_agent
        self._sf_agent = sf_agent
        self._ss_agent = ss_agent
        self._step_timeout = step_timeout
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
            plan = await self._create_plan(query, session=session)
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
            coros = [self._execute_step(s, task, session=session) for s, task in step_inputs]
            wave_results = await asyncio.gather(*coros, return_exceptions=True)

            # AgentInvocation recording (with per-step timestamps) is done inside _execute_step.
            for i in range(len(step_inputs)):
                step, task_input = step_inputs[i]
                res = wave_results[i]

                if isinstance(res, BaseException):
                    err_msg = str(res) or repr(res)
                    log.error("Step %d (%s) failed: %s", step["id"], step["agent"], err_msg, exc_info=res)
                    yield {
                        "type": "error",
                        "message": f"Step {step['id']} ({step['agent']}) failed: {err_msg}",
                    }
                    continue

                results[step["id"]] = res

        # ── Phase 3: Synthesis ─────────────────────────────────────────────────
        yield {"type": "text", "chunk": "Synthesizing...\n"}
        try:
            answer = await self._synthesize(query, plan, results, session=session)
        except Exception as exc:
            log.error("Synthesis failed: %s", exc, exc_info=True)
            yield {"type": "error", "message": f"Synthesis failed: {exc}"}
            return

        log.info("[run_sse] yielding final answer, length=%d", len(answer))
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

    async def _create_plan(self, query: str, session=None) -> dict:
        """Call the planner agent, parse + validate the JSON plan. Retries once."""
        available = self._available_agents_description()
        prompt = f"Available agents: {available}\n\nUser query: {query}"

        last_exc: Exception = RuntimeError("No attempts made")
        kwargs = {} if session is None else {"session": session}
        for attempt in range(2):
            try:
                resp = await self._planner.run(prompt, **kwargs)
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
            agents.append(
                "graph (Microsoft 365: emails, calendar events, OneDrive files, "
                "personal Outlook contacts / address book — use for communication history, "
                "documents, and scheduling related to a person or company. "
                "Also use for internal company documents stored in OneDrive such as HR policies, "
                "expense rules, onboarding guides, contracts, and procedure documents — "
                "i.e. any question about internal rules, processes, or company documentation)"
            )
        if self._sf_agent is not None:
            agents.append(
                "salesforce (CRM: accounts, CRM contacts, leads, opportunities, cases — "
                "use for commercial relationship data, deal pipeline, and support history "
                "related to a company or contact)"
            )
        if self._ss_agent is not None:
            agents.append(
                "smartsales (locations, catalog items — use for physical presence, "
                "store or site information, and product catalog related to a company)"
            )
        hint = (
            " | For open-ended entity queries ('tell me about X', 'full picture of X', "
            "'what do we know about X') — use ALL agents."
        )
        return ", ".join(agents) + hint

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

    async def _execute_step(self, step: dict, task: str, session=None) -> str:
        """Execute a single plan step by calling the appropriate sub-agent."""
        agent = {
            "graph": self._graph_agent,
            "salesforce": self._sf_agent,
            "smartsales": self._ss_agent,
        }.get(step["agent"])
        if agent is None:
            raise ValueError(f"Agent '{step['agent']}' is not available in this session")
        kwargs = {} if session is None else {"session": session}

        started_at = datetime.now(timezone.utc).isoformat()
        success = True
        error: Optional[str] = None
        llm_turns = 0
        tool_calls: list[str] = []
        result_text = ""

        try:
            try:
                resp = await asyncio.wait_for(agent.run(task, **kwargs), timeout=self._step_timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Step timed out after {self._step_timeout}s")
            except asyncio.CancelledError:
                raise RuntimeError("Step was cancelled (connection dropped or outer request aborted)")
            except Exception as exc:
                if "content_filter" in str(exc) or "ContentFilter" in type(exc).__name__:
                    result_text = "[Resultaat geblokkeerd door Azure content filter — mogelijk prompt-injection tekst in brondata]"
                    return result_text
                raise

            self._accumulate_usage(resp)
            result_text = resp.text or ""

            # Extract LLM turn count and called tool names from the response messages.
            # Each assistant message = one LLM iteration; function_call content = one tool call.
            for msg in (resp.messages or []):
                if getattr(msg, "role", None) == "assistant":
                    llm_turns += 1
                for content in getattr(msg, "contents", []):
                    if getattr(content, "type", None) == "function_call":
                        tool_calls.append(getattr(content, "name", "unknown"))

            log.info(
                "[step %d / %s] result length=%d llm_turns=%d tool_calls=%s preview=%r",
                step["id"], step["agent"], len(result_text), llm_turns, tool_calls, result_text[:200],
            )
            return result_text

        except Exception as exc:
            success = False
            error = str(exc) or repr(exc)
            raise
        finally:
            ended_at = datetime.now(timezone.utc).isoformat()
            trace = get_trace()
            if trace is not None:
                trace.invoked_agents.append(AgentInvocation(
                    agent=step["agent"],
                    order=step["id"],
                    input=task,
                    started_at=started_at,
                    ended_at=ended_at,
                    success=success,
                    error=error,
                    llm_turns=llm_turns,
                    tool_calls=tool_calls,
                ))

    # ── Internal: Synthesis ────────────────────────────────────────────────────

    async def _synthesize(self, query: str, plan: dict, results: dict, session=None) -> str:
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
        log.info("[synthesize] context length=%d chars, step_ids_with_results=%s", len(context), list(results.keys()))
        kwargs = {} if session is None else {"session": session}
        resp = await self._synthesizer.run(context, **kwargs)
        try:
            log.info("[synthesize] resp.__dict__=%s", vars(resp))
        except Exception:
            log.info("[synthesize] resp attrs=%s", {a: getattr(resp, a, None) for a in dir(resp) if not a.startswith("_")})
        answer = resp.text or ""
        log.info("[synthesize] response length=%d preview=%r", len(answer), answer[:300])
        self._accumulate_usage(resp)
        return answer


# ── Factory ────────────────────────────────────────────────────────────────────

def create_planning_orchestrator(
    graph_agent: Optional[Agent] = None,
    sf_agent: Optional[Agent] = None,
    ss_agent: Optional[Agent] = None,
    step_timeout: float = 120.0,
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
        step_timeout=step_timeout,
    )
