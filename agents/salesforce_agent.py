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
            - find_leads: search for leads by name, email, or company
            - get_opportunities: list opportunities, optionally filtered by account ID or stage
            - get_cases: list cases, optionally filtered by account ID or status

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - NEVER call a tool speculatively.
            - If a tool returns sufficient data, stop and answer.
            - Use find_accounts when the user asks about companies or accounts.
            - Use find_contacts when the user asks about people already in CRM.
            - Use find_leads when the user asks about prospective customers or leads.
            - Use get_opportunities when the user asks about deals or sales pipeline.
            - Use get_cases when the user asks about support tickets or cases.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
        """,
        tools=[salesforce_mcp],
    )
