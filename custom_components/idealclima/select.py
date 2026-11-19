"""Select platform for the Ideal Clima integration."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from idealclima_modbus import SkudoDCInverter, TemperatureUnit

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IdealclimaSelectEntityDescription(SelectEntityDescription):
    """Describe an Ideal Clima select entity."""

    value_fn: Callable[[SkudoDCInverter], str | None]
    write_fn: Callable[[SkudoDCInverter, str], Awaitable[None]]


SKUDO_SELECT_DESCRIPTIONS: tuple[IdealclimaSelectEntityDescription, ...] = (
    IdealclimaSelectEntityDescription(
        key="temperature_unit",
        translation_key="temperature_unit",
        entity_category=EntityCategory.CONFIG,
        options=[member.name.lower() for member in TemperatureUnit],
        value_fn=lambda device: (
            None
            if device.settings.temperature_unit is None
            else device.settings.temperature_unit.name.lower()
        ),
        write_fn=lambda device, option: device.async_set_temperature_unit(
            TemperatureUnit[option.upper()]
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ideal Clima select entities from a config entry."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, SkudoDCInverter):
        return
    async_add_entities(
        IdealclimaSelectEntity(coordinator, coordinator.device, description)
        for description in SKUDO_SELECT_DESCRIPTIONS
    )


class IdealclimaSelectEntity(IdealclimaEntity, SelectEntity):
    """Representation of an Ideal Clima select entity."""

    entity_description: IdealclimaSelectEntityDescription

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        device: SkudoDCInverter,
        description: IdealclimaSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, description)
        self._skudo = device

    @property
    @override
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return self.entity_description.value_fn(self._skudo)

    @override
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._async_execute(
            lambda: self.entity_description.write_fn(self._skudo, option)
        )
