"""Config flow for MCP Device integration.

Single-step flow:
  user: Connection settings (URL, transport, token, scan interval, device name)
  Entities are auto-created from DEFAULT_ENTITIES_CONFIG (can be edited later
  via Options Flow).
"""

from __future__ import annotations

import ipaddress
import json
import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_DEVICE_NAME,
    CONF_ENTITIES,
    CONF_MCP_TOKEN,
    CONF_MCP_URL,
    CONF_SCAN_INTERVAL,
    CONF_TRANSPORT,
    DEFAULT_DEVICE_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TransportType,
)
from .default_config import DEFAULT_ENTITIES_CONFIG
from .utils import validate_entities_config
from .local_client import validate_local_host

_LOGGER = logging.getLogger(__name__)


def _validate_mcp_url(url: str) -> str | None:
    """Validate MCP URL for basic security.

    Returns an error message string if invalid, or None if the URL passes checks.
    Blocks non-HTTP(S) schemes and loopback/link-local addresses.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return f"URL scheme must be http or https (got: {parsed.scheme})"

    hostname = parsed.hostname
    if not hostname:
        return "URL must have a hostname"

    # Block loopback and link-local addresses (SSRF mitigation)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return "URL must not point to loopback or link-local address"
    except ValueError:
        pass  # hostname is a domain name, not an IP -- allow

    return None

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MCP_URL): str,
        vol.Required(
            CONF_TRANSPORT,
            default=TransportType.STREAMABLE_HTTP,
        ): vol.In(
            {
                TransportType.STREAMABLE_HTTP: "Streamable HTTP",
                TransportType.SSE: "SSE (Server-Sent Events)",
            }
        ),
        vol.Optional(CONF_MCP_TOKEN): str,
        vol.Optional("local_host", default=""): str,
        vol.Optional(
            CONF_DEVICE_NAME,
            default=DEFAULT_DEVICE_NAME,
        ): str,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=DEFAULT_SCAN_INTERVAL,
        ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
    }
)


async def _test_connection(
    hass: HomeAssistant,
    url: str,
    transport: TransportType,
    token: str | None,
) -> dict[str, Any]:
    """Test MCP connection, return device info and available tool names."""
    from .mcp_client import McpClient

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with McpClient(url, transport, token) as client:
            # Get available tools
            tools = await client.list_tools()
            tool_names = [t.get("name", "unknown") for t in tools]
            _LOGGER.debug("MCP server offers %d tools", len(tool_names))

            # Try to get device info
            device_info: dict[str, Any] = {}
            if "get_device_info" in tool_names:
                result = await client.call_tool("get_device_info", {})
                device_info = result if isinstance(result, dict) else {}

            return {
                "device_info": device_info,
                "tools": tool_names,
            }
    except Exception as exc:
        _LOGGER.warning("MCP connection test failed: %s", type(exc).__name__)
        raise CannotConnectError("Unable to connect to MCP server") from exc


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect to the MCP server."""


