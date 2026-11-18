"""Climate platform for the Ideal Clima integration."""

from collections.abc import Awaitable
from typing import Any, override

from idealclima_modbus import (
    FanSpeed,
    IkaroHW,
    IkaroMode,
    SkudoDCInverter,
    SkudoMode,
    SkudoRunningMode,
)

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1

DEFAULT_MIN_TEMP = 18.0
DEFAULT_MAX_TEMP = 30.0

FAN_SUPER_SILENCE = "super_silence"

FAN_SPEED_TO_HA: dict[FanSpeed, str] = {
    FanSpeed.SUPER_SILENCE: FAN_SUPER_SILENCE,
    FanSpeed.LOW: FAN_LOW,
    FanSpeed.MEDIUM: FAN_MEDIUM,
    FanSpeed.HIGH: FAN_HIGH,
    FanSpeed.AUTO: FAN_AUTO,
}
HA_TO_FAN_SPEED: dict[str, FanSpeed] = {
    value: key for key, value in FAN_SPEED_TO_HA.items()
}

IKARO_MODE_TO_HA: dict[IkaroMode, HVACMode] = {
    IkaroMode.OFF: HVACMode.OFF,
    IkaroMode.COOL: HVACMode.COOL,
    IkaroMode.DRY: HVACMode.DRY,
    IkaroMode.FAN_ONLY: HVACMode.FAN_ONLY,
    IkaroMode.HEAT: HVACMode.HEAT,
}
HA_TO_IKARO_MODE: dict[HVACMode, IkaroMode] = {
    HVACMode.COOL: IkaroMode.COOL,
    HVACMode.DRY: IkaroMode.DRY,
    HVACMode.FAN_ONLY: IkaroMode.FAN_ONLY,
    HVACMode.HEAT: IkaroMode.HEAT,
}

SKUDO_MODE_TO_HA: dict[SkudoMode, HVACMode] = {
    SkudoMode.AUTO: HVACMode.AUTO,
    SkudoMode.COOL: HVACMode.COOL,
    SkudoMode.DRY: HVACMode.DRY,
    SkudoMode.FAN_ONLY: HVACMode.FAN_ONLY,
    SkudoMode.HEAT: HVACMode.HEAT,
}
HA_TO_SKUDO_MODE: dict[HVACMode, SkudoMode] = {
    HVACMode.AUTO: SkudoMode.AUTO,
    HVACMode.COOL: SkudoMode.COOL,
    HVACMode.DRY: SkudoMode.DRY,
    HVACMode.FAN_ONLY: SkudoMode.FAN_ONLY,
    HVACMode.HEAT: SkudoMode.HEAT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ideal Clima climate entity from a config entry."""
    async_add_entities([IdealclimaClimateEntity(entry.runtime_data)])


class IdealclimaClimateEntity(IdealclimaEntity, ClimateEntity):
    """Representation of an Ideal Clima fan coil unit."""

    _attr_name = None
    _attr_translation_key = "idealclima"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = PRECISION_HALVES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: IdealclimaDataUpdateCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_fan_modes = list(HA_TO_FAN_SPEED)
        if isinstance(self.device, IkaroHW):
            self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.COOL,
                HVACMode.DRY,
                HVACMode.FAN_ONLY,
                HVACMode.HEAT,
            ]
        else:
            self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.AUTO,
                HVACMode.COOL,
                HVACMode.DRY,
                HVACMode.FAN_ONLY,
                HVACMode.HEAT,
            ]

    @property
    @override
    def native_current_temperature(self) -> float | None:
        """Return the current ambient temperature."""
        return self.device.readings.ambient_temperature

    @property
    @override
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        if (
            isinstance(self.device, SkudoDCInverter)
            and self.device.settings.min_target_temp is not None
        ):
            return self.device.settings.min_target_temp
        return DEFAULT_MIN_TEMP

    @property
    @override
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        if (
            isinstance(self.device, SkudoDCInverter)
            and self.device.settings.max_target_temp is not None
        ):
            return self.device.settings.max_target_temp
        return DEFAULT_MAX_TEMP

    @property
    @override
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC operation mode."""
        if self.device.settings.power is None:
            return None
        if not self.device.settings.power:
            return HVACMode.OFF
        if isinstance(self.device, IkaroHW):
            if self.device.settings.mode is None:
                return None
            return IKARO_MODE_TO_HA[self.device.settings.mode]
        if self.device.settings.mode is None:
            return None
        return SKUDO_MODE_TO_HA[self.device.settings.mode]

    @property
    @override
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        speed = self.device.settings.fan_speed
        if speed is None:
            return None
        if speed is FanSpeed.OFF:
            return FAN_OFF
        return FAN_SPEED_TO_HA[speed]

    @property
    @override
    def native_target_temperature(self) -> float | None:
        """Return the active target temperature for the current HVAC mode."""
        mode = self.hvac_mode
        if mode in (HVACMode.COOL, HVACMode.DRY):
            return self.device.settings.target_temp_cool
        if mode is HVACMode.HEAT:
            return self.device.settings.target_temp_heat
        if mode is HVACMode.AUTO and isinstance(self.device, SkudoDCInverter):
            if self.device.readings.running_mode is SkudoRunningMode.HEAT:
                return self.device.settings.target_temp_auto_heat
            return self.device.settings.target_temp_auto_cool
        return None

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set a new target HVAC mode."""
        if hvac_mode is HVACMode.OFF:
            await self._async_execute(self.device.async_set_power(False))
            return

        calls: list[Awaitable[None]] = []
        if isinstance(self.device, IkaroHW):
            calls.append(self.device.async_set_mode(HA_TO_IKARO_MODE[hvac_mode]))
        else:
            calls.append(self.device.async_set_mode(HA_TO_SKUDO_MODE[hvac_mode]))

        if not self.device.settings.power:
            calls.append(self.device.async_set_power(True))

        await self._async_execute(*calls)

    @override
    async def async_turn_on(self) -> None:
        """Turn the fan coil unit on."""
        await self._async_execute(self.device.async_set_power(True))

    @override
    async def async_turn_off(self) -> None:
        """Turn the fan coil unit off."""
        await self._async_execute(self.device.async_set_power(False))

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set a new target fan mode."""
        await self._async_execute(
            self.device.async_set_fan_speed(HA_TO_FAN_SPEED[fan_mode])
        )

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature for the active mode."""
        calls: list[Awaitable[None]] = []
        mode = self.hvac_mode
        if (new_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            mode = HVACMode(new_mode)
            if mode is HVACMode.OFF:
                calls.append(self.device.async_set_power(False))
            else:
                if isinstance(self.device, IkaroHW):
                    calls.append(self.device.async_set_mode(HA_TO_IKARO_MODE[mode]))
                else:
                    calls.append(self.device.async_set_mode(HA_TO_SKUDO_MODE[mode]))
                if not self.device.settings.power:
                    calls.append(self.device.async_set_power(True))

        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            if mode in (HVACMode.COOL, HVACMode.DRY):
                calls.append(self.device.async_set_target_temp_cool(temperature))
            elif mode is HVACMode.HEAT:
                calls.append(self.device.async_set_target_temp_heat(temperature))
            elif mode is HVACMode.AUTO and isinstance(self.device, SkudoDCInverter):
                if self.device.readings.running_mode is SkudoRunningMode.HEAT:
                    calls.append(
                        self.device.async_set_target_temp_auto_heat(temperature)
                    )
                else:
                    calls.append(
                        self.device.async_set_target_temp_auto_cool(temperature)
                    )

        if calls:
            await self._async_execute(*calls)
