"""Experimental public-schema MQTT coordinator, isolated from MCP transport."""
from __future__ import annotations

import asyncio
import time

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import TransportType
from .coordinator import McpDeviceCoordinator
from .mqtt_client import CocanMqttClient, MqttCommandError
from .mqtt_data import signed, pd_status, display_config, display_snapshot
from .mqtt_wire import decode, integer, message, nested, packed, scalar, text, version

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
        self._device_stream = {}
        self._device_stream_time = 0
        self._display = {}
        self._display_time = 0
        self._pd_stream = {}
        self.optional_errors = []
        self._facts = {}
        self._budget = {}
        self._budget_time = 0
        self.available_tools = {'mqtt_public_schema'}

    def _observe(self, kind, command, fields):
        now = time.monotonic()
        if kind == 'stream' and command == 0x80:
            stream = nested(fields, 112, required=True)
            if len(stream.get(2, [])) != 5:
                raise ValueError('Expected five telemetry ports')
            self._stream, self._stream_time = stream, now
        elif kind == 'stream' and command == 0x81:
            stream = nested(fields, 113, required=True)
            self._device_stream, self._device_stream_time = stream, now
            if 9 in stream:
                self._display = display_config(nested(stream, 9, required=True))
                self._display_time = now
            elif 2 in stream:
                self._display = display_config(nested(stream, 2, required=True), canonical=True)
                self._display_time = now
        elif kind == 'stream' and command == 0x82:
            stream = nested(fields, 114, required=True)
            port = scalar(stream, 1)
            if port in range(5):
                self._pd_stream[port] = (nested(stream, 2, required=True), now)
        elif kind == 'telemetry' and command == 0x80:
            report = nested(fields, 80, required=True)
            config = nested(report, 2, required=True)
            self._device_stream = {7: [scalar(config, 4)]}
            self._device_stream_time = now
            if 5 in config:
                self._display = display_config(nested(config, 5, required=True))
                self._display_time = now
            elif 6 in config:
                self._display = display_config(nested(config, 6, required=True), canonical=True)
                self._display_time = now
        elif kind == 'telemetry' and command == 0x10:
            # Whitelist two public metadata fields; never retain the boot message
            # or its private mcp_auth_token field 22.
            boot = nested(fields, 10, required=True)
            self._facts = {'product_family': text(boot, 21), 'device_model': text(boot, 20)}
        elif kind == 'telemetry' and command == 0x31:
            budget = nested(fields, 31, required=True)
            self._budget = {'power_budget': scalar(budget, 1), 'remaining_power': scalar(budget, 2)}
            self._budget_time = now

    def _clear_streams(self):
        self._stream = {}
        self._device_stream = {}
        self._display = {}
        self._pd_stream = {}
        self._budget = {}
        self._budget_time = 0
        self._facts = {}
        self._stream_time = self._device_stream_time = self._display_time = 0

    async def _async_update_data(self):
        try:
            async with self._cycle_lock, asyncio.timeout(60):
                cycle_started = time.monotonic()
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
                    'rssi': signed(info, 11) if 11 in info else None, 'wifi_protocol': scalar(info, 12) if 12 in info else None, 'channel': scalar(info, 13) if 13 in info else None,
                    'zrlib_version': version(nested(info, 6)) if 6 in info else None,
                }
                power = scalar(await self.client.request(0x1B), 1)
                if power not in (0, 1):
                    raise MqttCommandError('Invalid power state')
                if not power:
                    self._clear_streams()
                    self._charging_strategy = None
                    self._power_allocations = [None] * 5
                    self.mqtt_ready = True
                    return await self._finish_snapshot({'get_device_info': self.device_info, 'mqtt_power': {'state': 0}})
                self.optional_errors = []
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
                                                 'power_budget': scalar(detail, 13), 'session_id': scalar(detail, 2),
                                                 'session_charge_raw': scalar(detail, 1)})
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
                pd_ports = []
                # Optional PD detail cannot take down base telemetry; bounded 2s/port.
                for index, port in enumerate(ports):
                    protocol = scalar(decode(raw_ports[index]), 1)
                    if not 15 <= protocol <= 21 or not status & (1 << index):
                        continue
                    cached, sampled = self._pd_stream.get(index, ({}, 0))
                    try:
                        if sampled >= cycle_started:
                            raw_pd = cached
                        else:
                            async with asyncio.timeout(2):
                                raw_pd = nested(await self.client.request(0x49, integer(1, index)), 1, required=True)
                        if raw_pd:
                            pd_ports.append(pd_status(raw_pd, index + 1))
                    except (MqttCommandError, ValueError, TypeError, TimeoutError):
                        self.optional_errors.append(f'pd_port_{index+1}')
                snapshot = {'get_device_info': self.device_info, 'get_port_details': {'ports': ports},
                            'get_port_pd_status': {'ports': pd_ports},
                            'get_charging_status': {'status_bitmask': status}, 'mqtt_power': {'state': power}}
                snapshot['get_machine_facts'] = {'product_family': self.device_info['model'], **self._facts}
                if time.monotonic() - self._budget_time < 30:
                    snapshot['mqtt_budget'] = dict(self._budget)
                if time.monotonic() - self._device_stream_time < 30:
                    mode = scalar(self._device_stream, 7)
                    if mode in (0, 1):
                        snapshot['get_temperature_mode'] = {'mode': mode}
                if time.monotonic() - self._display_time < 30:
                    snapshot['get_display_config'] = display_snapshot(self._display)
                else:
                    # These two read commands are consistent across both documented
                    # profiles; unlike 0x7D they cannot change the device configuration.
                    display = {}
                    for command, key, allowed in ((0x72, 'intensity', range(101)), (0x73, 'mode', (0, 1, 2))):
                        try:
                            async with asyncio.timeout(2):
                                value = scalar(await self.client.request(command), 1)
                            if value not in allowed:
                                raise ValueError('Invalid display value')
                            display[key] = value
                        except (MqttCommandError, ValueError, TypeError, TimeoutError):
                            self.optional_errors.append(key)
                    if 'intensity' in display:
                        snapshot['get_display_config'] = display_snapshot({
                            'rotation': None, 'idle_animation': None, 'mode': None, **display})
                    elif display.get('mode') in (1, 2):
                        snapshot['get_display_config'] = {'display_mode': '待机动画优先' if display['mode'] == 1 else '功率显示优先'}
                self.mqtt_ready = True
                return await self._finish_snapshot(snapshot)
        except (MqttCommandError, ValueError, TypeError, TimeoutError):
            self._clear_streams()
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
        elif tool_name == 'set_temperature_mode':
            mode = args.get('mode')
            if type(mode) is not int or mode not in (0, 1):
                raise ValueError('Invalid temperature mode')
            command, payload = 0x5B, integer(1, mode)
        elif tool_name == 'set_display_intensity':
            intensity = {'关': 0, '低': 25, '中': 50, '高': 100}.get(args.get('level'))
            if intensity is None:
                raise ValueError('Invalid brightness preset')
            command, payload = 0x70, integer(1, intensity)
        elif tool_name in ('set_status_display_mode', 'set_idle_display', 'set_hourly_chime'):
            async with self._command_lock, self._cycle_lock:
                self._require_control()
                await self._set_display(tool_name, args)
            await self.async_request_refresh()
            return {}
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
            if tool_name == 'set_display_intensity':
                self._display = {}
            elif tool_name == 'set_temperature_mode':
                self._device_stream = {}
                self._device_stream_time = 0
        if tool_name != 'mqtt_reboot':
            await self.async_request_refresh()
        return result

    async def _set_display(self, tool, args):
        # Only the official 0x7F schema. Never probe ambiguous 0x7D, which
        # means GET config in the new profile but SET setup in older firmware.
        if not self._display or time.monotonic() - self._display_time >= 30:
            raise MqttCommandError('Fresh display telemetry is required')
        config = dict(self._display)
        if 'hourly_chime' not in config or config.get('mode_param', 0):
            raise MqttCommandError('Cannot preserve all display settings for this profile')
        if tool == 'set_status_display_mode':
            mode = {'待机动画优先': 1, '功率显示优先': 2}.get(args.get('mode'))
            if mode is None:
                raise ValueError('Invalid display mode')
            config['mode'] = mode
        elif tool == 'set_idle_display':
            idle = {'流星': 1, '康威的生命游戏': 2, '时间': 4}.get(args.get('idle_display'))
            if idle is None:
                raise ValueError('Idle animation is not defined in this MQTT profile')
            config['idle_animation'] = idle
        else:
            if type(args.get('enabled')) is not bool:
                raise ValueError('Invalid chime state')
            config['hourly_chime'] = args['enabled']
        payload = message(1, b''.join(integer(field, value) for field, value in (
            (1, config['mode']), (2, config['intensity']), (3, config['flip']),
            (4, config['rotation']), (5, config['idle_animation']), (6, config['duration']),
            (7, int(config['hourly_chime'])))))
        await self.client.request(0x7F, payload)
        # ACK isn't readback. Wait for new device telemetry, never optimistic state.
        self._display = {}
        self._display_time = 0

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
