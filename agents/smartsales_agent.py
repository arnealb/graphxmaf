import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"


def create_smartsales_agent(smartsales_mcp):
    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="SmartSalesAgent",
        description="Interacts with SmartSales to access location data",
        instructions="""
            You are a helpful assistant with access to SmartSales location data.

            Available tools:
            - get_location: retrieve a single location by its uid.
            - list_locations: query locations using SmartSales-native params:
                q  — JSON filter string, e.g. '{"city":"eq:Brussels"}' or
                     '{"country":"eq:Belgium","name":"contains:acme"}'
                s  — sort, e.g. "name:asc"
                p  — projection: "minimal", "simple", "fullWithColor", "full"
                d  — comma-separated field list
                nextPageToken — token from previous response to fetch the next page
                Returns: { locations: [...], nextPageToken: "...", resultSizeEstimate: N }

            STRICT TOOL SELECTION RULES:
            - ONLY call tools directly required by the user's request.
            - Use get_location when the user provides a specific uid.
            - Use list_locations for all search/list requests.
            - Build the q filter as a JSON string with operator-prefixed values,
              e.g. {"city":"eq:Knokke"} — never omit the operator.
            - Call list_locations EXACTLY ONCE per user request. Do NOT call it
              again using nextPageToken unless the user explicitly asks for the next page.
            - The response includes resultSizeEstimate — use it to know the total count,
              but do NOT keep fetching pages to collect all results.
            - If a tool returns sufficient data, stop and answer immediately.

            OUTPUT
            - Return the exact JSON object or array that the tool returned. No prose, no explanation.
            - If multiple tools were called, return a JSON array where each element is
              {"tool": "<tool_name>", "result": <tool_result>}.
            - If only one tool was called, return its result directly.
        """,
        tools=[smartsales_mcp],
    )
