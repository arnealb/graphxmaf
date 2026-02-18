import sys
import os
import logging
import configparser
from agent_framework import MCPStdioTool
from agent_framework.devui import serve
from agent import create_graph_agent
from graph_tutorial import Graph


logging.getLogger('asyncio').setLevel(logging.CRITICAL)


def authenticate() -> str:
    config = configparser.ConfigParser()
    config.read(["config.cfg"])
    azure_settings = config["azure"]

    graph = Graph(azure_settings)
    print("Authenticating... (follow the instructions below)")
    token = graph.get_user_token()
    print("Authenticated.")
    return token


def main():
    print("Starting application...")

    token = authenticate()

    graph_mcp = MCPStdioTool(
        name="graph",
        command=sys.executable,
        args=["mcp_api_tool.py"],
        env={
            "GRAPH_ACCESS_TOKEN": token
        }
    )

    print(os.environ["GRAPH_ACCESS_TOKEN"])

    agent = create_graph_agent(graph_mcp=graph_mcp)

    serve(entities=[agent], port=8080, auto_open=True)


if __name__ == "__main__":
    main()
