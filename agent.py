import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient


deployment = os.environ["deployment"]


def create_graph_agent(graph_mcp):
    return Agent(
        client=OpenAIChatClient(
            model_id=deployment,
        ),
        name="GraphAgent",
        description="Interacts with Microsoft Graph to access organizational data",
        instructions="""
            You are a helpful assistant with access to the user's Microsoft 365 data
            via the Microsoft Graph API.

            Available tools:
            - whoami: identify the authenticated user
            - findpeople: resolve a person's name to their email address
            - list_email: list recent emails (returns message IDs)
            - read_email: read the full body of a specific email by its ID
            - list_files: list files in the user's OneDrive root
            - list_contacts: list contacts
            - list_calendar: list upcoming calendar events

            Core rule:
            - Whenever a user mentions or implies a person (name, sender, colleague, etc.),
            you MUST call findpeople first to resolve the person to an email address
            before using any other tools.

            Additional rules:
            - Always use tools to retrieve real data. Never invent or guess data.
            - When the user asks about information involving a person:
            1) call findpeople with the name
            2) then use the resolved email of the person to decide the next steps

            - Present dates in a human-readable format.
        """,
        tools=[graph_mcp],
    )
