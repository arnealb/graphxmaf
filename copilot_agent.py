# copilot_agent.py
import sys, traceback, os
from dotenv import load_dotenv
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication, TurnState, TurnContext, MemoryStorage
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from agent_framework_agent import GraphAgentWrapper
from microsoft_agents.activity import load_configuration_from_env
import os

load_dotenv()


agents_sdk_config = load_configuration_from_env(os.environ)

STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    **agents_sdk_config,
)

graph_agent = GraphAgentWrapper()

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    await context.send_activity("Hi! Ik ben je Graph Agent. Wat wil je weten?")
    return True

@AGENT_APP.activity("message")
async def on_message(context: TurnContext, _state: TurnState):
    user_text = (context.activity.text or "").strip()
    print(f"[on_message] Ontvangen: {user_text}")  # ADD
    if not user_text:
        return
    try:
        print("[on_message] Agent aanroepen...")  # ADD
        answer = await graph_agent.invoke(user_text)
        print(f"[on_message] Antwoord: {answer[:100]}")  # ADD
        await context.send_activity(answer)
    except Exception as e:
        print(f"[on_message] FOUT: {e}")  # ADD
        traceback.print_exc()
        await context.send_activity(f"Fout: {str(e)}")

@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception):
    traceback.print_exc()
    await context.send_activity("Bot fout opgetreden.")