"""Private HTTP session helper for Kaloricke Tabulky."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp import DummyCookieJar
from homeassistant.helpers.aiohttp_client import async_create_clientsession

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.core import HomeAssistant


def async_create_kt_session(hass: HomeAssistant) -> ClientSession:
    """Create a session with no shared cookie jar.

    Each KT account authenticates separately and passes its own Cookie header.
    A private session keeps KT login cookies out of Home Assistant's shared
    cookie jar, which matters when several accounts are configured.
    """
    return async_create_clientsession(hass, cookie_jar=DummyCookieJar())
