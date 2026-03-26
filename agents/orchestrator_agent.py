import os
from typing import Annotated

from agent_framework import Agent, FunctionTool
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv

load_dotenv()
deployment = os.environ["deployment"]
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
api_version = "2024-12-01-preview"


def create_orchestrator_agent(
    smartsales_agent: Agent,
    graph_agent: Agent | None = None,
    salesforce_agent: Agent | None = None,
) -> Agent:

    tools = []

    if graph_agent is not None:
        async def ask_graph_agent(query: Annotated[str, "The full question to send to the Microsoft Graph agent"]) -> str:
            response = await graph_agent.run(query)
            print(f"GraphAgent response: {response}")
            return response.text or "(no response from GraphAgent)"

        tools.append(FunctionTool(
            name="ask_graph_agent",
            description=(
                "Route a question to the Microsoft Graph agent. "
                "Use this for anything related to emails, OneDrive files, calendar events, "
                "contacts, or identifying the current Microsoft 365 user."
            ),
            func=ask_graph_agent,
            approval_mode="never_require",
        ))

    if salesforce_agent is not None:
        async def ask_salesforce_agent(query: Annotated[str, "The full question to send to the Salesforce CRM agent"]) -> str:
            response = await salesforce_agent.run(query)
            print(f"salesforce response: {response}")
            return response.text or "(no response from SalesforceAgent)"

        tools.append(FunctionTool(
            name="ask_salesforce_agent",
            description=(
                "Route a question to the Salesforce CRM agent. "
                "Use this for anything related to CRM accounts, contacts, leads, "
                "sales opportunities, or support cases."
            ),
            func=ask_salesforce_agent,
            approval_mode="never_require",
        ))

    async def ask_smartsales_agent(query: Annotated[str, "The full question to send to the SmartSales agent"]) -> str:
        response = await smartsales_agent.run(query)
        print(f"SmartSalesAgent response: {response}")
        return response.text or "(no response from SmartSalesAgent)"

    tools.append(FunctionTool(
        name="ask_smartsales_agent",
        description=(
            "Route a question to the SmartSales agent. "
            "Use this for anything related to SmartSales locations, catalog items, "
            "or orders: searching, listing, and retrieving by name, city, country, or uid."
        ),
        func=ask_smartsales_agent,
        approval_mode="never_require",
    ))

    active_systems = []
    if graph_agent is not None:
        active_systems.append("1. ask_graph_agent  — handles everything Microsoft 365:\n               emails, OneDrive files, calendar events, contacts, user identity.")
    if salesforce_agent is not None:
        active_systems.append("2. ask_salesforce_agent — handles everything Salesforce CRM:\n               accounts, contacts, leads, opportunities, support cases.")
    active_systems.append("3. ask_smartsales_agent — handles SmartSales data:\n               locations, catalog items, and orders.")

    return Agent(
        client=AzureOpenAIChatClient(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        ),
        name="OrchestratorAgent",
        description="Central orchestrator that routes queries to the available sub-agents and combines their results",
        instructions=f"""
            You are a central orchestrator that coordinates specialized agents:

            {chr(10).join(active_systems)}

            ROUTING RULES
            - Microsoft 365 / Office data → ask_graph_agent (if available)
            - Salesforce / CRM data       → ask_salesforce_agent (if available)
            - SmartSales data             → ask_smartsales_agent
            - Query spans multiple systems → call relevant tools, then combine

            STRICT TOOL SELECTION RULES
            - Only call a tool when the user's request explicitly requires it.
            - Pass the user's original question (rephrased if needed for clarity) to the sub-agent.
            - Never guess or fabricate data — only report what the sub-agents return.
            - If a single tool call returns sufficient information, do NOT call the others.

            SUB-AGENT RESPONSES
            - Sub-agents return the raw JSON objects from their tool calls, not prose.
            - Parse and read the structured fields (id, name, email, etc.) to answer the user.
            - For cross-system queries, extract the relevant value from one sub-agent's JSON
              result and include it in the next sub-agent query.

            COMBINING RESULTS
            - When multiple agents are called, synthesize their results into one coherent answer.
            - Clearly indicate which system each piece of information comes from
              (e.g. "From Microsoft 365: …" / "From Salesforce: …" / "From SmartSales: …").
            - Present a unified, structured summary — do not just concatenate raw outputs.

            OUTPUT
            - Be concise and factual.
            - Use bullet points or sections when presenting data from multiple sources.
            - Present dates in a human-readable format.
        """,
        tools=tools,
    )
