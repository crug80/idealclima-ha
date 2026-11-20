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
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1


def _validate_max_target_temp(device: SkudoDCInverter, value: float) -> None:
    """Ensure maximum target temperature stays strictly above the minimum."""
    min_temp = device.settings.min_target_temp
    if min_temp is not None and value <= min_temp:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="max_target_temp_too_low",
        )


def _validate_min_target_temp(device: SkudoDCInverter, value: float) -> None:
    """Ensure minimum target temperature stays strictly below the maximum."""
    max_temp = device.settings.max_target_temp
    if max_temp is not None and value >= max_temp:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="min_target_temp_too_high",
        )


def _normalize_to_step(value: float, step: float) -> float:
    """Round value to the entity's native step resolution."""
    return round(value / step) * step


@dataclass(frozen=True, kw_only=True)
class IdealclimaNumberEntityDescription(NumberEntityDescription):
    """Describe an Ideal Clima number entity."""

    native_step: float
    value_fn: Callable[[SkudoDCInverter], float | int | None]
    write_fn: Callable[[SkudoDCInverter, float], Awaitable[None]]
    validate_fn: Callable[[SkudoDCInverter, float], None] | None = None


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
        validate_fn=_validate_max_target_temp,
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
        validate_fn=_validate_min_target_temp,
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
        normalized = _normalize_to_step(value, self.entity_description.native_step)
        async with self.coordinator.command_lock:
            if self.entity_description.validate_fn is not None:
                self.entity_description.validate_fn(self._skudo, normalized)
            await self._async_execute_locked(
                lambda: self.entity_description.write_fn(self._skudo, normalized)
            )
