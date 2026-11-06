"""Admin-only connection fields and structured entity configuration editing."""
from copy import deepcopy
import hashlib
import json

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_ENTITIES
from .default_config import DEFAULT_ENTITIES_CONFIG
from .local_client import validate_local_host
from .utils import validate_entities_config


def configured_entities(data, mqtt=False):
    if mqtt:
        from .mqtt_config import mqtt_entities
        items = mqtt_entities()
    else:
        items = deepcopy(data.get(CONF_ENTITIES, DEFAULT_ENTITIES_CONFIG))
    # Older entries persist their original entity list. Add only this new group
    # control; never restore unrelated entities the user removed.
    if not any(item.get('unique_id') == 'all_ports_charging' for item in items):
        items.append(deepcopy(next(item for item in DEFAULT_ENTITIES_CONFIG if item['unique_id'] == 'all_ports_charging')))
    overrides = data.get('entity_overrides', {})
    return [deepcopy(overrides.get(f"{item['type']}:{item['unique_id']}", item)) for item in items]


def revision(data):
    return hashlib.sha256(json.dumps(dict(data), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/settings', vol.Required('entry_id'): str,
    vol.Optional('action', default='read'): vol.In(['read', 'save_connection', 'save_entity']),
    vol.Optional('revision'): str, vol.Optional('values'): dict, vol.Optional('entity'): dict})
@websocket_api.async_response
async def websocket_settings(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Administrator required')
        return
    entry = hass.config_entries.async_get_entry(msg['entry_id'])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg['id'], 'not_found', 'Device not found')
        return
    data = dict(entry.data)
    action = msg.get('action', 'read')
    if action == 'read':
        # Tokens are never returned. The device-specific MCP URL is only exposed
        # to this authenticated administrator editor, never the dashboard index.
        values = {key: data.get(key, default) for key, default in [('mcp_url', ''), ('transport', 'streamable_http'), ('local_host', ''), ('scan_interval', 15)]}
        values['has_token'] = bool(data.get('mcp_token'))
        registry = er.async_get(hass)
        prefix = data.get('entity_id_prefix', '')
        registered = {x.unique_id: x for x in er.async_entries_for_config_entry(registry, entry.entry_id)}
        items = []
        for config in configured_entities(data, data.get('connection_mode') == 'mqtt'):
            registered_entity = registered.get(prefix + config['unique_id'])
            items.append({'config': config, 'entity_id': registered_entity.entity_id if registered_entity else None,
                          'name': (registered_entity.name or registered_entity.original_name) if registered_entity else config.get('name'),
                          'disabled': bool(registered_entity and registered_entity.disabled_by)})
        connection.send_result(msg['id'], {'values': values, 'entities': items, 'revision': revision(data)})
        return
    if msg.get('revision') != revision(data):
        connection.send_error(msg['id'], 'settings_changed', 'Settings changed; reload before saving')
        return
    try:
        if action == 'save_connection':
            from .config_flow import _validate_mcp_url
            values = msg.get('values', {})
            allowed = {'mcp_url', 'transport', 'mcp_token', 'clear_token', 'local_host', 'scan_interval'}
            if set(values) - allowed:
                raise ValueError('Unknown settings')
            if 'mcp_url' in values:
                if not isinstance(values['mcp_url'], str) or (values['mcp_url'] and _validate_mcp_url(values['mcp_url'])) or (not values['mcp_url'] and data.get('connection_mode', 'mcp') == 'mcp'):
                    raise ValueError('Invalid MCP URL')
                data['mcp_url'] = values['mcp_url'].strip()
            if 'transport' in values:
                if values['transport'] not in ('streamable_http', 'sse'):
                    raise ValueError('Invalid transport')
                data['transport'] = values['transport']
            if 'local_host' in values:
                host = values['local_host'].strip()
                data['local_host'] = validate_local_host(host) if host else ''
            if 'scan_interval' in values:
                interval = values['scan_interval']
                if type(interval) is not int or not (10 if data.get('connection_mode') == 'mqtt' else 5) <= interval <= 300:
                    raise ValueError('Invalid scan interval')
                data['scan_interval'] = interval
            if values.get('clear_token') is True:
                data['mcp_token'] = ''
            elif values.get('mcp_token'):
                if not isinstance(values['mcp_token'], str):
                    raise ValueError('Invalid token')
                data['mcp_token'] = values['mcp_token']
        else:
            config = msg.get('entity', {})
            identity = (config.get('type'), config.get('unique_id'))
            existing = configured_entities(data, data.get('connection_mode') == 'mqtt')
            if identity not in {(x['type'], x['unique_id']) for x in existing}:
                raise ValueError('Entity identity cannot change')
            if len(json.dumps(config, allow_nan=False)) > 65536 or validate_entities_config([config]):
                raise ValueError('Invalid entity configuration')
            data['entity_overrides'] = {**data.get('entity_overrides', {}), f'{identity[0]}:{identity[1]}': deepcopy(config)}
        # Invalidate pending Broker previews when connection/config fields change.
        for flow_id, record in list(hass.data.get('mcp_cocan_broker_previews', {}).items()):
            if record['entry'] == entry.entry_id:
                if record['busy']:
                    connection.send_error(msg['id'], 'switch_in_progress', 'A Broker switch is in progress')
                    return
        for flow_id, record in list(hass.data.get('mcp_cocan_broker_previews', {}).items()):
            if record['entry'] == entry.entry_id:
                hass.data['mcp_cocan_broker_previews'].pop(flow_id)
                try:
                    hass.config_entries.options.async_abort(flow_id)
                except Exception:
                    pass
        hass.config_entries.async_update_entry(entry, data=data)
        connection.send_result(msg['id'], {'revision': revision(data)})
        hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
    except (ValueError, TypeError, KeyError, AttributeError):
        connection.send_error(msg['id'], 'invalid_settings', 'Invalid settings; nothing saved')
