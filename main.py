import sys
import asyncio
import logging
from agent_framework import MCPStdioTool
from agent_framework.devui import serve
from agent import create_graph_agent






logging.getLogger('asyncio').setLevel(logging.CRITICAL)


def main():
    graph_mcp = MCPStdioTool(
        name="graph",
        command=sys.executable,
        args=["mcp_api_tool.py"]
    )

    agent = create_graph_agent(graph_mcp=graph_mcp)

    print("starting devui")
    serve(entities=[agent], port=8080, auto_open=True)

if __name__ == "__main__":
    main()