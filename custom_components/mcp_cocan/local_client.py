"""Verified LAN reads and explicitly requested official Broker restoration."""
from __future__ import annotations

import ipaddress
import json
import math
import re
import socket
from urllib.parse import urlsplit

import aiohttp

MAX_LOCAL_BYTES = 262144


def validate_local_host(host: str) -> str:
    host = host.strip()
    if not host or len(host) > 253 or not re.fullmatch(r'[a-zA-Z0-9.-]+', host):
        raise ValueError('Enter an IPv4 address or local hostname, without a URL or port')
    return host


def normalise_metrics(data: dict) -> dict:
    """Convert only documented mV/mA/W fields. Missing data remains missing."""
    ports = data.get('ports')
    if not isinstance(ports, list) or not 1 <= len(ports) <= 5:
        raise ValueError('Invalid local port list')
    result = []
    seen = set()
    fields = {'voltage': 'vout_mv', 'current': 'iout_ma', 'vin_value': 'vin_mv', 'power_budget': 'power_budget'}
    for source in ports:
        if not isinstance(source, dict):
            raise ValueError('Invalid local port')
        index = source.get('id')
        if type(index) is not int or index not in range(5) or index in seen:
            raise ValueError('Invalid or duplicate local port ID')
        seen.add(index)
        port = {'port': index + 1}
        for key, target in fields.items():
            value = source.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('Invalid local numeric field')
                port[target] = value
        if isinstance(source.get('attached'), bool):
            port['connected'] = source['attached']
        # session_charge has undocumented units; do not relabel it as mWh.
        if isinstance(source.get('state'), str):
            port['state'] = source['state'][:64]
        if type(source.get('active')) is bool:
            port['active'] = source['active']
        for key in ('session_id', 'charging_duration_seconds'):
            if type(source.get(key)) is int and source[key] >= 0:
                port[key] = source[key]
        result.append(port)
    return {'ports': sorted(result, key=lambda item: item['port'])}


class LocalClient:
    def __init__(self, hass, host: str, expected_psn: str):
        self.hass = hass
        self.host = validate_local_host(host)
        self.expected_psn = str(expected_psn)

    async def read(self) -> dict:
        return await self._read(False)

    async def read_profile(self) -> dict:
        """Read identity and broker only for an explicit connection switch."""
        return await self._read(True)

    async def restore_official_broker(self) -> dict:
        """Clear the custom Broker and rebuild MQTT only on explicit restoration."""
        return await self._read(True, restore_official=True)

    async def _read(self, profile_only: bool, restore_official: bool = False) -> dict:
        # Resolve once per snapshot and pin both HTTP requests to this address.
        records = await self.hass.async_add_executor_job(socket.getaddrinfo, self.host, 80, socket.AF_INET, socket.SOCK_STREAM)
        addresses = [item[4][0] for item in records]
        if not addresses or any(not ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback or ipaddress.ip_address(ip).is_link_local for ip in addresses):
            raise ValueError('Local telemetry must resolve to a private LAN address')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4, connect=2)) as session:
            async def fetch(path, **kwargs):
                async with session.request(kwargs.pop('method', 'GET'), f'http://{addresses[0]}{path}', allow_redirects=False, **kwargs) as response:
                    if response.status != 200:
                        raise ValueError('Local telemetry HTTP error')
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(8192):
                        raw.extend(chunk)
                        if len(raw) > MAX_LOCAL_BYTES:
                            raise ValueError('Local response exceeds limit')
                    return raw.decode('utf-8')
            html = await fetch('/')
            marker = re.search(r'window\.__INFOZ\s*=\s*', html)
            if marker is None:
                raise ValueError('Cannot verify local device identity')
            info, _ = json.JSONDecoder().raw_decode(html[marker.end():].lstrip())
            psn = info.get('psn') if isinstance(info, dict) else None
            if str(psn) != self.expected_psn:
                raise ValueError('Local device identity mismatch')
            if profile_only:
                config_marker = re.search(r'window\.__CONFIG\s*=\s*', html)
                if config_marker is None:
                    raise ValueError('Device broker config is unavailable')
                config, _ = json.JSONDecoder().raw_decode(html[config_marker.end():].lstrip())
                if not isinstance(config, dict) or not isinstance(config.get('broker'), str):
                    raise ValueError('Device broker config is invalid')
                if restore_official:
                    from .broker import OFFICIAL_BROKER_URL
                    official = urlsplit(OFFICIAL_BROKER_URL)
                    active = urlsplit(config['broker'])
                    if (active.scheme, active.hostname, active.port) != (official.scheme, official.hostname, official.port):
                        endpoints_marker = re.search(r'window\.__ENDPOINTS\s*=\s*', html)
                        if endpoints_marker is None:
                            raise ValueError('Device does not advertise Broker restoration')
                        endpoints, _ = json.JSONDecoder().raw_decode(html[endpoints_marker.end():].lstrip())
                        if not isinstance(endpoints, list) or not all(path in endpoints for path in ('/setbrokerz', '/destroymqttz', '/startmqttz')):
                            raise ValueError('Device does not support Broker restoration')
                        # Empty body removes only the custom override. The protected
                        # factory Broker and its device certificates stay untouched.
                        await fetch('/setbrokerz', method='POST', data='', headers={'Content-Type': 'text/plain'})
                        try:
                            await fetch('/destroymqttz')
                        finally:
                            await fetch('/startmqttz')
                        profile = await self.read_profile()
                        restored = urlsplit(profile['broker'])
                        if (restored.scheme, restored.hostname, restored.port) != (official.scheme, official.hostname, official.port):
                            raise ValueError('Device did not restore the official Broker')
                        return profile
                return {'psn': str(psn), 'broker': config['broker']}
            return normalise_metrics(json.loads(await fetch('/metrics.json')))
