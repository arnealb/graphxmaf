import os
from agent_framework import Agent, MCPStdioTool
from agent_framework.openai import OpenAIChatClient
from openai import AzureOpenAI

endpoint = os.environ["endpoint"]
model_name = os.environ["model_name"]
deployment = os.environ["deployement"]
subscription_key = os.environ["subscription_key"]
api_version = os.environ["api_version"]


from agent_framework.openai import OpenAIChatClient

def create_graph_agent(graph_mcp):
    return Agent(
        client=OpenAIChatClient(
            model_id="gpt-4o-mini",
        ),
        name="GraphAgent",
        description="Interacts with Microsoft Graph",
        instructions="""
            Use tools when Microsoft Graph data is required.
            Never invent data.
        """,
        tools=[graph_mcp],  
    )



