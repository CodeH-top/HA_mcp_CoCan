"""Compare explicitly configured targets, without claiming an official feed."""
from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity import McpDeviceEntity


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get('connection_mode') == 'mqtt':
        coordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([CocanFirmware(coordinator, {'unique_id': 'mqtt_firmware_target', 'name': '固件（自定义目标版本）', 'type': 'update'})])


class CocanFirmware(McpDeviceEntity, UpdateEntity):
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = '小电拼固件 · 用户配置目标'
    _attr_release_summary = '与用户明确配置的 ESP32/SW3566/FPGA 目标组合比较，不是厂商最新版本查询。'

    @property
    def supported_features(self):
        return UpdateEntityFeature.INSTALL if self.coordinator.allow_ota else UpdateEntityFeature(0)

    @property
    def installed_version(self):
        info = self.coordinator.device_info
        if not all(info.get(key) for key in ('app_version', 'bp_version', 'fpga_version')):
            return None
        return f"ESP32 {info['app_version']} / SW3566 {info['bp_version']} / FPGA {info['fpga_version']}"

    @property
    def latest_version(self):
        target = self.coordinator.firmware_target
        return f"ESP32 {target['esp32']} / SW3566 {target['sw3566']} / FPGA {target['fpga']}" if target else None

    @property
    def in_progress(self):
        return self.coordinator.ota_status == 'installing'

    @property
    def extra_state_attributes(self):
        coordinator = self.coordinator
        return {
            'firmware_source': 'manual_target',
            'official_update_check': 'not_available',
            'ota_enabled': coordinator.allow_ota,
            'ota_status': coordinator.ota_status,
            'ota_failure_reason': coordinator.ota_failure_reason,
            'ota_error': coordinator.ota_error,
            'target_model': (coordinator.firmware_target or {}).get('model'),
        }

    async def async_install(self, version, backup, **kwargs):
        try:
            if version and version != self.latest_version:
                raise ValueError('Only configured firmware target can be installed')
            await self.coordinator.async_install_firmware()
        except Exception:
            raise HomeAssistantError('Firmware request rejected, timed out, or not explicitly enabled') from None
