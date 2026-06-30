"""Reusable validation helpers for extracted business data."""

from __future__ import annotations

import re


PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]{7,25}$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
URL_PATTERN = re.compile(
    r"^(https?://)?([A-Za-z0-9-]+\.)+[A-Za-z]{2,}([/?#][^\s]*)?$",
    re.IGNORECASE,
)


def validate_phone(value: str | None) -> str | None:
    """Validate and normalize a phone number-like value."""

    if not value:
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()
    if not PHONE_PATTERN.fullmatch(cleaned):
        return None
    return cleaned


def validate_email(value: str | None) -> str | None:
    """Validate and normalize an email address."""

    if not value:
        return None

    cleaned = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(cleaned):
        return None
    return cleaned


def validate_url(value: str | None) -> str | None:
    """Validate and normalize a URL."""

    if not value:
        return None

    cleaned = value.strip()
    if not URL_PATTERN.fullmatch(cleaned):
        return None
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    return f"https://{cleaned}"


def validate_rating(value: float | int | str | None) -> float | None:
    """Validate and normalize a business rating between 0 and 5."""

    if value is None:
        return None

    try:
        cleaned = float(value)
    except (TypeError, ValueError):
        return None

    if 0.0 <= cleaned <= 5.0:
        return round(cleaned, 1)
    return None


def validate_coordinates(
    latitude: float | int | str | None,
    longitude: float | int | str | None,
) -> tuple[float | None, float | None]:
    """Validate and normalize latitude and longitude values."""

    if latitude is None or longitude is None:
        return None, None

    try:
        parsed_latitude = float(latitude)
        parsed_longitude = float(longitude)
    except (TypeError, ValueError):
        return None, None

    if not -90 <= parsed_latitude <= 90:
        return None, None
    if not -180 <= parsed_longitude <= 180:
        return None, None

    return parsed_latitude, parsed_longitude


# TODO: Add business-domain validators for hours, category names, and review counts later.
