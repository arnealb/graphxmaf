import configparser
import os
import time

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from azure.core.credentials import AccessToken

from graph_tutorial import Graph

class StaticTokenCredential:
    def __init__(self, token: str):
        self.token = token

    def get_token(self, *_scopes, **_kwargs) -> AccessToken:
        return AccessToken(self.token, int(time.time()) + 3600)


def _make_graph_client(token: str, _azure_settings) -> Graph:
    return Graph(_azure_settings, credential=StaticTokenCredential(token))

async def search(
    self,
    query: str,
    entity_types: list[str],
    size: int = 25,
):
    body = {
        "requests": [
            {
                "entityTypes": entity_types,
                "query": {
                    "queryString": query
                },
                "from": 0,
                "size": size
            }
        ]
    }

    return await self._client.post(
        "/search/query",
        json=body
    )
