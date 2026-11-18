"""Base entity for the Ideal Clima integration."""

from collections.abc import Awaitable

from modbus_connection import ModbusError

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IdealclimaDataUpdateCoordinator
from .helpers import IdealclimaDevice


class IdealclimaEntity(CoordinatorEntity[IdealclimaDataUpdateCoordinator]):
    """Defines a base Ideal Clima entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        description: EntityDescription | None = None,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.device: IdealclimaDevice = coordinator.device
        self._attr_device_info = coordinator.device_info
        entry_id = coordinator.config_entry.entry_id
        if description is not None:
            self.entity_description = description
            self._attr_unique_id = f"{entry_id}_{description.key}"
        else:
            self._attr_unique_id = entry_id

    async def _async_execute(self, *calls: Awaitable[None]) -> None:
        """Run one or more Modbus write calls and refresh the coordinator."""
        try:
            for call in calls:
                await call
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            ) from err
        await self.coordinator.async_refresh()
