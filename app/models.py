"""Domain models used across the application."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Business:
    """Represent a single Google Maps business record."""

    name: str | None = None
    category: str | None = None
    rating: float | None = None
    reviews: int | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    hours: str | None = None
    google_maps_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Convert the business dataclass into a serializable dictionary."""

        return asdict(self)
