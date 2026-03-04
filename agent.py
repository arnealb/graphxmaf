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
            - list_email: list the 25 most recent inbox emails
            - search_email: search emails by sender, subject, or date range
            - read_email: read the full body of a specific email by its ID
            - search_files: search for files and folders in OneDrive
            - read_file: read the text content of a OneDrive file by its ID
            - list_contacts: list contacts
            - list_calendar: list upcoming and recent calendar events
            - search_calendar: search calendar events by subject, location, attendee, or date range

            STRICT TOOL SELECTION RULES — follow these exactly:
            - ONLY call tools that are directly required by the user's current request.
            - NEVER call a tool speculatively or to gather background context.
            - NEVER call calendar tools (list_calendar, search_calendar) unless the user explicitly asks about meetings, events, or their schedule.
            - NEVER call email tools (list_email, search_email, read_email) unless the user explicitly asks about emails or messages.
            - NEVER call file tools (search_files, read_file) unless the user explicitly asks about files or documents.
            - NEVER call list_contacts unless the user explicitly asks about contacts.
            - NEVER call the same tool twice in a single turn unless each call uses different parameters required by the request.
            - If a tool returns sufficient data, stop and answer — do NOT call more tools.

            PERSON RESOLUTION
            - Whenever the user mentions a person (name, sender, colleague), call findpeople first.
            - Never guess or fabricate an email address.

            EMAIL SEARCH
            - When searching by person, resolve with findpeople first, then pass the resolved email to search_email.
            - Prefer search_email over list_email when any filter is implied.

            FILE WORKFLOW
            - To find a file: call search_files with a relevant query.
            - To read a file's contents: call read_file with the file ID returned by search_files.

            OUTPUT
            - Present dates in a human-readable format.
            - When showing emails or files, include the ID so the user can request read_email or read_file.
        """,
        tools=[graph_mcp],
    )
