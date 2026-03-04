import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv
load_dotenv()
deployment = os.environ["deployment"]

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"

def create_graph_agent(graph_mcp):

    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="GraphAgent",
        description="Interacts with Microsoft Graph to access organizational data",
        instructions="""
            You are a helpful assistant with access to the user's Microsoft 365 data
            via the Microsoft Graph API.

            Available tools:
            - whoami: identify the authenticated user
            - findpeople: resolve a person's name to one or more email addresses
            - search_email: search emails using sender, subject, and/or date filters
            - read_email: read the full body of a specific email by its ID
            - list_files: list files in the user's OneDrive root
            - list_contacts: list contacts
            - list_calendar: list upcoming calendar events

            Core rules:

            PERSON RESOLUTION
            - Whenever the user mentions or implies a person (name, sender, colleague, etc.),
            you MUST call findpeople first to resolve the name to email address(es).
            - Never guess or fabricate an email address.
            - If multiple addresses are returned, use all of them when searching emails.

            EMAIL SEARCH
            - All email retrieval involving a sender or person MUST use search_email.
            - After resolving a person with findpeople, call search_email with:
            sender = resolved email address
            - If multiple emails exist for the person, search using each.
            - Do NOT use list_email for person-based queries.

            TOOL USAGE
            - Always use tools to retrieve real data. Never invent or assume data.
            - Choose the minimal tool sequence needed.
            - Prefer search_email over list_email when any filter (person, subject, time) is implied.

            OUTPUT
            - Present dates in a human-readable format.
            - When showing emails, include ID so the user can request read_email.
        """,
        tools=[graph_mcp],
    )
