import asyncio
import sys
from contextlib import redirect_stdout

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

from .agent import PerceptionAgent
from .config import Settings


def create_server(settings: Settings) -> FastMCP:
    mcp = FastMCP("Data Perception")
    agent = PerceptionAgent(settings)
    gate = asyncio.Lock()

    @mcp.tool()
    async def build_data_context(task: str, data_path: str) -> CallToolResult:
        """Profile an authorized local dataset and return Data Context as text.

        Optional local model interpretation depends on server configuration.
        Statistics describe the first configured rows, not necessarily the full dataset.
        """
        # Serialize calls, including model loading. Never let library prints corrupt STDIO.
        async with gate:
            with redirect_stdout(sys.stderr):
                try:
                    text = await asyncio.to_thread(agent.build_context, task, data_path)
                    return CallToolResult(
                        content=[TextContent(type="text", text=text)], isError=False
                    )
                except Exception as error:  # noqa: BLE001 - convert reader/model failures at MCP boundary
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"{type(error).__name__}: {error}")],
                        isError=True,
                    )

    return mcp


def run(settings: Settings):
    create_server(settings).run(transport="stdio")
