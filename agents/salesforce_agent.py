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

            LINKED QUERIES:
            - When the user asks for opportunities or cases for a named account:
              1. Call find_accounts to get the account ID.
              2. Pass that ID to get_opportunities or get_cases.
            - NEVER pass account_id=null when the user specifies an account name.

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - NEVER call a tool speculatively.
            - If a tool returns sufficient data, stop and answer.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
        """,
        tools=[salesforce_mcp],
    )
