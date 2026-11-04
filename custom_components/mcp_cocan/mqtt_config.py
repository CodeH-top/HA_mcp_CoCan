"""Only expose entities with implemented public-profile MQTT data/controls."""
from copy import deepcopy
from .default_config import DEFAULT_ENTITIES_CONFIG


def mqtt_entities():
    supported = {'total_power', 'total_allocated_power', 'charging_strategy'}
    for port in range(1, 6):
        supported.update(f'port_{port}_{suffix}' for suffix in ('power', 'voltage', 'current', 'connected', 'protocol', 'charging', 'power_alloc'))
    # Match real default unique IDs without changing the MCP configuration.
    result = [deepcopy(entity) for entity in DEFAULT_ENTITIES_CONFIG if entity['unique_id'] in supported]
    result.append({'type': 'switch', 'name': '整机电源', 'unique_id': 'mqtt_device_power',
                   'on_tool': 'mqtt_device_power', 'on_args': {'state': 1},
                   'off_tool': 'mqtt_device_power', 'off_args': {'state': 0},
                   'poll_tool': 'mqtt_power', 'field': 'state', 'icon': 'mdi:power'})
    return result
