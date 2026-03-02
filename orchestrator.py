import os
from agent import create_graph_agent
from bullshit_agent import create_bullshit_agent
from agent_framework import Agent, MCPStreamableHTTPTool, WorkflowAgent
from agent_framework.orchestrations import GroupChatBuilder
from agent_framework.openai import OpenAIChatClient

from dotenv import load_dotenv
load_dotenv()
deployment = os.environ["deployment"]


def setup(graph_mcp: MCPStreamableHTTPTool) -> WorkflowAgent:
    graph_agent = create_graph_agent(graph_mcp)
    bullshit = create_bullshit_agent()

    orchestrator = Agent(
        client=OpenAIChatClient(model_id=deployment),
        name="Orchestrator",
        description="Routes user queries to the right agent",
        instructions="""
            You are an orchestrator that routes user queries to the right agent.
            - For anything related to Microsoft 365 (emails, calendar, files, contacts, people): use GraphAgent.
            - For basic math operations: use BullshitAgent.
            If unsure, ask the user for clarification.
        """,
    )

    workflow = GroupChatBuilder(
        participants=[graph_agent, bullshit],
        orchestrator_agent=orchestrator,
        max_rounds=20,
    )

    return workflow.build().as_agent()
