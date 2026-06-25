"""MCP (Model Context Protocol) client for connecting external tool servers."""

import asyncio
import os
import subprocess
from typing import Any


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

        # stdio_client returns (read, write) streams
        self._read, self._write = await stdio_client(params).__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

        # Discover tools
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
        return result.content

    async def disconnect(self):
        """Close the MCP session."""
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._read and self._write:
            # stdio transport cleanup
            try:
                await self._read.aclose()
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
