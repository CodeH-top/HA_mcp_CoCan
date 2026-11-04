"""Serve the bundled Lovelace card and a credential-free entity index."""
import asyncio
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/dashboard'})
@websocket_api.async_response
async def websocket_dashboard(hass, connection, msg):
    registry = er.async_get(hass)
    entries = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            continue
        entities = {}
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity.disabled_by is None and connection.user.permissions.check_entity(entity.entity_id, 'read'):
                entities[entity.translation_key or entity.unique_id] = entity.entity_id
        entries.append({'entry_id': entry.entry_id, 'name': entry.title, 'entities': entities,
                        'source': coordinator.source, 'last_sample': coordinator.last_sample,
                        'model': coordinator.device_info.get('product_family'),
                        'available': coordinator.last_update_success})
    connection.send_result(msg['id'], entries)


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/refresh', vol.Required('entry_id'): str})
@websocket_api.async_response
async def websocket_refresh(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Administrator required')
        return
    coordinator = hass.data.get(DOMAIN, {}).get(msg['entry_id'])
    if coordinator is None:
        connection.send_error(msg['id'], 'not_found', 'Entry not loaded')
        return
    await coordinator.async_request_refresh()
    connection.send_result(msg['id'], {'available': coordinator.last_update_success})


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/allocate', vol.Required('entry_id'): str, vol.Required('watts'): [vol.All(vol.Coerce(int), vol.Range(min=0, max=140))]})
@websocket_api.async_response
async def websocket_allocate(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Administrator required')
        return
    coordinator = hass.data.get(DOMAIN, {}).get(msg['entry_id'])
    if coordinator is None:
        connection.send_error(msg['id'], 'not_found', 'Entry not loaded')
        return
    try:
        await coordinator.async_set_allocations(msg['watts'])
    except Exception:
        connection.send_error(msg['id'], 'command_failed', 'Allocation rejected or device unavailable')
        return
    connection.send_result(msg['id'], {})


async def async_setup_frontend(hass):
    lock = hass.data.setdefault('mcp_cocan_frontend_lock', asyncio.Lock())
    async with lock:
        await _async_setup_frontend(hass)


async def _async_setup_frontend(hass):
    if hass.data.get('mcp_cocan_frontend'):
        return
    # No device URLs or tokens are ever sent to frontend assets or websocket data.
    await hass.http.async_register_static_paths([
        StaticPathConfig('/mcp_cocan/cocan-card.js', str(Path(__file__).parent / 'www' / 'cocan-card.js'), False)
    ])
    websocket_api.async_register_command(hass, websocket_dashboard)
    websocket_api.async_register_command(hass, websocket_refresh)
    websocket_api.async_register_command(hass, websocket_allocate)
    frontend.add_extra_js_url(hass, '/mcp_cocan/cocan-card.js?v=0.4.0')
    hass.data['mcp_cocan_frontend'] = True
