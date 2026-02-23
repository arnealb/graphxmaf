import time

from azure.core.credentials import AccessToken

from graph_tutorial import Graph


class StaticTokenCredential:
    def __init__(self, token: str):
        self.token = token

    def get_token(self, *_scopes, **_kwargs) -> AccessToken:
        return AccessToken(self.token, int(time.time()) + 3600)


def _make_graph_client(token: str, _azure_settings) -> Graph:
    return Graph(_azure_settings, credential=StaticTokenCredential(token))
