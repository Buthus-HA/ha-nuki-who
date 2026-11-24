"""Infos communes d'appareil."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def device_info(data) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, data.nuki_id)},
        name=f"{data.lock_name} – accès",
        manufacturer="Nuki (MQTT local)",
        model="Journal des accès",
    )