async def _test_mqtt_connection(hass, psn):
    """Load optional MQTT code only after the HA integration is configured."""
    if not hass.config_entries.async_entries("mqtt"):
        raise CannotConnectError("Configure the Home Assistant MQTT integration first")
    from .mqtt_client import CocanMqttClient
    from .mqtt_wire import nested, text
    client = CocanMqttClient(hass, psn)
    try:
        await client.start()
        return text(nested(await client.request(0x92), 1, required=True), 1)
    finally:
        client.close()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MCP Device."""

    VERSION = 1
    MINOR_VERSION = 3

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["mcp", "mqtt"])

    async def async_step_mqtt(self, user_input=None):
        errors = {}
        schema = vol.Schema({
            vol.Required("mqtt_psn"): str,
            vol.Optional("local_host", default=""): str,
            vol.Optional(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=15): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
        })
        if user_input is not None:
            try:
                psn = user_input["mqtt_psn"].strip()
                local_host = user_input.get("local_host", "").strip()
                if local_host:
                    validate_local_host(local_host)
                if await _test_mqtt_connection(self.hass, psn) != psn:
                    raise ValueError("Identity mismatch or incompatible public schema")
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(psn)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME), data={
                    "connection_mode": "mqtt", "mqtt_psn": psn, "local_host": local_host,
                    CONF_MCP_URL: "", CONF_TRANSPORT: TransportType.STREAMABLE_HTTP.value,
                    CONF_DEVICE_NAME: user_input.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME),
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 15),
                })
        return self.async_show_form(step_id="mqtt", data_schema=schema, errors=errors)

    async def async_step_mcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_MCP_URL].strip()
            local_host = user_input.get("local_host", "").strip()
            if local_host:
                try:
                    validate_local_host(local_host)
                except ValueError:
                    return self.async_show_form(step_id="mcp", data_schema=STEP_USER_DATA_SCHEMA, errors={"base": "invalid_local_host"})
            transport = TransportType(user_input[CONF_TRANSPORT])
            token = user_input.get(CONF_MCP_TOKEN)

            # Validate URL before attempting connection (SSRF mitigation)
            url_error = _validate_mcp_url(url)
            if url_error:
                errors["base"] = "invalid_url"
                return self.async_show_form(
                    step_id="mcp",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                    description_placeholders={
                        "url_example": "https://mcp.thecandysign.com/your-device-id/mcp"
                    },
                )

            try:
                result = await _test_connection(self.hass, url, transport, token)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "unknown"
            else:
                device_info = result.get("device_info", {})

                unique_id = device_info.get("psn") or url
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                device_name = user_input.get(
                    CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME
                )

                # Auto-create entry with default entity config
                # Users can edit entity config later via Options Flow
                return self.async_create_entry(
                    title=device_name,
                    data={
                        CONF_MCP_URL: url,
                        "local_host": local_host,
                        CONF_TRANSPORT: transport.value,
                        CONF_MCP_TOKEN: token or "",
                        CONF_DEVICE_NAME: device_name,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                        CONF_ENTITIES: DEFAULT_ENTITIES_CONFIG,
                    },
                )

        return self.async_show_form(
            step_id="mcp",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "url_example": "https://mcp.thecandysign.com/your-device-id/mcp"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "OptionsFlowHandler":
        """Get the options flow handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for MCP Device.

    Allows editing connection settings and entity config JSON after setup.
    """

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["settings", "connection"])

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options -- connection settings + entity config."""
        if self.config_entry.data.get("connection_mode") == "mqtt":
            return await self.async_step_mqtt_options(user_input)
        if user_input is not None:
            entities_json = user_input.get(CONF_ENTITIES, "[]")
            errors: dict[str, str] = {}

            if _validate_mcp_url(user_input[CONF_MCP_URL]):
                return await self._show_form({"base": "invalid_url"})
            local_host = user_input.get("local_host", "").strip()
            if local_host:
                try:
                    validate_local_host(local_host)
                except ValueError:
                    return await self._show_form({"base": "invalid_local_host"})
            try:
                entities = json.loads(entities_json)
                if not isinstance(entities, list):
                    errors["base"] = "invalid_json"
                else:
                    validation_errors = validate_entities_config(entities)
                    if validation_errors:
                        errors["base"] = "validation_error"
                    else:
                        new_data = {
                            **self.config_entry.data,
                            CONF_MCP_URL: user_input[CONF_MCP_URL],
                            CONF_TRANSPORT: user_input[CONF_TRANSPORT],
                            CONF_MCP_TOKEN: user_input.get(CONF_MCP_TOKEN, ""),
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                            CONF_ENTITIES: entities,
                            "local_host": local_host,
                        }
                        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                        # Reload after returning the flow response.
                        self.hass.async_create_task(self.hass.config_entries.async_reload(self.config_entry.entry_id))
                        return self.async_create_entry(title="", data={})
            except json.JSONDecodeError:
                errors["base"] = "invalid_json"

            # Re-show form with errors
            return await self._show_form(errors)

        return await self._show_form({})

    async def _show_form(self, errors: dict[str, str]) -> FlowResult:
        """Show the options form."""
        current = self.config_entry.data
        current_entities = current.get(CONF_ENTITIES, DEFAULT_ENTITIES_CONFIG)
        entities_json = json.dumps(current_entities, indent=2, ensure_ascii=False)

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MCP_URL,
                        default=current.get(CONF_MCP_URL, ""),
                    ): str,
                    vol.Required(
                        CONF_TRANSPORT,
                        default=current.get(
                            CONF_TRANSPORT,
                            TransportType.STREAMABLE_HTTP.value,
                        ),
                    ): vol.In(
                        {
                            TransportType.STREAMABLE_HTTP: "Streamable HTTP",
                            TransportType.SSE: "SSE",
                        }
                    ),
                    vol.Optional(
                        CONF_MCP_TOKEN,
                        default=current.get(CONF_MCP_TOKEN, ""),
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                    vol.Optional("local_host", default=current.get("local_host", "")): str,
                    vol.Optional(
                        CONF_ENTITIES,
                        default=entities_json,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_mqtt_options(self, user_input=None):
        from .mqtt_wire import version_tuple
        errors = {}
        current = self.config_entry.data
        if user_input is not None:
            try:
                target = json.loads(user_input.get("firmware_target", "{}"))
                if not isinstance(target, dict):
                    raise ValueError("Expected object")
                local_host = user_input.get("local_host", "").strip()
                if local_host:
                    validate_local_host(local_host)
                if target:
                    if not isinstance(target.get("model"), str) or not target["model"]:
                        raise ValueError("Target model required")
                    for key in ("esp32", "sw3566", "fpga"):
                        version_tuple(target[key])
            except (ValueError, KeyError, AttributeError, TypeError):
                errors["base"] = "invalid_json"
            else:
                self.hass.config_entries.async_update_entry(self.config_entry, data={**current,
                    "local_host": local_host,
                    "firmware_target": target, "allow_ota": user_input.get("allow_ota", False),
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 15)})
                self.hass.async_create_task(self.hass.config_entries.async_reload(self.config_entry.entry_id))
                return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="mqtt_options", errors=errors, data_schema=vol.Schema({
            vol.Optional("local_host", default=current.get("local_host", "")): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=current.get(CONF_SCAN_INTERVAL, 15)): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            vol.Optional("firmware_target", default=json.dumps(current.get("firmware_target", {}))): str,
            vol.Optional("allow_ota", default=current.get("allow_ota", False)): bool,
        }))

    async def async_step_connection(self, user_input=None):
        """Switch HA transport after a read-only identity check; never write a broker."""
        from .broker import detect_connection, ha_broker
        current = self.config_entry.data
        values = {**current, **(user_input or {})}
        errors = {}
        if user_input is not None:
            try:
                selection = user_input["connection_mode"]
                mode = selection
                local_host = user_input.get("local_host", "").strip()
                if local_host:
                    validate_local_host(local_host)
                expected_psn = str(current.get("mqtt_psn") or self.config_entry.unique_id or "")
                if not expected_psn.isdigit():
                    errors["base"] = "identity_unavailable"
                else:
                    if selection == "auto":
                        if not local_host:
                            raise ValueError("Local host required to detect device broker")
                        mode = await detect_connection(self.hass, local_host, expected_psn)
                if not errors and mode == "mqtt":
                    if await _test_mqtt_connection(self.hass, expected_psn) != expected_psn:
                        errors["base"] = "wrong_device"
                elif not errors and mode == "mcp":
                    url = user_input.get(CONF_MCP_URL, "").strip()
                    if _validate_mcp_url(url):
                        errors["base"] = "invalid_url"
                    else:
                        result = await _test_connection(self.hass, url, TransportType(current.get(CONF_TRANSPORT, TransportType.STREAMABLE_HTTP)), current.get(CONF_MCP_TOKEN) or None)
                        if str(result["device_info"].get("psn")) != expected_psn:
                            errors["base"] = "wrong_device"
            except ValueError:
                errors["base"] = "broker_detection_failed"
            except Exception:
                errors["base"] = "cannot_connect"
            if not errors:
                # Freeze the existing namespace on the first switch. Existing MCP
                # entries use legacy IDs; native MQTT entries use a PSN prefix.
                prefix = current.get("entity_id_prefix", f"{expected_psn}_" if current.get("connection_mode") == "mqtt" else "")
                new_data = {**current, "connection_mode": mode, "connection_selection": selection, "mqtt_psn": expected_psn,
                            "entity_id_prefix": prefix, "local_host": local_host,
                            CONF_ENTITIES: current.get(CONF_ENTITIES, DEFAULT_ENTITIES_CONFIG)}
                # Preserve both profiles, including the last official MCP URL.
                if user_input.get(CONF_MCP_URL, "").strip():
                    new_data[CONF_MCP_URL] = user_input[CONF_MCP_URL].strip()
                new_data.setdefault(CONF_MCP_URL, "")
                new_data.setdefault(CONF_TRANSPORT, TransportType.STREAMABLE_HTTP.value)
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                self.hass.async_create_task(self.hass.config_entries.async_reload(self.config_entry.entry_id))
                return self.async_create_entry(title="", data={})
        try:
            detected_broker = (await ha_broker(self.hass, values.get("local_host", "")))["uri"]
        except Exception:
            detected_broker = "未配置或无法识别 / Not configured or unavailable"
        return self.async_show_form(step_id="connection", errors=errors, description_placeholders={"ha_broker": detected_broker}, data_schema=vol.Schema({
            vol.Required("connection_mode", default=values.get("connection_selection", values.get("connection_mode", "auto"))): vol.In({"auto": "根据设备 Broker 检测", "mcp": "官方云（MCP）", "mqtt": "HA MQTT Broker"}),
            vol.Optional("local_host", default=values.get("local_host", "")): str,
            vol.Optional(CONF_MCP_URL, default=values.get(CONF_MCP_URL, "")): str,
        }))
