import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"


def create_salesforce_agent(salesforce_mcp):

    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="SalesforceAgent",
        description="Interacts with Salesforce CRM to access accounts, contacts, opportunities, and cases",
        instructions="""
            You are a helpful assistant with access to Salesforce CRM data.

            Available tools:
            - find_accounts: search for accounts by name or keyword
            - find_contacts: search for contacts by name or email
            - get_opportunities: list opportunities, optionally filtered by account or stage
            - get_cases: list cases, optionally filtered by account or status

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - NEVER call a tool speculatively.
            - If a tool returns sufficient data, stop and answer.

            OUTPUT
            - Always include the ID so the user can reference records in follow-up questions.
            - Present dates in a human-readable format.
        """,
        tools=[salesforce_mcp],
    )
