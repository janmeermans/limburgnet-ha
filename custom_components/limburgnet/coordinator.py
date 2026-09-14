"""DataUpdateCoordinator voor Limburg.net."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LimburgNetAPI
from .const import (
    CONF_HUISNUMMER,
    CONF_NIS_CODE,
    CONF_STRAAT_NUMMER,
    CONF_TOEVOEGING,
    DOMAIN,
    SCAN_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


def calendar_config_from_entry(entry: ConfigEntry) -> dict[str, str] | None:
    """Extract calendar address from entry data/options (options win)."""
    merged: dict[str, Any] = {**entry.data, **entry.options}
    nis = merged.get(CONF_NIS_CODE)
    straat = merged.get(CONF_STRAAT_NUMMER)
    huis = merged.get(CONF_HUISNUMMER)
    if not nis or not straat or not huis:
        return None
    return {
        "nis_code": str(nis),
        "straat_nummer": str(straat),
        "huisnummer": str(huis),
        "toevoeging": str(merged.get(CONF_TOEVOEGING) or ""),
    }


class LimburgNetCoordinator(DataUpdateCoordinator):
    """Beheert het periodiek ophalen van data van Limburg.net."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: LimburgNetAPI,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> dict:
        """Haal alle data op — wordt automatisch aangeroepen door HA."""
        cal = calendar_config_from_entry(self.entry)
        try:
            return await self.hass.async_add_executor_job(
                self.api.haal_alle_data_op, cal
            )
        except ValueError as err:
            raise UpdateFailed(f"Fout bij ophalen data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Onverwachte fout: {err}") from err
