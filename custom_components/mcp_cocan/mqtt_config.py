"""Preserve MCP identities and add MQTT diagnostics; absent data stays unknown."""
from copy import deepcopy
from .default_config import DEFAULT_ENTITIES_CONFIG


def mqtt_entities():
    # Keep all existing identities; unsupported fields stay unknown, not removed.
    result = deepcopy(DEFAULT_ENTITIES_CONFIG)
    result.append({'type': 'switch', 'name': '整机电源', 'unique_id': 'mqtt_device_power',
                   'on_tool': 'mqtt_device_power', 'on_args': {'state': 1},
                   'off_tool': 'mqtt_device_power', 'off_args': {'state': 0},
                   'poll_tool': 'mqtt_power', 'field': 'state', 'icon': 'mdi:power'})
    diagnostics = [('mqtt_app_version', '应用固件版本', 'app_version'),
                   ('mqtt_mcu_version', '协议芯片版本', 'bp_version'),
                   ('mqtt_zrlib_version', '协议库版本', 'zrlib_version')]
    for uid, name, field in diagnostics:
        result.append({'type': 'sensor', 'unique_id': uid, 'name': name,
                       'poll_tool': 'get_device_info', 'field': field, 'entity_category': 'diagnostic'})
    for uid, name, field in [('mqtt_power_budget', '当前功率预算', 'power_budget'),
                             ('mqtt_remaining_power', '剩余功率预算', 'remaining_power')]:
        result.append({'type': 'sensor', 'unique_id': uid, 'name': name,
                       'poll_tool': 'mqtt_budget', 'field': field, 'device_class': 'power',
                       'unit': 'W', 'state_class': 'measurement'})
    for port in range(1, 6):
        result.append({'type': 'sensor', 'unique_id': f'mqtt_port_{port}_session_raw',
                       'name': f'{("A", "C1", "C2", "C3", "C4")[port-1]} 口原始电量计数',
                       'poll_tool': 'get_port_details', 'field': f'ports.{port-1}.session_charge_raw',
                       'entity_category': 'diagnostic'})
        for field, name in [('manufacturer_vid', '设备 VID'), ('manufacturer_pid', '设备 PID'),
                            ('cable_vid', '线缆 VID'), ('cable_pid', '线缆 PID')]:
            result.append({'type': 'sensor', 'unique_id': f'mqtt_port_{port}_{field}',
                           'name': f'{("A", "C1", "C2", "C3", "C4")[port-1]} 口{name}',
                           'poll_tool': 'get_port_pd_status', 'field': f'ports[port={port}].{field}',
                           'entity_category': 'diagnostic'})
    return result
