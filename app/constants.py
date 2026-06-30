"""Project-wide constants shared across the application."""

from __future__ import annotations


APPLICATION_NAME = "Google Maps Business Extractor"
GOOGLE_MAPS_URL = "https://www.google.com/maps"
DEFAULT_TIMEOUT = 10000
DEFAULT_NAVIGATION_TIMEOUT = 30000
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
DEFAULT_SCROLL_DELAY = 2
MAX_SCROLL_ATTEMPTS = 25
EXPORT_FORMATS = ("excel", "csv", "json")

# TODO: Revisit viewport, timeout, and export defaults once real browser flows exist.
