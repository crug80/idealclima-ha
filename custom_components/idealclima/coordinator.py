"""Data update coordinator for the Ideal Clima integration."""

from datetime import timedelta
import logging
from typing import override

from modbus_connection import ModbusConnectionError, ModbusError, ModbusTimeoutError
from modbus_connection.model import UpdateReport

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_MANUFACTURER,
    DOMAIN,
    MODEL_NAMES,
    SCAN_INTERVAL,
    IdealclimaModel,
)
from .helpers import IdealclimaDevice

_LOGGER = logging.getLogger(__name__)

type IdealclimaConfigEntry = ConfigEntry[IdealclimaDataUpdateCoordinator]


class IdealclimaDataUpdateCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Class to manage fetching Ideal Clima device data."""

    config_entry: IdealclimaConfigEntry
    device: IdealclimaDevice

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IdealclimaConfigEntry,
        device: IdealclimaDevice,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.device = device
        model = IdealclimaModel(entry.data[CONF_MODEL])
        self.device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=ATTR_MANUFACTURER,
            model=MODEL_NAMES[model],
        )

    @override
    async def _async_update_data(self) -> UpdateReport:
        """Poll both input readings and holding settings from the unit."""
        try:
            report = await self.device.async_update()
        except (ModbusConnectionError, ModbusTimeoutError) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="device_unreachable",
            ) from err
        except ModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="modbus_error",
            ) from err

        if not report.complete:
            first_error = next(iter(report.failed.values()))
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="modbus_error",
            ) from first_error

        return report
