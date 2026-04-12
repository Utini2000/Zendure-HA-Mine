"""Initialize the Zendure component."""

import logging

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import Api
from .const import (
    CONF_APPTOKEN,
    CONF_DEVICES,
    CONF_LOCAL_ONLY,
    CONF_MQTTLOCAL,
    CONF_MQTTLOG,
    CONF_MQTTPORT,
    CONF_MQTTPSW,
    CONF_MQTTSERVER,
    CONF_MQTTUSER,
    CONF_P1METER,
    CONF_SIM,
    CONF_WIFIPSW,
    CONF_WIFISSID,
    DOMAIN,
)
from .device import ZendureDevice
from .manager import ZendureConfigEntry, ZendureManager

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)

YAML_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_APPTOKEN): cv.string,
        vol.Optional(CONF_P1METER, default="sensor.power_actual"): cv.entity_id,
        vol.Optional(CONF_MQTTLOG, default=False): cv.boolean,
        vol.Optional(CONF_MQTTLOCAL, default=True): cv.boolean,
        vol.Optional(CONF_MQTTSERVER): cv.string,
        vol.Optional(CONF_MQTTPORT, default=1883): cv.port,
        vol.Optional(CONF_MQTTUSER): cv.string,
        vol.Optional(CONF_MQTTPSW): cv.string,
        vol.Optional(CONF_WIFISSID): cv.string,
        vol.Optional(CONF_WIFIPSW): cv.string,
        vol.Optional(CONF_LOCAL_ONLY, default=False): cv.boolean,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(cv.ensure_list, [dict]),
    }
)
CONFIG_SCHEMA = vol.Schema({DOMAIN: YAML_SCHEMA}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Zendure from YAML and import into a config entry."""
    if DOMAIN not in config:
        return True

    if hass.config_entries.async_entries(DOMAIN):
        _LOGGER.debug("Zendure config entry already exists, skipping YAML import")
        return True

    yaml_data = YAML_SCHEMA(config[DOMAIN])
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data=yaml_data,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZendureConfigEntry) -> bool:
    """Set up Zendure as config entry."""
    manager = ZendureManager(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await manager.loadDevices()
    entry.runtime_data = manager
    await manager.async_config_entry_first_refresh()
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def update_listener(_hass: HomeAssistant, entry: ZendureConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Updating Zendure config entry: %s", entry.entry_id)
    Api.mqttLogging = entry.data.get(CONF_MQTTLOG, False)
    ZendureManager.simulation = entry.data.get(CONF_SIM, False)
    entry.runtime_data.update_p1meter(entry.data.get(CONF_P1METER, "sensor.power_actual"))


async def async_unload_entry(hass: HomeAssistant, entry: ZendureConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Zendure config entry: %s", entry.entry_id)
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        manager = entry.runtime_data
        if Api.mqttCloud.is_connected():
            Api.mqttCloud.disconnect()
        if Api.mqttLocal.is_connected():
            Api.mqttLocal.disconnect()
        for c in Api.devices.values():
            if c.zendure is not None and c.zendure.is_connected():
                c.zendure.disconnect()
            c.zendure = None
        manager.update_p1meter(None)
        manager.fuseGroups.clear()
        manager.devices.clear()
    return result


async def async_remove_config_entry_device(_hass: HomeAssistant, entry: ZendureConfigEntry, device_entry: dr.DeviceEntry) -> bool:
    """Remove a device from a config entry."""
    manager = entry.runtime_data

    # check for device to remove
    for d in manager.devices:
        if d.name == device_entry.name:
            manager.devices.remove(d)
            return True

        if isinstance(d, ZendureDevice) and (bat := next((b for b in d.batteries.values() if b.name == device_entry.name), None)) is not None:
            d.batteries.pop(bat.deviceId)
            return True

    return True
