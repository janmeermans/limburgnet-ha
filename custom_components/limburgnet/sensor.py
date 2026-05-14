"""Sensor platform voor Limburg.net afvalophaling."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FRACTIES, FRACTIE_NAMEN
from .coordinator import LimburgNetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak sensor entiteiten aan."""
    coordinator: LimburgNetCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        LimburgNetSensor(coordinator, fractie)
        for fractie in FRACTIES
    ])


class LimburgNetSensor(CoordinatorEntity, SensorEntity):
    """Sensor voor één afvalfractie van Limburg.net."""

    _attr_device_class    = SensorDeviceClass.WEIGHT
    _attr_state_class     = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon            = "mdi:trash-can-outline"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie: str) -> None:
        super().__init__(coordinator)
        self._fractie        = fractie
        self._attr_unique_id = f"limburgnet_{fractie}"
        self._attr_name      = f"Limburg.net {FRACTIE_NAMEN.get(fractie, fractie)}"

    @property
    def native_value(self) -> float | None:
        """Gewicht van de laatste ophaling in kg."""
        data = self.coordinator.data
        if data and data.get(self._fractie):
            return data[self._fractie]["gewicht_kg"]
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Extra attributen zoals datum, bedrag, prijs per kg."""
        data = self.coordinator.data
        if not data or not data.get(self._fractie):
            return {}
        leging = data[self._fractie]
        return {
            "datum":          leging.get("datum"),
            "datum_iso":      leging.get("datum_iso"),
            "betaald_bedrag": leging.get("betaald_bedrag"),
            "prijs_per_kg":   leging.get("prijs_per_kg"),
            "fractie":        self._fractie,
        }

    @property
    def device_info(self) -> dict:
        """Groepeer beide sensoren onder één apparaat."""
        return {
            "identifiers":  {(DOMAIN, "limburgnet")},
            "name":         "Limburg.net Afvalophaling",
            "manufacturer": "Limburg.net",
            "model":        "Huis-aan-huis ophalingen",
            "entry_type":   "service",
        }
