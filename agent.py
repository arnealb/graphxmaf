import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient

from dotenv import load_dotenv
load_dotenv()
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
            - list_inbox: list recent emails (returns message IDs)
            - read_email: read the full body of a specific email by its ID
            - list_files: list files in the user's OneDrive root
            - list_contacts: list contacts
            - list_calendar: list upcoming calendar events
            - unified_search: search across mail, calendar, files and contacts

            Rules:
            - Always use tools to retrieve real data. Never invent or guess data.
            - When the user asks about an email's content, first call list_inbox to
              get the message ID, then call read_email with that ID.
            - For broad queries spanning multiple data types, prefer unified_search.
            - Present dates in a human-readable format.
        """,
        tools=[graph_mcp],
    )
