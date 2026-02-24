import time

from azure.core.credentials import AccessToken

from graph.repository import GraphRepository



class StaticTokenCredential:
    def __init__(self, token: str):
        self.token = token

    def get_token(self, *_scopes, **_kwargs) -> AccessToken:
        return AccessToken(self.token, int(time.time()) + 3600)


def _make_graph_client(token: str, _azure_settings) -> GraphRepository:
    return GraphRepository(_azure_settings, credential=StaticTokenCredential(token))
