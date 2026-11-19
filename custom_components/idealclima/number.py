"""Number platform for the Ideal Clima integration."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from idealclima_modbus import SkudoDCInverter

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IdealclimaNumberEntityDescription(NumberEntityDescription):
    """Describe an Ideal Clima number entity."""

    value_fn: Callable[[SkudoDCInverter], float | int | None]
    write_fn: Callable[[SkudoDCInverter, float], Awaitable[None]]


SKUDO_NUMBER_DESCRIPTIONS: tuple[IdealclimaNumberEntityDescription, ...] = (
    IdealclimaNumberEntityDescription(
        key="timer_off_hours",
        translation_key="timer_off_hours",
        native_min_value=0,
        native_max_value=11,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        value_fn=lambda device: device.settings.timer_off_hours,
        write_fn=lambda device, value: device.async_set_timer_off_hours(int(value)),
    ),
    IdealclimaNumberEntityDescription(
        key="timer_on_hours",
        translation_key="timer_on_hours",
        native_min_value=0,
        native_max_value=11,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        value_fn=lambda device: device.settings.timer_on_hours,
        write_fn=lambda device, value: device.async_set_timer_on_hours(int(value)),
    ),
    IdealclimaNumberEntityDescription(
        key="max_target_temp",
        translation_key="max_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        native_min_value=15.0,
        native_max_value=35.0,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        value_fn=lambda device: device.settings.max_target_temp,
        write_fn=lambda device, value: device.async_set_max_target_temp(value),
    ),
    IdealclimaNumberEntityDescription(
        key="min_target_temp",
        translation_key="min_target_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        native_min_value=15.0,
        native_max_value=35.0,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        value_fn=lambda device: device.settings.min_target_temp,
        write_fn=lambda device, value: device.async_set_min_target_temp(value),
    ),
    IdealclimaNumberEntityDescription(
        key="anti_draft_threshold",
        translation_key="anti_draft_threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0.0,
        native_max_value=40.0,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        value_fn=lambda device: device.settings.anti_draft_threshold,
        write_fn=lambda device, value: device.async_set_anti_draft_threshold(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ideal Clima number entities from a config entry."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, SkudoDCInverter):
        return
    async_add_entities(
        IdealclimaNumberEntity(coordinator, coordinator.device, description)
        for description in SKUDO_NUMBER_DESCRIPTIONS
    )


class IdealclimaNumberEntity(IdealclimaEntity, NumberEntity):
    """Representation of an Ideal Clima number entity."""

    entity_description: IdealclimaNumberEntityDescription

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        device: SkudoDCInverter,
        description: IdealclimaNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, description)
        self._skudo = device

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current number value."""
        value = self.entity_description.value_fn(self._skudo)
        return None if value is None else float(value)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Update the current number value."""
        await self._async_execute(
            lambda: self.entity_description.write_fn(self._skudo, value)
        )
