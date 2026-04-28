import sys, os
sys.path.insert(0, os.path.abspath('..'))  # graphxmaf root toevoegen aan path

import configparser
from graph.repository import GraphRepository
import asyncio

config = configparser.ConfigParser()
config.read('../config.cfg')  # pad vanuit md/ map
graph_repo = GraphRepository(config['azure'])

# Device code login — browser opent automatisch
me = asyncio.run(graph_repo.get_user())
MY_EMAIL = me.mail or me.user_principal_name
GRAPH_TOKEN = graph_repo.get_user_token()
print(f"graph token: {GRAPH_TOKEN}")
print(f'✓ Graph auth  user={MY_EMAIL}')