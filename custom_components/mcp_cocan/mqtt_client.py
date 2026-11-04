"""HA-managed MQTT connection with bounded, correlated binary requests."""
from __future__ import annotations

import asyncio
import secrets

from homeassistant.components import mqtt
from homeassistant.core import callback

from .mqtt_wire import COMMANDS, decode, integer, message, nested, scalar


class MqttCommandError(Exception):
    """No credentials or private response bodies in error text."""


class CocanMqttClient:
    def __init__(self, hass, psn, observer=None):
        if not psn.isdigit() or not 6 <= len(psn) <= 32:
            raise ValueError('Invalid device serial number')
        self.hass = hass
        self.psn = psn
        self.observer = observer
        self._pending = {}
        self._subscriptions = []
        self._next_id = secrets.randbelow(2**31) + 1
        self._lock = asyncio.Lock()

    async def start(self):
        if self._subscriptions:
            return
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            raise MqttCommandError('Configure the HA MQTT integration first')
        try:
            for suffix in ('enduser/response/+', 'telemetry/+'):
                unsubscribe = await mqtt.async_subscribe(self.hass, f'device/{self.psn}/{suffix}', self._receive, qos=1, encoding=None)
                self._subscriptions.append(unsubscribe)
        except BaseException:
            self.close()
            raise

    @callback
    def _receive(self, msg):
        if msg.retain:
            return
        prefix = f'device/{self.psn}/'
        if not msg.topic.startswith(prefix):
            return
        suffix = msg.topic[len(prefix):].split('/')
        try:
            if suffix[-1] != str(int(suffix[-1])):
                return
            command = int(suffix[-1])
            fields = decode(msg.payload)
            if len(suffix) == 3 and suffix[:2] == ['enduser', 'response']:
                key = (command, scalar(fields, 1))
                future = self._pending.get(key)
                if future is not None and not future.done():
                    status = scalar(fields, 2)
                    if status:
                        future.set_exception(MqttCommandError(f'Device rejected command (status {status})'))
                    else:
                        future.set_result(nested(fields, COMMANDS[command][1], required=True))
                elif command in (0x80, 0x81) and scalar(fields, 2) == 0 and self.observer:
                    self.observer('stream', command, fields)
            elif len(suffix) == 2 and suffix[0] == 'telemetry' and self.observer:
                self.observer('telemetry', command, fields)
        except (ValueError, TypeError, KeyError, UnicodeError):
            # Malformed, wrong-schema, unrelated and expired packets never ACK.
            return

    async def request(self, command, payload=b''):
        if command not in COMMANDS:
            raise MqttCommandError('Command is not supported by the public profile')
        async with self._lock:
            if not self._subscriptions or not mqtt.is_connected(self.hass):
                raise MqttCommandError('MQTT is disconnected')
            self._next_id = (self._next_id % (2**32 - 1)) + 1
            request_id = self._next_id
            key = (command, request_id)
            future = asyncio.get_running_loop().create_future()
            self._pending[key] = future
            try:
                raw = integer(1, request_id) + message(COMMANDS[command][0], payload)
                await mqtt.async_publish(self.hass, f'device/{self.psn}/enduser/request/{command}', raw, qos=1, retain=False)
                async with asyncio.timeout(8):
                    return await future
            except TimeoutError:
                raise MqttCommandError('Device response timed out') from None
            finally:
                self._pending.pop(key, None)
                if not future.done():
                    future.cancel()

    @callback
    def close(self):
        for unsubscribe in self._subscriptions:
            unsubscribe()
        self._subscriptions.clear()
        for future in self._pending.values():
            if not future.done():
                future.set_exception(MqttCommandError('MQTT connection closed'))
        self._pending.clear()
