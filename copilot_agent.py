import sys, traceback, os
from dotenv import load_dotenv
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import AgentApplication, TurnState, TurnContext, MemoryStorage, Authorization
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env
from agent_framework_agent import GraphAgentWrapper

load_dotenv()

agents_sdk_config = load_configuration_from_env(os.environ)
STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config
)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    await context.send_activity("Hi! Ik ben je Graph Agent. Wat wil je weten?")
    return True


@AGENT_APP.activity("message", auth_handlers=["GRAPH"])
async def on_message(context: TurnContext, state: TurnState):
    user_text = (context.activity.text or "").strip()
    print(f"[on_message] Ontvangen: {user_text}")
    if not user_text:
        return

    try:
        token_response = await AGENT_APP.auth.get_token(context, "GRAPH")
        if not token_response or not token_response.token:
            print("[on_message] Geen token beschikbaar")
            await context.send_activity("Kon geen token ophalen. Probeer opnieuw in te loggen.")
            return

        print(f"[on_message] Token ontvangen via OBO")
        agent = GraphAgentWrapper(token=token_response.token)
        answer = await agent.invoke(user_text)
        await context.send_activity(answer)

    except Exception as e:
        print(f"[on_message] FOUT: {e}")
        traceback.print_exc()
        await context.send_activity(f"Fout: {str(e)}")


@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception):
    traceback.print_exc()
    await context.send_activity("Bot fout opgetreden.")