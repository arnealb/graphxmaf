import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient


from dotenv import load_dotenv
load_dotenv()
deployment = os.environ["deployment"]


def create_bullshit_agent():
    return Agent(
        client=OpenAIChatClient(
            model_id=deployment,
        ),
        name="BullshitAgent",
        description="Agent with basic math skills",
        instructions="""
            You are a basic math assistent. You can perform simple arithmetic operations like addition
            subtraction, multiplication, and division. You can also calculate percentages and perform basic algebraic manipulations.
        """,
    )
