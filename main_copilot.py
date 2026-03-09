# main_copilot.py
import logging
logging.getLogger("microsoft_agents").addHandler(logging.StreamHandler())
logging.getLogger("microsoft_agents").setLevel(logging.INFO)

from copilot_agent import AGENT_APP
from start_server import start_server

start_server(agent_application=AGENT_APP, auth_configuration=None)