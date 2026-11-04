"""Read HA's broker address without copying its credentials to the integration."""
from urllib.parse import quote, urlsplit
import ipaddress
import socket

from homeassistant.components.network import async_get_source_ip


OFFICIAL_HOSTS = {'iot-broker.ifanrusercontent.com'}
OFFICIAL_BROKER_URL = 'mqtts://iot-broker.ifanrusercontent.com:8883'
ADDON_HOSTS = {'core-mosquitto', 'core-mosquitto.local.hass.io'}


def broker_endpoint(uri):
    """Return endpoint only; never return username, password, path or query."""
    parsed = urlsplit(uri)
    if parsed.scheme not in ('mqtt', 'mqtts') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Unsupported device broker URI')
    return parsed.scheme, parsed.hostname.lower().rstrip('.'), parsed.port or (8883 if parsed.scheme == 'mqtts' else 1883)


async def ha_broker(hass, device_host=''):
    entries = hass.config_entries.async_entries('mqtt')
    if len(entries) != 1:
        raise ValueError('Configure exactly one Home Assistant MQTT integration')
    config = {**entries[0].data, **entries[0].options}
    host = config.get('broker', '')
    if not isinstance(host, str) or not host:
        raise ValueError('HA MQTT broker is unavailable')
    if config.get('transport', 'tcp') != 'tcp':
        raise ValueError('Device requires a TCP MQTT broker')
    if host.lower().rstrip('.') in ADDON_HOSTS:
        target = device_host
        try:
            ipaddress.IPv4Address(target)
        except ValueError:
            target = None
        host = await async_get_source_ip(hass, **({'target_ip': target} if target else {}))
    host = host.lower().rstrip('.')
    if '/' in host or '@' in host:
        raise ValueError('Invalid broker hostname')
    port = config.get('port', 1883)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid broker port')
    tls = bool(config.get('certificate'))
    scheme = 'mqtts' if tls else 'mqtt'
    # Never copy or return username/password/client certificates.
    return {'scheme': scheme, 'host': host, 'port': port, 'uri': f'{scheme}://{host}:{port}'}


def connection_for_broker(uri):
    """Every non-official broker uses MQTT; never fall back to MCP."""
    _, host, _ = broker_endpoint(uri)
    return 'mcp' if host in OFFICIAL_HOSTS else 'mqtt'


def public_broker_uri(uri):
    """Describe an actual device endpoint without exposing its credentials."""
    parsed = urlsplit(uri)
    host = parsed.hostname
    if not host:
        raise ValueError('Invalid device Broker')
    authority = f'[{host}]' if ':' in host else host
    endpoint = f'{parsed.scheme}://{authority}:{parsed.port or (8883 if parsed.scheme == "mqtts" else 1883)}'
    broker_endpoint(endpoint)
    return endpoint


async def device_broker_uri(hass, uri, local_host):
    """Use HA MQTT authentication only for the confirmed device-side write.

    The result is transient: never return it to a form or store it in this
    integration's entry, logs or coordinator.
    """
    await validate_ha_broker(hass, uri, local_host)
    entry = hass.config_entries.async_entries('mqtt')[0]
    config = {**entry.data, **entry.options}
    username, password = config.get('username'), config.get('password')
    parts = urlsplit(uri)
    credentials = ''
    if username is not None or password is not None:
        credentials = quote(username or '', safe='')
        if password is not None:
            credentials += ':' + quote(password, safe='')
        credentials += '@'
    host = f'[{parts.hostname}]' if ':' in parts.hostname else parts.hostname
    return f'{parts.scheme}://{credentials}{host}:{parts.port or (8883 if parts.scheme == "mqtts" else 1883)}'


async def validate_ha_broker(hass, uri, local_host=''):
    scheme, host, port = broker_endpoint(uri)
    configured = await ha_broker(hass, local_host)
    if (scheme, port) != (configured['scheme'], configured['port']):
        raise ValueError('Broker does not match HA MQTT configuration')
    if host != configured['host']:
        def addresses(name):
            return {record[4][0] for record in socket.getaddrinfo(name, None, socket.AF_INET, socket.SOCK_STREAM)}
        device_ips = await hass.async_add_executor_job(addresses, host)
        ha_ips = await hass.async_add_executor_job(addresses, configured['host'])
        if not device_ips.intersection(ha_ips):
            raise ValueError('Broker does not match HA MQTT configuration')
