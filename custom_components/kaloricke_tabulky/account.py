"""Account identity helpers for the Kaloricke Tabulky integration."""

from __future__ import annotations

from typing import Any

from .const import CONF_ACCOUNT_LABEL, CONF_OWNER_USER_ID


def account_label(entry: Any) -> str:
    """Return the display label for an account, never falling back to blank.

    Existing entries created before labels were introduced fall back to their
    title. Keeping this helper in one place avoids leaking the email into a
    device name or entity attribute by accident.
    """
    for source in (getattr(entry, "options", {}), getattr(entry, "data", {})):
        if not isinstance(source, dict):
            continue
        value = source.get(CONF_ACCOUNT_LABEL)
        if isinstance(value, str) and value.strip():
            return value.strip()
    title = getattr(entry, "title", None)
    return str(title) if title else "Kaloricke Tabulky"


def owner_user_id(entry: Any) -> str | None:
    """Return the Home Assistant user id that owns this KT account."""
    for source in (getattr(entry, "options", {}), getattr(entry, "data", {})):
        if not isinstance(source, dict):
            continue
        value = source.get(CONF_OWNER_USER_ID)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def default_label_for_email(email: str) -> str:
    """Suggest a short default label from the local part of an email address."""
    local_part = str(email).split("@", 1)[0].strip()
    return local_part or "Account"


def is_owner_or_admin(user: Any, entry: Any) -> bool:
    """Return whether a user may write to the given account.

    Entries without an owner keep the historical, permissive behavior so
    single-user installations are not broken by an upgrade.
    """
    owner = owner_user_id(entry)
    if not owner:
        return True
    if getattr(user, "id", None) == owner:
        return True
    return bool(getattr(user, "is_admin", False))
