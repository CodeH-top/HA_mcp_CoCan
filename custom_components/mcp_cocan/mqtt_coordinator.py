"""Experimental public-schema MQTT coordinator, isolated from MCP transport."""
from __future__ import annotations

import asyncio
import time

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import TransportType
from .coordinator import McpDeviceCoordinator
from .mqtt_client import CocanMqttClient, MqttCommandError
from .mqtt_wire import decode, integer, nested, packed, scalar, text, version

PROTOCOLS = ['None', 'QC2', 'QC3', 'QC3+', 'SFCP', 'AFC', 'FCP', 'SCP', 'VOOC1.0', 'VOOC4.0', 'SVOOC2.0', 'TFCP', 'UFCS', 'PE1', 'PE2', 'PD Fixed 5V', 'PD Fixed High Voltage', 'PD SPR AVS', 'PD PPS', 'PD EPR HV', 'PD AVS', 'PD MiPPS']


class CocanMqttCoordinator(McpDeviceCoordinator):
    def __init__(self, hass, entry, entities):
        super().__init__(hass, '', TransportType.STREAMABLE_HTTP, None, entry.title, entry.data.get('scan_interval', 15), entities, local_host=entry.data.get('local_host', ''))
        self.psn = entry.data['mqtt_psn']
        self.device_info = {'psn': self.psn}
        self.source = 'mqtt'
        self.connection_mode = 'mqtt'
        self.mqtt_ready = False
        self.client = CocanMqttClient(hass, self.psn, self._observe)
        self._stream = {}
        self._stream_time = 0
        self._stream_requested = 0
        self._cycle_lock = asyncio.Lock()
        self.available_tools = {'mqtt_public_schema'}

    def _observe(self, kind, command, fields):
        if kind == 'stream' and command == 0x80:
            self._stream = nested(fields, 112, required=True)
            self._stream_time = time.monotonic()
        # Boot telemetry contains an MCP authentication token: never store it.

    async def _async_update_data(self):
        try:
            async with self._cycle_lock, asyncio.timeout(45):
                await self.client.start()
                info = nested(await self.client.request(0x92), 1, required=True)
                if text(info, 1) != self.psn:
                    raise MqttCommandError('Device identity mismatch or incompatible schema')
                self.device_info = {
                    'psn': self.psn, 'model': text(info, 2),
                    'app_version': version(nested(info, 3, required=True)),
                    'bp_version': version(nested(info, 4, required=True)),
                    'fpga_version': version(nested(info, 5, required=True)),
                    'ssid': text(info, 10), 'wifi_mac': text(info, 8), 'bssid': text(info, 9),
                }
                power = scalar(await self.client.request(0x1B), 1)
                if power not in (0, 1):
                    raise MqttCommandError('Invalid power state')
                if not power:
                    self._charging_strategy = None
                    self._power_allocations = [None] * 5
                    self.mqtt_ready = True
                    return await self._finish_snapshot({'get_device_info': self.device_info, 'mqtt_power': {'state': 0}})
                status = scalar(await self.client.request(0x44), 1)
                self._charging_strategy = scalar(await self.client.request(0x48), 1)
                stats = await self.client.request(0x4A)
                raw_ports = stats.get(1, [])
                if len(raw_ports) != 5:
                    raise MqttCommandError('Expected five ports from public schema')
                ports = []
                for index, raw in enumerate(raw_ports):
                    item = decode(raw)
                    protocol = scalar(item, 1)
                    ports.append({'port': index + 1, 'iout_ma': scalar(item, 2), 'vout_mv': scalar(item, 3),
                                  'fc_protocol': PROTOCOLS[protocol] if protocol < len(PROTOCOLS) else 'Not Charging' if protocol == 255 else 'Unknown'})
                if time.monotonic() - self._stream_time < 30:
                    entries = self._stream.get(2, [])
                    if len(entries) == 5:
                        for index, raw in enumerate(entries):
                            detail = nested(decode(raw), 3, required=True)
                            ports[index].update({'connected': bool(scalar(detail, 11)), 'vin_mv': scalar(detail, 10),
                                                 'power_budget': scalar(detail, 13), 'session_id': scalar(detail, 2)})
                            # Raw session_charge units are not documented as mWh.
                self._power_allocations = [p.get('power_budget') for p in ports]
                # Subscription lease is periodically renewed; no global STOP on unload,
                # as another client may use the same device stream.
                if time.monotonic() - self._stream_requested > 30:
                    try:
                        await self.client.request(0x90)
                        self._stream_requested = time.monotonic()
                    except MqttCommandError:
                        pass  # Polling remains usable if stream is unsupported.
                self.mqtt_ready = True
                return await self._finish_snapshot({'get_device_info': self.device_info, 'get_port_details': {'ports': ports},
                        'get_charging_status': {'status_bitmask': status}, 'mqtt_power': {'state': power}})
        except (MqttCommandError, ValueError, TypeError, TimeoutError):
            self._charging_strategy = None
            self._power_allocations = [None] * 5
            self.mqtt_ready = False
            return await self._finish_snapshot({})

    async def _finish_snapshot(self, data):
        """MQTT mode never polls HTTP or falls back to cloud MCP."""
        self.source = 'mqtt'
        if not data or not self.mqtt_ready:
            raise UpdateFailed('MQTT telemetry is unavailable')
        values = [p.get('power_budget') for p in data.get('get_port_details', {}).get('ports', [])]
        self._power_allocations = [value if type(value) is int and 0 <= value <= (60 if i == 0 else 140) else None for i, value in enumerate(values)] if len(values) == 5 else [None] * 5
        self.last_sample = time.time()
        return data

    def _require_control(self):
        if not self.mqtt_ready:
            raise MqttCommandError('MQTT identity and connection have not been verified')

    async def async_call_tool(self, tool_name, arguments=None):
        args = arguments or {}
        if tool_name in ('turn_on_port', 'turn_off_port'):
            ports = args.get('ports', [])
            if not ports or any(type(p) is not int or p not in range(1, 6) for p in ports):
                raise ValueError('Invalid port list')
            command = 0x4C if tool_name == 'turn_on_port' else 0x4D
            payload = packed(1, [p - 1 for p in ports])
        elif tool_name == 'set_charging_strategy':
            strategy = args.get('strategy')
            if type(strategy) is not int or strategy not in (0, 1, 7, 8):
                raise ValueError('Unsupported charging strategy in public schema')
            command, payload = 0x43, integer(1, strategy)
        elif tool_name == 'mqtt_device_power':
            state = args.get('state')
            if type(state) is not int or state not in (0, 1):
                raise ValueError('Invalid power state')
            command, payload = 0x1A, integer(1, state)
        elif tool_name == 'mqtt_reboot':
            command, payload = 0x11, b''
        else:
            raise MqttCommandError('Control not implemented for this schema profile')
        async with self._cycle_lock:
            self._require_control()
            result = await self.client.request(command, payload)
        if tool_name != 'mqtt_reboot':
            await self.async_request_refresh()
        return result

    async def async_set_allocations(self, values):
        if len(values) != 5 or any(type(value) is not int or not 0 <= value <= (60 if index == 0 else 140) for index, value in enumerate(values)) or sum(values) > 160:
            raise ValueError('Invalid five-port allocation')
        async with self._command_lock, self._cycle_lock:
            self._require_control()
            result = await self.client.request(0x5C, packed(1, values))
            self._power_allocations = list(values)
        await self.async_request_refresh()
        return result

    async def async_set_power_allocation(self, port_index, value):
        # A single-port UI write cannot safely fill unknown other ports.
        async with self._command_lock:
            if port_index not in range(1, 6) or any(v is None for v in self._power_allocations):
                return False
            values = list(self._power_allocations)
            values[port_index - 1] = int(value)
            if any(v < 0 or v > (60 if i == 0 else 140) for i, v in enumerate(values)) or sum(values) > 160:
                return False
            async with self._cycle_lock:
                self._require_control()
                await self.client.request(0x5C, packed(1, values))
                self._power_allocations = values
        await self.async_request_refresh()
        return True
