"""Climate platform for the Ideal Clima integration."""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, override

from idealclima_modbus import (
    FanSpeed,
    IkaroHW,
    IkaroMode,
    SkudoDCInverter,
    SkudoMode,
    SkudoRunningMode,
)
from modbus_connection import ModbusError

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
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1

DEFAULT_MIN_TEMP = 18.0
DEFAULT_MAX_TEMP = 30.0
MIN_LIMIT_TEMP = 15.0
MAX_LIMIT_TEMP = 35.0
DEFAULT_FALLBACK_HEAT_TEMP = 21.0
DEFAULT_FALLBACK_COOL_TEMP = 24.0
FALLBACK_TEMP_MARGIN = 2.0
MIN_VALID_AMBIENT_TEMP = 5.0
MAX_VALID_AMBIENT_TEMP = 45.0

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


def _ikaro_fallback_target_temp(mode: HVACMode, ambient: float | None) -> float:
    """Compute a safe fallback target temperature when IKARO's setpoint is invalid."""
    if (
        ambient is not None
        and MIN_VALID_AMBIENT_TEMP <= ambient <= MAX_VALID_AMBIENT_TEMP
    ):
        raw = (
            max(ambient + FALLBACK_TEMP_MARGIN, DEFAULT_FALLBACK_HEAT_TEMP)
            if mode is HVACMode.HEAT
            else min(ambient - FALLBACK_TEMP_MARGIN, DEFAULT_FALLBACK_COOL_TEMP)
        )
    else:
        raw = (
            DEFAULT_FALLBACK_HEAT_TEMP
            if mode is HVACMode.HEAT
            else DEFAULT_FALLBACK_COOL_TEMP
        )
    clamped = min(max(raw, DEFAULT_MIN_TEMP), DEFAULT_MAX_TEMP)
    return round(clamped * 2) / 2


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

    def _skudo_temp_bounds(self) -> tuple[float, float]:
        """Return validated (min, max) target temperature bounds for SKUDO."""
        if not isinstance(self.device, SkudoDCInverter):
            return (DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP)
        low = self.device.settings.min_target_temp
        high = self.device.settings.max_target_temp
        min_temp = (
            low
            if low is not None and MIN_LIMIT_TEMP <= low <= MAX_LIMIT_TEMP
            else DEFAULT_MIN_TEMP
        )
        max_temp = (
            high
            if high is not None and MIN_LIMIT_TEMP <= high <= MAX_LIMIT_TEMP
            else DEFAULT_MAX_TEMP
        )
        if min_temp >= max_temp:
            return (DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP)
        return (min_temp, max_temp)

    @property
    @override
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        return self._skudo_temp_bounds()[0]

    @property
    @override
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        return self._skudo_temp_bounds()[1]

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
        if mode is HVACMode.COOL:
            return self.device.settings.target_temp_cool
        if mode is HVACMode.HEAT:
            return self.device.settings.target_temp_heat
        if mode is HVACMode.AUTO and isinstance(self.device, SkudoDCInverter):
            if self.device.readings.running_mode is SkudoRunningMode.HEAT:
                return self.device.settings.target_temp_auto_heat
            if self.device.readings.running_mode is SkudoRunningMode.COOL:
                return self.device.settings.target_temp_auto_cool
            return None
        return None

    def _ikaro_fallback_temp_call(
        self, mode: HVACMode | None
    ) -> Callable[[], Awaitable[None]] | None:
        """Return a setpoint write callable if IKARO lacks a valid target temp."""
        if not isinstance(self.device, IkaroHW):
            return None
        if mode is HVACMode.HEAT:
            current = self.device.settings.target_temp_heat
            if current is not None and DEFAULT_MIN_TEMP <= current <= DEFAULT_MAX_TEMP:
                return None
            return partial(
                self.device.async_set_target_temp_heat,
                _ikaro_fallback_target_temp(
                    mode, self.device.readings.ambient_temperature
                ),
            )
        if mode is HVACMode.COOL:
            current = self.device.settings.target_temp_cool
            if current is not None and DEFAULT_MIN_TEMP <= current <= DEFAULT_MAX_TEMP:
                return None
            return partial(
                self.device.async_set_target_temp_cool,
                _ikaro_fallback_target_temp(
                    mode, self.device.readings.ambient_temperature
                ),
            )
        return None

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set a new target HVAC mode."""
        if hvac_mode is HVACMode.OFF:
            await self._async_execute(partial(self.device.async_set_power, False))
            return

        calls: list[Callable[[], Awaitable[None]]] = []
        if isinstance(self.device, IkaroHW):
            calls.append(
                partial(self.device.async_set_mode, HA_TO_IKARO_MODE[hvac_mode])
            )
        else:
            calls.append(
                partial(self.device.async_set_mode, HA_TO_SKUDO_MODE[hvac_mode])
            )

        if not self.device.settings.power:
            if (fallback_call := self._ikaro_fallback_temp_call(hvac_mode)) is not None:
                calls.append(fallback_call)
            calls.append(partial(self.device.async_set_power, True))

        await self._async_execute(*calls)

    @override
    async def async_turn_on(self) -> None:
        """Turn the fan coil unit on."""
        calls: list[Callable[[], Awaitable[None]]] = []
        if isinstance(self.device, IkaroHW) and self.device.settings.mode is not None:
            mode = IKARO_MODE_TO_HA[self.device.settings.mode]
            if (fallback_call := self._ikaro_fallback_temp_call(mode)) is not None:
                calls.append(fallback_call)
        calls.append(partial(self.device.async_set_power, True))
        await self._async_execute(*calls)

    @override
    async def async_turn_off(self) -> None:
        """Turn the fan coil unit off."""
        await self._async_execute(partial(self.device.async_set_power, False))

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set a new target fan mode."""
        await self._async_execute(
            partial(self.device.async_set_fan_speed, HA_TO_FAN_SPEED[fan_mode])
        )

    async def _async_read_skudo_readings(self, device: SkudoDCInverter) -> None:
        """Read fresh input registers before selecting the AUTO setpoint register."""
        try:
            report = await device.async_update_readings()
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            ) from err
        if not report.complete:
            first_error = next(iter(report.failed.values()))
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            ) from first_error
        self.coordinator.async_update_listeners()

    @staticmethod
    def _skudo_auto_temp_call(
        device: SkudoDCInverter, temperature: float
    ) -> Callable[[], Awaitable[None]]:
        """Return the AUTO setpoint write callable matching SKUDO's running mode."""
        running_mode = device.readings.running_mode
        if running_mode is SkudoRunningMode.HEAT:
            return partial(device.async_set_target_temp_auto_heat, temperature)
        if running_mode is SkudoRunningMode.COOL:
            return partial(device.async_set_target_temp_auto_cool, temperature)
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_running_mode",
        )

    def _validate_target_temperature(self, temperature: float) -> None:
        """Re-check target temperature against live device bounds under lock."""
        min_temp, max_temp = self._skudo_temp_bounds()
        if not (min_temp <= temperature <= max_temp):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="temperature_out_of_range",
                translation_placeholders={
                    "temperature": str(temperature),
                    "min_temp": str(min_temp),
                    "max_temp": str(max_temp),
                },
            )

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature for the active mode."""
        new_mode = kwargs.get(ATTR_HVAC_MODE)
        if new_mode is not None:
            requested_mode = HVACMode(new_mode)
            if requested_mode not in self.hvac_modes:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="unsupported_hvac_mode",
                    translation_placeholders={"hvac_mode": requested_mode},
                )
        else:
            requested_mode = None

        temperature = kwargs.get(ATTR_TEMPERATURE)
        async with self.coordinator.command_lock:
            calls: list[Callable[[], Awaitable[None]]] = []
            mode = requested_mode if requested_mode is not None else self.hvac_mode
            turn_on = False
            if requested_mode is not None:
                if requested_mode is HVACMode.OFF:
                    calls.append(partial(self.device.async_set_power, False))
                else:
                    if isinstance(self.device, IkaroHW):
                        calls.append(
                            partial(
                                self.device.async_set_mode,
                                HA_TO_IKARO_MODE[requested_mode],
                            )
                        )
                    else:
                        calls.append(
                            partial(
                                self.device.async_set_mode,
                                HA_TO_SKUDO_MODE[requested_mode],
                            )
                        )
                    turn_on = not self.device.settings.power

            if (
                mode is HVACMode.AUTO
                and isinstance(self.device, SkudoDCInverter)
                and temperature is not None
            ):
                self._validate_target_temperature(temperature)
                await self._async_read_skudo_readings(self.device)
                calls.append(self._skudo_auto_temp_call(self.device, temperature))
            elif temperature is not None:
                if mode is HVACMode.COOL:
                    self._validate_target_temperature(temperature)
                    calls.append(
                        partial(self.device.async_set_target_temp_cool, temperature)
                    )
                elif mode is HVACMode.HEAT:
                    self._validate_target_temperature(temperature)
                    calls.append(
                        partial(self.device.async_set_target_temp_heat, temperature)
                    )
                elif requested_mode is None:
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="cannot_set_temperature_in_mode",
                        translation_placeholders={
                            "hvac_mode": mode.value if mode is not None else "unknown"
                        },
                    )

            if turn_on:
                calls.append(partial(self.device.async_set_power, True))

            if calls:
                await self._async_execute_locked(*calls)
