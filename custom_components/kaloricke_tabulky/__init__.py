"""The Kaloricke Tabulky integration."""

from __future__ import annotations

from datetime import timedelta
from math import isfinite
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, UnknownUser, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .account import account_label, is_owner_or_admin, owner_user_id
from .api import (
    KalorickeTabulkyApi,
    KalorickeTabulkyError,
    parse_service_date,
    parse_service_time,
)
from .const import (
    ATTR_ACCOUNT,
    ATTR_AMOUNT,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DATE,
    ATTR_FOOD_GUID,
    ATTR_KIND,
    ATTR_MEAL_TYPE,
    ATTR_PAGE,
    ATTR_QUERY,
    ATTR_TIME,
    ATTR_UNIT,
    ATTR_UNIT_GUID,
    ATTR_WEIGHT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    SERVICE_RECORD_FOOD,
    SERVICE_RECORD_WEIGHT,
    SERVICE_SEARCH_FOOD,
)
from .coordinator import KalorickeTabulkyCoordinator
from .session import async_create_kt_session

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


def _positive_finite_number(value: float) -> float:
    if not isfinite(value) or value <= 0:
        raise vol.Invalid("Value must be a positive finite number")
    return value

SERVICE_RECORD_WEIGHT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_ACCOUNT): cv.string,
        vol.Required(ATTR_WEIGHT): vol.Coerce(float),
        vol.Optional(ATTR_DATE): cv.string,
    }
)

SERVICE_SEARCH_FOOD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_ACCOUNT): cv.string,
        vol.Required(ATTR_QUERY): cv.string,
        vol.Optional(ATTR_KIND, default="food"): vol.In(("food", "drink")),
        vol.Optional(ATTR_PAGE, default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)

