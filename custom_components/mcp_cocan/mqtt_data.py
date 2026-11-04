"""Translate public MQTT fields into the existing entity data contract.

No vendor identity guesses, undocumented energy conversions or cloud requests.
"""
from .mqtt_wire import scalar


# USB vendor labels adapted from CoCanBar PortIdentity.swift (MIT).
# Copyright (c) 2026 yangyihang96. Full license: licenses/CoCanBar-MIT.txt.
USB_VENDORS = {
    0x05AC: 'Apple',
    0x04E8: '三星',
    0x18D1: 'Google',
    0x12D1: '华为',
    0x2717: '小米',
    0x22D9: 'OPPO',
    0x2D95: 'vivo',
    0x2A70: '一加',
    0x2A45: '魅族',
    0x19D2: '中兴',
    0x22B8: '摩托罗拉',
    0x1004: 'LG',
    0x0BB4: 'HTC',
    0x054C: '索尼',
    0x0FCE: '索尼',
    0x17EF: '联想',
    0x413C: '戴尔',
    0x03F0: '惠普',
    0x0B05: '华硕',
    0x0502: '宏碁',
    0x045E: '微软',
    0x32AC: 'Framework',
    0x057E: '任天堂',
    0x28DE: 'Valve',
    0x046D: '罗技',
    0x1532: '雷蛇',
    0x2CA3: '大疆',
    0x2672: 'GoPro',
    0x091E: '佳明',
    0x1949: '亚马逊',
    0x291A: '安克',
    0x050D: '贝尔金',
}


def signed(fields, field):
    value = scalar(fields, field)
    return (value >> 1) ^ -(value & 1)


def pd_status(fields, port):
    result = {'port': port}
    mapping = {7: 'battery_present', 9: 'cable_is_active', 14: 'cable_max_vbus_voltage',
               16: 'cable_usb_highest_speed', 26: 'request_pdo_id', 38: 'sink_maximum_pdp',
               37: 'sink_operational_pdp', 40: 'operating_current', 41: 'pd_revision',
               43: 'has_battery', 44: 'dual_role_power', 45: 'has_emarker', 46: 'operating_voltage',
               1: 'battery_vid', 2: 'battery_pid', 32: 'cable_vid', 33: 'cable_pid',
               34: 'manufacturer_vid', 35: 'manufacturer_pid', 3: 'battery_design_capacity',
               4: 'battery_last_full_charge_capacity', 5: 'battery_present_capacity'}
    # Proto3 defaults are meaningful for booleans and bit fields only after a
    # successfully decoded, nonempty PD message from a charging PD port.
    for field, name in mapping.items():
        result[name] = scalar(fields, field)
    for name in ('cable_is_active', 'has_battery', 'dual_role_power', 'has_emarker', 'battery_present'):
        result[name] = bool(result[name])
    for name in ('operating_current', 'operating_voltage', 'request_pdo_id', 'sink_operational_pdp', 'sink_maximum_pdp'):
        if result[name] == 0:
            result.pop(name)
    if scalar(fields, 6) or not result['battery_present'] or result['battery_present_capacity'] == 65535:
        for name in ('battery_last_full_charge_capacity', 'battery_present_capacity'):
            result.pop(name, None)
    vid, pid = result['manufacturer_vid'], result['manufacturer_pid']
    identity_vid = vid or (result['battery_vid'] if result['battery_vid'] in (0x05AC, 0x04E8, 0x057E) else 0)
    brand = USB_VENDORS.get(identity_vid)
    if brand:
        result['device_brand_zh'] = brand
        result['device_name_zh'] = f'{brand} 设备（型号未识别）'
    elif vid:
        result['device_name_zh'] = f'USB PD 设备（VID {vid:04X} / PID {pid:04X}）'
    if result['has_emarker']:
        voltage = {0: '20V', 1: '30V', 2: '40V', 3: '50V'}.get(result['cable_max_vbus_voltage'])
        speed = {0: 'USB 2.0', 1: 'USB 3.2 Gen1', 2: 'USB 3.2/4 Gen2', 3: 'USB4 Gen3', 4: 'USB4 Gen4'}.get(result['cable_usb_highest_speed'])
        current = {1: '3A', 2: '5A'}.get(scalar(fields, 15))
        result['cable_max_vbus_voltage'] = voltage
        result['cable_usb_highest_speed'] = speed
        result['cable_name_zh'] = 'E-Marker 线缆' + (' · ' + ' / '.join(x for x in (current, voltage) if x) if current or voltage else '')
        cable_brand = USB_VENDORS.get(result['cable_vid'])
        if cable_brand:
            result['cable_brand_zh'] = cable_brand
    else:
        for key in ('cable_max_vbus_voltage', 'cable_usb_highest_speed', 'cable_is_active'):
            result.pop(key, None)
    return result


def display_config(fields, canonical=False):
    """Convert both documented config messages, without conflating wire tags."""
    if canonical:
        values = {'intensity': scalar(fields, 1), 'mode': scalar(fields, 2),
                  'flip': scalar(fields, 3), 'rotation': scalar(fields, 5),
                  'idle_animation': scalar(fields, 6), 'duration': scalar(fields, 7),
                  'mode_param': scalar(fields, 4)}
    else:
        values = {'mode': scalar(fields, 1), 'intensity': scalar(fields, 2),
                  'flip': scalar(fields, 3), 'rotation': scalar(fields, 4),
                  'idle_animation': scalar(fields, 5), 'duration': scalar(fields, 6)}
        if 7 in fields:
            value = scalar(fields, 7)
            if value not in (0, 1):
                raise ValueError('Invalid hourly chime')
            values['hourly_chime'] = bool(value)
    if values['mode'] not in (0, 1, 2) or not 0 <= values['intensity'] <= 100 or values['rotation'] not in (0, 90, 180, 270):
        raise ValueError('Invalid display config')
    return values


def display_snapshot(config):
    if not config:
        return {}
    intensity = config['intensity']
    # Explicit HA presets, not a claim about MCP's private brightness mapping.
    level = '关' if intensity == 0 else '低' if intensity <= 25 else '中' if intensity <= 50 else '高'
    result = {'level': level, 'intensity': intensity, 'rotation': config['rotation']}
    if config['mode'] in (1, 2):
        result['display_mode'] = '待机动画优先' if config['mode'] == 1 else '功率显示优先'
    idle = {1: '流星', 2: '康威的生命游戏', 4: '时间'}.get(config['idle_animation'])
    if idle:
        result['idle_display'] = idle
    if 'hourly_chime' in config:
        result['hourly_chime'] = config['hourly_chime']
    return result
