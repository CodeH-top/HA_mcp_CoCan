"""Device actions, including a transport-independent Broker shortcut."""
import asyncio
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity import McpDeviceEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [CocanBrokerToggle(coordinator, entry)]
    if entry.data.get('connection_mode') == 'mqtt':
        entities.append(CocanReboot(coordinator, {'unique_id': 'mqtt_reboot', 'name': '重启设备', 'type': 'button'}))
    async_add_entities(entities)


class CocanReboot(McpDeviceEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.RESTART
    async def async_press(self):
        try:
            await self.coordinator.async_call_tool('mqtt_reboot')
        except Exception:
            raise HomeAssistantError('Device did not acknowledge reboot') from None


class CocanBrokerToggle(McpDeviceEntity, ButtonEntity):
    """Explicit button press authorizes one opposite-Broker switch.

    Use the existing options flow so PSN, source recheck, HA authentication and
    target connection verification stay identical to the settings dialog.
    """

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, {'unique_id': 'broker_toggle', 'name': '切换官方 / HA MQTT',
                                     'type': 'button', 'icon': 'mdi:swap-horizontal', 'entity_category': 'config'})
        self._entry = entry
        # An explicit None suppresses HA platform translations as well.
        del self._attr_name
        self._attr_translation_key = 'broker_toggle'

    @property
    def available(self):
        # A failed cloud connection must not hide the LAN recovery action.
        return bool(self._entry.data.get('local_host') and
                    str(self._entry.data.get('mqtt_psn') or self._entry.unique_id or '').isdigit())

    @property
    def extra_state_attributes(self):
        mode = self.coordinator.connection_mode
        return {'current_mode': mode, 'target_mode': 'mqtt' if mode == 'mcp' else 'mcp',
                'switch_basis': 'live_device_broker'}

    async def async_press(self):
        lock = self.hass.data.setdefault('mcp_cocan_shortcut_locks', {}).setdefault(self._entry.entry_id, asyncio.Lock())
        if lock.locked():
            raise HomeAssistantError('Broker 切换正在进行，请勿重复操作')
        manager = self.hass.config_entries.options
        flow_id = None
        async with lock:
            try:
                result = await manager.async_init(self._entry.entry_id)
                flow_id = result['flow_id']
                result = await manager.async_configure(flow_id, {'next_step_id': 'quick_switch'})
                if result.get('step_id') != 'broker_confirm' or result.get('errors'):
                    raise HomeAssistantError('无法读取设备 Broker 或 HA MQTT 配置，请在集成设置中检查')
                result = await manager.async_configure(flow_id, {'confirm': True})
                if result['type'] != 'create_entry':
                    raise HomeAssistantError('Broker 切换未完成，请打开集成设置核对实际连接后重试')
            except HomeAssistantError:
                raise
            except Exception:
                raise HomeAssistantError('Broker 切换失败，请检查设备局域网地址和 HA MQTT 集成') from None
            finally:
                if flow_id:
                    try:
                        manager.async_abort(flow_id)
                    except Exception:
                        pass
