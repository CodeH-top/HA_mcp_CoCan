"""Bounded Streamable HTTP MCP client; never log device credentials."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from .const import TransportType

MAX_JSON_SIZE = 1_048_576


class McpError(Exception):
    """Protocol, transport or device error with no private response content."""


class McpClient:
    def __init__(self, url: str, transport: TransportType, token: str | None = None) -> None:
        parts = urlsplit(url)
        # Official service exposes the same device token through both transports.
        # Normalize its legacy link; do not claim generic legacy SSE support.
        if parts.hostname == 'mcp.thecandysign.com' and parts.path.endswith('/sse'):
            url = urlunsplit(parts._replace(path=parts.path[:-4] + '/mcp'))
        self._url = url
        self._token = token
        self._session = None
        self._session_id = None
        self._msg_id = 0

    async def __aenter__(self):
        headers = {'Accept': 'application/json, text/event-stream'}
        if self._token:
            headers['Authorization'] = f'Bearer {self._token}'
        self._session = aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=25, connect=5))
        try:
            await self._post_json(self._make_payload('initialize', {
                'protocolVersion': '2024-11-05', 'capabilities': {},
                'clientInfo': {'name': 'ha-cocan', 'version': '0.4.0'},
            }))
            await self._post_json({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        except BaseException:
            await self._session.close()
            raise
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
            self._session = None

    def _make_payload(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        return {'jsonrpc': '2.0', 'id': self._msg_id, 'method': method, 'params': params or {}}

    async def _post_json(self, payload: dict) -> Any:
        if self._session is None:
            raise McpError('MCP session is closed')
        headers = {'Mcp-Session-Id': self._session_id} if self._session_id else {}
        try:
            async with self._session.post(self._url, json=payload, headers=headers, allow_redirects=False) as response:
                if response.status not in (200, 202, 204):
                    raise McpError(f'MCP HTTP {response.status}')
                self._session_id = response.headers.get('Mcp-Session-Id', self._session_id)
                if 'id' not in payload:
                    return {}
                raw = bytearray()
                # iter_chunked enforces the limit before a large body is allocated.
                async for chunk in response.content.iter_chunked(8192):
                    raw.extend(chunk)
                    if len(raw) > MAX_JSON_SIZE:
                        raise McpError('MCP response exceeds size limit')
                    if 'text/event-stream' in response.headers.get('Content-Type', ''):
                        for event in bytes(raw).replace(b'\r\n', b'\n').split(b'\n\n')[:-1]:
                            lines = [line[5:].lstrip() for line in event.split(b'\n') if line.startswith(b'data:')]
                            if lines:
                                result = json.loads(b'\n'.join(lines))
                                if isinstance(result, dict) and result.get('id') == payload['id']:
                                    return self._result(result, payload['id'])
                result = json.loads(raw)
                return self._result(result, payload['id'])
        except (aiohttp.ClientError, TimeoutError, ValueError, RecursionError) as exc:
            raise McpError(f'MCP transport failed ({type(exc).__name__})') from None

    @staticmethod
    def _result(data: Any, request_id: int) -> Any:
        if not isinstance(data, dict) or data.get('id') != request_id:
            raise McpError('MCP response ID mismatch')
        if 'error' in data:
            raise McpError('MCP JSON-RPC error')
        return data.get('result', {})

    async def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        cursor = None
        for _ in range(20):
            result = await self._post_json(self._make_payload('tools/list', {'cursor': cursor} if cursor else {}))
            tools.extend(result.get('tools', []))
            cursor = result.get('nextCursor')
            if not cursor:
                return tools
        raise McpError('MCP tool pagination exceeds limit')

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = await self._post_json(self._make_payload('tools/call', {'name': tool_name, 'arguments': arguments or {}}))
        if not isinstance(result, dict):
            raise McpError('Invalid MCP tool result')
        if result.get('isError'):
            raise McpError('Device rejected MCP command')
        if 'structuredContent' in result:
            value = result['structuredContent']
        else:
            value = result
            for item in result.get('content', []):
                if item.get('type') == 'text':
                    try:
                        value = json.loads(item.get('text', ''))
                    except (ValueError, RecursionError):
                        raise McpError('Unstructured MCP tool response') from None
                    break
        if isinstance(value, dict) and (value.get('success') is False or value.get('error')):
            raise McpError('Device rejected MCP command')
        return value


async def call_mcp_tool(url, transport, tool_name, arguments=None, token=None):
    async with McpClient(url, transport, token) as client:
        return await client.call_tool(tool_name, arguments)


def parse_tool_result(result):
    return result if result is not None else {}
