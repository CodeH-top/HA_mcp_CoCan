"""MQTT device reboot (never factory reset)."""
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity import McpDeviceEntity


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get('connection_mode') == 'mqtt':
        async_add_entities([CocanReboot(hass.data[DOMAIN][entry.entry_id], {'unique_id': 'mqtt_reboot', 'name': '重启设备', 'type': 'button'})])


class CocanReboot(McpDeviceEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.RESTART
    async def async_press(self):
        try:
            await self.coordinator.async_call_tool('mqtt_reboot')
        except Exception:
            raise HomeAssistantError('Device did not acknowledge reboot') from None
