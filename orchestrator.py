import os
from agent import create_graph_agent
from bullshit_agent import create_bullshit_agent
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient

from dotenv import load_dotenv
load_dotenv()
deployment = os.environ["deployment"]


def setup(graph_mcp: MCPStreamableHTTPTool) -> Agent:
    graph_agent = create_graph_agent(graph_mcp)
    bullshit = create_bullshit_agent()

    return Agent(
        client=OpenAIChatClient(model_id=deployment),
        name="Orchestrator",
        description="Routes user queries to the right agent",
        instructions="""
            You are an orchestrator that routes user queries to the right agent tool.
            - For anything related to Microsoft 365 (emails, calendar, files, contacts, people): use graph_agent.
            - For basic math operations: use bullshit_agent.
            If unsure, ask the user for clarification.
        """,
        tools=[
            graph_agent.as_tool(),
            bullshit.as_tool(),
        ],
    )
