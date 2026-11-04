"""Serve the bundled Lovelace card and a credential-free entity index."""
import asyncio
import time
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .local_client import validate_local_host


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/dashboard'})
@websocket_api.async_response
async def websocket_dashboard(hass, connection, msg):
    registry = er.async_get(hass)
    entries = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            continue
        identities = {coordinator.entity_id_prefix + item['unique_id']: item['unique_id'] for item in coordinator.entities_config}
        mode = coordinator.connection_mode
        if mode == 'mqtt':
            identities.update({coordinator.entity_id_prefix + key: key for key in ('mqtt_reboot',)})
        entities = {}
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            key = identities.get(entity.unique_id)
            if key and entity.disabled_by is None and connection.user.permissions.check_entity(entity.entity_id, 'read'):
                entities[key] = entity.entity_id
        local_url = None
        if entities and entry.data.get('local_host'):
            try:
                local_url = f"http://{validate_local_host(entry.data['local_host'])}/"
            except ValueError:
                pass
        entries.append({'entry_id': entry.entry_id, 'name': entry.title, 'entities': entities,
                        'source': coordinator.source, 'connection_mode': mode,
                        'control_available': getattr(coordinator, 'mqtt_ready', coordinator.source != 'local'),
                        'local_url': local_url, 'last_sample': coordinator.last_sample,
                        'model': coordinator.device_info.get('product_family') or coordinator.device_info.get('model'),
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


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/allocate', vol.Required('entry_id'): str, vol.Required('watts'): [vol.All(int, vol.Range(min=0, max=140))]})
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


@websocket_api.websocket_command({vol.Required('type'): 'mcp_cocan/broker_settings', vol.Required('entry_id'): str,
    vol.Optional('action', default='status'): vol.In(['status', 'prepare', 'confirm', 'cancel']),
    vol.Optional('target'): vol.In(['official', 'custom']), vol.Optional('broker_url'): str,
    vol.Optional('flow_id'): str, vol.Optional('confirm', default=False): bool})
@websocket_api.async_response
async def websocket_broker_settings(hass, connection, msg):
    """Single-page adapter to the same identity-checked confirmation flow."""
    if not connection.user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Administrator required')
        return
    entry = hass.config_entries.async_get_entry(msg['entry_id'])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg['id'], 'not_found', 'Device not found')
        return
    from .broker import OFFICIAL_BROKER_URL, ha_broker, public_broker_uri
    from .local_client import LocalClient
    manager = hass.config_entries.options
    pending = hass.data.setdefault('mcp_cocan_broker_previews', {})
    now = time.monotonic()
    for flow_id, record in list(pending.items()):
        if now - record['created'] > 300 and not record['busy']:
            pending.pop(flow_id)
            try:
                manager.async_abort(flow_id)
            except Exception:
                pass
    def cancel(flow_id):
        record = pending.get(flow_id)
        if record and not record['busy'] and record['user'] == connection.user.id and record['entry'] == entry.entry_id:
            pending.pop(flow_id)
            try:
                manager.async_abort(flow_id)
            except Exception:
                pass
    try:
        action = msg['action']
        if action == 'status':
            # Only public endpoint metadata leaves the server.
            result = {'name': entry.title, 'mode': entry.data.get('connection_mode', 'mcp'),
                      'official': public_broker_uri(entry.data.get('official_broker_url', OFFICIAL_BROKER_URL)), 'current': None, 'custom': None}
            try:
                result['custom'] = (await ha_broker(hass, entry.data.get('local_host', '')))['uri']
            except Exception:
                pass
            try:
                psn = str(entry.data.get('mqtt_psn') or entry.unique_id or '')
                profile = await LocalClient(hass, entry.data.get('local_host', ''), psn).read_profile()
                result['current'] = public_broker_uri(profile['broker'])
            except Exception:
                result['error'] = 'device_broker_unavailable'
            connection.send_result(msg['id'], result)
            return
        if action == 'cancel':
            cancel(msg.get('flow_id'))
            connection.send_result(msg['id'], {})
            return
        if action == 'prepare':
            if msg.get('target') not in ('official', 'custom'):
                raise ValueError('Missing target')
            # At most one preview per user and device; every edit invalidates it.
            for flow_id, record in list(pending.items()):
                if record['user'] == connection.user.id and record['entry'] == entry.entry_id:
                    if record['busy']:
                        connection.send_error(msg['id'], 'switch_in_progress', 'A switch is already in progress')
                        return
                    cancel(flow_id)
            flow = await manager.async_init(entry.entry_id)
            flow_id = flow['flow_id']
            pending[flow_id] = {'user': connection.user.id, 'entry': entry.entry_id, 'created': now, 'busy': False}
            await manager.async_configure(flow_id, {'next_step_id': 'connection'})
            if msg['target'] == 'official':
                result = await manager.async_configure(flow_id, {'next_step_id': 'official_broker'})
            else:
                await manager.async_configure(flow_id, {'next_step_id': 'custom_broker'})
                result = await manager.async_configure(flow_id, {'broker_url': msg.get('broker_url', '')})
        else:
            flow_id = msg.get('flow_id')
            record = pending.get(flow_id)
            if not record or record['user'] != connection.user.id or record['entry'] != entry.entry_id or record['busy'] or msg.get('confirm') is not True:
                connection.send_error(msg['id'], 'confirmation_required', 'Prepare and confirm this switch first')
                return
            record['busy'] = True
            try:
                result = await manager.async_configure(flow_id, {'confirm': True})
            finally:
                record['busy'] = False
        completed = result['type'] == 'create_entry'
        errors = result.get('errors', {})
        preview = result.get('description_placeholders') if result.get('step_id') == 'broker_confirm' else None
        if completed or not preview:
            cancel(flow_id)
        connection.send_result(msg['id'], {'completed': completed, 'flow_id': None if completed or not preview else flow_id,
                                           'preview': preview, 'errors': errors})
    except Exception:
        if 'flow_id' in locals():
            cancel(flow_id)
        connection.send_error(msg['id'], 'broker_settings_failed', 'Could not load or apply Broker settings')


async def async_setup_frontend(hass):
    lock = hass.data.setdefault('mcp_cocan_frontend_lock', asyncio.Lock())
    async with lock:
        await _async_setup_frontend(hass)


async def _async_setup_frontend(hass):
    if hass.data.get('mcp_cocan_frontend'):
        return
    # No MCP URLs or credentials are sent to frontend assets or websocket data.
    await hass.http.async_register_static_paths([
        StaticPathConfig('/mcp_cocan/broker-settings.js', str(Path(__file__).parent / 'www' / 'broker-settings.js'), False),
        StaticPathConfig('/mcp_cocan/cocan-card.js', str(Path(__file__).parent / 'www' / 'cocan-card.js'), False)
    ])
    websocket_api.async_register_command(hass, websocket_dashboard)
    websocket_api.async_register_command(hass, websocket_refresh)
    websocket_api.async_register_command(hass, websocket_allocate)
    websocket_api.async_register_command(hass, websocket_broker_settings)
    from .settings_api import websocket_settings
    websocket_api.async_register_command(hass, websocket_settings)
    # The unified editor opens inside the integration's own settings dialog.
    # Remove the separately registered panel when upgrading from b13.
    if frontend.async_panel_exists(hass, 'cocan-settings'):
        frontend.async_remove_panel(hass, 'cocan-settings')
    frontend.add_extra_js_url(hass, '/mcp_cocan/broker-settings.js?v=0.4.1b17')
    frontend.add_extra_js_url(hass, '/mcp_cocan/cocan-card.js?v=0.4.1b17')
    hass.data['mcp_cocan_frontend'] = True