SERVICE_RECORD_FOOD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_ACCOUNT): cv.string,
        vol.Optional(ATTR_QUERY): cv.string,
        vol.Optional(ATTR_FOOD_GUID): cv.string,
        vol.Optional(ATTR_KIND, default="food"): vol.In(("food", "drink")),
        vol.Optional(ATTR_AMOUNT): vol.All(vol.Coerce(float), _positive_finite_number),
        vol.Optional(ATTR_UNIT): cv.string,
        vol.Optional(ATTR_UNIT_GUID): cv.string,
        vol.Optional(ATTR_DATE): cv.string,
        vol.Optional(ATTR_TIME): cv.string,
        vol.Optional(ATTR_MEAL_TYPE): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration-level services."""

    async def handle_record_weight(call: ServiceCall) -> None:
        coordinator = await _coordinator_from_service_call(hass, call, "recording weight")
        try:
            target_date = parse_service_date(call.data.get(ATTR_DATE)) or dt_util.now().date()
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        try:
            await coordinator.api.async_record_weight(call.data[ATTR_WEIGHT], target_date)
        except KalorickeTabulkyError as err:
            raise HomeAssistantError(str(err)) from err

        await coordinator.async_request_refresh()

    async def handle_search_food(call: ServiceCall) -> ServiceResponse:
        coordinator = await _coordinator_from_service_call(hass, call, "searching food")
        try:
            results = await coordinator.api.async_search_food(
                call.data[ATTR_QUERY],
                call.data[ATTR_KIND],
                call.data[ATTR_PAGE],
            )
        except KalorickeTabulkyError as err:
            raise HomeAssistantError(str(err)) from err
        return {"results": results}

    async def handle_record_food(call: ServiceCall) -> ServiceResponse | None:
        if not call.data.get(ATTR_QUERY) and not call.data.get(ATTR_FOOD_GUID):
            raise HomeAssistantError("Set query or food_guid")

        coordinator = await _coordinator_from_service_call(hass, call, "recording food")
        try:
            target_date = parse_service_date(call.data.get(ATTR_DATE)) or dt_util.now().date()
            target_time = parse_service_time(call.data.get(ATTR_TIME)) or dt_util.now().strftime(
                "%H:%M"
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        try:
            result = await coordinator.api.async_record_food(
                query=call.data.get(ATTR_QUERY),
                food_guid=call.data.get(ATTR_FOOD_GUID),
                kind=call.data[ATTR_KIND],
                amount=call.data.get(ATTR_AMOUNT),
                unit=call.data.get(ATTR_UNIT),
                unit_guid=call.data.get(ATTR_UNIT_GUID),
                target_date=target_date,
                target_time=target_time,
                meal_type=call.data.get(ATTR_MEAL_TYPE),
            )
        except KalorickeTabulkyError as err:
            raise HomeAssistantError(str(err)) from err

        await coordinator.async_request_refresh()
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_WEIGHT,
        handle_record_weight,
        schema=SERVICE_RECORD_WEIGHT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_FOOD,
        handle_search_food,
        schema=SERVICE_SEARCH_FOOD_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_FOOD,
        handle_record_food,
        schema=SERVICE_RECORD_FOOD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def _async_calling_user(hass: HomeAssistant, call: ServiceCall) -> Any | None:
    """Return the user who made the call, or None for HA-internal calls."""
    user_id = call.context.user_id
    if not user_id:
        return None
    user = await hass.auth.async_get_user(user_id)
    if user is None:
        raise UnknownUser(context=call.context)
    return user


async def _async_select_entry(
    hass: HomeAssistant,
    call: ServiceCall,
    user: Any | None,
    action: str,
) -> ConfigEntry:
    """Resolve an account from explicit fields, owner mapping or legacy rules."""
    entries = hass.config_entries.async_entries(DOMAIN)
    config_entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    account = call.data.get(ATTR_ACCOUNT)

    if config_entry_id:
        entry = next((item for item in entries if item.entry_id == config_entry_id), None)
        if entry is None:
            raise HomeAssistantError("Unknown Kaloricke Tabulky config entry")
        return entry

    if account:
        wanted = str(account).strip().casefold()
        matches = [
            item for item in entries if account_label(item).casefold() == wanted
        ]
        if not matches:
            raise HomeAssistantError(f"Unknown Kaloricke Tabulky account: {account}")
        if len(matches) > 1:
            raise HomeAssistantError(
                f"More than one Kaloricke Tabulky account is labeled {account}; "
                "use config_entry_id"
            )
        return matches[0]

    if user is not None:
        owned = [item for item in entries if owner_user_id(item) == user.id]
        if len(owned) == 1:
            return owned[0]
        if len(owned) > 1:
            raise HomeAssistantError(
                "This user owns more than one Kaloricke Tabulky account; "
                "use account or config_entry_id"
            )

    if len(entries) == 1:
        return entries[0]
    if not entries:
        raise HomeAssistantError(f"Set up Kaloricke Tabulky before {action}")
    raise HomeAssistantError(
        "Select account or config_entry_id when more than one Kaloricke Tabulky "
        "account is configured"
    )


async def _async_assert_owner(
    call: ServiceCall, entry: ConfigEntry, user: Any | None
) -> None:
    """Reject writes to an account owned by another HA user."""
    if user is not None and not is_owner_or_admin(user, entry):
        raise Unauthorized(context=call.context, config_entry_id=entry.entry_id)


async def _coordinator_from_service_call(
    hass: HomeAssistant, call: ServiceCall, action: str
) -> KalorickeTabulkyCoordinator:
    user = await _async_calling_user(hass, call)
    entry = await _async_select_entry(hass, call, user, action)
    await _async_assert_owner(call, entry, user)

    if entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            f"Kaloricke Tabulky account must be loaded before {action}"
        )

    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        raise HomeAssistantError(
            f"Kaloricke Tabulky account is not ready for {action}"
        )

    return coordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Kaloricke Tabulky from a config entry."""
    session = async_create_kt_session(hass)
    api = KalorickeTabulkyApi(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    interval_minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = KalorickeTabulkyCoordinator(
        hass,
        api,
        timedelta(minutes=max(MIN_SCAN_INTERVAL, interval_minutes)),
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
