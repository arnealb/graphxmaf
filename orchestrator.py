import os
from agent import create_graph_agent
from bullshit_agent import create_bullshit_agent
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import GroupChatBuilder

from dotenv import load_dotenv
load_dotenv()
deployment = os.environ["deployment"]


def setup(graph_mcp: MCPStreamableHTTPTool):
    graph_agent = create_graph_agent(graph_mcp)
    bullshit = create_bullshit_agent()

    orchestrator_agent = Agent(
        client=OpenAIChatClient(model_id=deployment),
        name="Orchestrator",
        description="Routes user queries to the right agent",
        instructions="""
            You are an orchestrator that routes user queries to the right agent.
            - For anything related to Microsoft 365 (emails, calendar, files, contacts, people): select GraphAgent.
            - For basic math operations: select BullshitAgent.
            When the task is complete, set terminate=true and provide a final_message summarizing the result.
            If unsure, ask the user for clarification by terminating with a clarifying question.
        """,
    )

    return GroupChatBuilder(
        participants=[graph_agent, bullshit],
        orchestrator_agent=orchestrator_agent,
    ).build()

