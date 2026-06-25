"""MCP (Model Context Protocol) client for connecting external tool servers."""

import asyncio
import os
from typing import Any
from langchain_core.tools import tool


class MCPTool:
    """A tool discovered from an MCP server."""
    def __init__(self, name: str, description: str, input_schema: dict, server_name: str):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name


class MCPServer:
    """A connected MCP server providing tools."""
    def __init__(self, name: str, command: str, args: list[str] = None,
                 env: dict = None, tools: list[MCPTool] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.tools = tools or []
        self._process = None
        self._session = None

    async def connect(self):
        """Start the MCP server process and establish a session."""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client, StdioServerParameters

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**os.environ, **self.env} if self.env else None,
        )

        self._read, self._write = await stdio_client(params).__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

        result = await self._session.list_tools()
        self.tools = [
            MCPTool(
                name=t.name,
                description=t.description or "",
                input_schema=t.inputSchema if hasattr(t, 'inputSchema') else {},
                server_name=self.name,
            )
            for t in result.tools
        ]
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Invoke a tool on this server."""
        if not self._session:
            raise RuntimeError(f"Server {self.name} not connected")
        result = await self._session.call_tool(tool_name, arguments)
        # result.content is a list of content blocks
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            else:
                parts.append(str(block))
        return "\n".join(parts)

    async def disconnect(self):
        """Close the MCP session (best-effort)."""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
                self._session = None
        except Exception:
            pass
        try:
            if hasattr(self, '_read') and self._read:
                await self._read.aclose()
        except Exception:
            pass
        try:
            if hasattr(self, '_write') and self._write:
                await self._write.aclose()
        except Exception:
            pass


class MCPClient:
    """Manages multiple MCP server connections and their tools."""

    def __init__(self):
        self._servers: dict[str, MCPServer] = {}

    async def connect_server(self, name: str, command: str,
                              args: list[str] = None, env: dict = None) -> list[MCPTool]:
        """Connect to a new MCP server and discover its tools."""
        if name in self._servers:
            raise ValueError(f"Server {name} already connected")
        server = MCPServer(name, command, args, env)
        tools = await server.connect()
        self._servers[name] = server
        return tools

    async def disconnect_server(self, name: str):
        """Disconnect an MCP server."""
        server = self._servers.pop(name, None)
        if server:
            await server.disconnect()

    async def disconnect_all(self):
        for name in list(self._servers.keys()):
            await self.disconnect_server(name)

    def list_servers(self) -> list[dict]:
        """List connected servers with their tools."""
        return [
            {"name": s.name, "command": s.command, "tools": len(s.tools)}
            for s in self._servers.values()
        ]

    def list_tools(self) -> list[MCPTool]:
        """List all tools from all connected servers."""
        tools = []
        for s in self._servers.values():
            tools.extend(s.tools)
        return tools

    def get_server(self, name: str) -> MCPServer | None:
        return self._servers.get(name)

    def build_langchain_tools(self):
        """Convert all discovered MCP tools to LangChain tools."""
        lc_tools = []
        for mcp_tool in self.list_tools():
            lc_tools.append(_mcp_to_langchain_tool(self, mcp_tool))
        return lc_tools


def _mcp_to_langchain_tool(client: MCPClient, mcp_tool: MCPTool):
    """Convert a single MCP tool to a LangChain tool."""
    server_name = mcp_tool.server_name
    tool_name = mcp_tool.name

    @tool(mcp_tool.name, description=f"[MCP:{server_name}] {mcp_tool.description}")
    def mcp_wrapper(**kwargs) -> str:
        """MCP tool wrapper."""
        server = client.get_server(server_name)
        if not server:
            return f"Error: MCP server {server_name} not connected"
        # Run async call in a sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        lambda: asyncio.run(server.call_tool(tool_name, kwargs))
                    ).result()
            return asyncio.run(server.call_tool(tool_name, kwargs))
        except RuntimeError:
            return asyncio.run(server.call_tool(tool_name, kwargs))

    # Rename the function for better display
    mcp_wrapper.name = f"mcp_{server_name}_{tool_name}"
    return mcp_wrapper
