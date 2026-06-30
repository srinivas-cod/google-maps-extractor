"""Custom exception hierarchy for the Google Maps Business Extractor."""

from __future__ import annotations


class GoogleMapsExtractorError(Exception):
    """Base exception for all application-specific errors."""


class BrowserLaunchError(GoogleMapsExtractorError):
    """Raised when the browser cannot be launched."""


class BrowserCloseError(GoogleMapsExtractorError):
    """Raised when browser resources fail to close cleanly."""


class SearchError(GoogleMapsExtractorError):
    """Raised when search execution fails."""


class ScrollError(GoogleMapsExtractorError):
    """Raised when scrolling through results fails."""


class ExtractionError(GoogleMapsExtractorError):
    """Raised when business data cannot be extracted as expected."""


class ExportError(GoogleMapsExtractorError):
    """Raised when exporting collected records fails."""


class ValidationError(GoogleMapsExtractorError):
    """Raised when business data fails domain validation."""


class ConfigurationError(GoogleMapsExtractorError):
    """Raised when application configuration is missing or invalid."""


# TODO: Introduce richer exception context once browser and extraction logic are implemented.
