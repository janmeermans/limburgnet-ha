"""DataUpdateCoordinator voor Limburg.net."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LimburgNetAPI
from .const import DOMAIN, SCAN_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


class LimburgNetCoordinator(DataUpdateCoordinator):
    """Beheert het periodiek ophalen van data van Limburg.net."""

    def __init__(self, hass: HomeAssistant, api: LimburgNetAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Haal data op — wordt automatisch aangeroepen door HA."""
        try:
            return await self.hass.async_add_executor_job(
                self.api.haal_ledigingen_op
            )
        except ValueError as err:
            raise UpdateFailed(f"Fout bij ophalen data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Onverwachte fout: {err}") from err
