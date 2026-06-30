"""Configuration management for the Google Maps Business Extractor."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.constants import (
    DEFAULT_NAVIGATION_TIMEOUT,
    DEFAULT_SCROLL_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_VIEWPORT,
    GOOGLE_MAPS_URL,
    MAX_SCROLL_ATTEMPTS as DEFAULT_MAX_SCROLL_ATTEMPTS,
)


def _parse_bool(value: str, default: bool = False) -> bool:
    """Convert a string environment variable into a boolean."""

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_int(value: str, default: int) -> int:
    """Convert a string environment variable into an integer."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class AppConfig:
    """Centralized runtime configuration for the application."""

    headless: bool
    timeout: int
    retry_count: int
    scroll_delay: int
    click_delay: int
    output_folder: str
    log_folder: str
    max_scroll_attempts: int
    max_retries: int
    playwright_browser: str
    user_agent: str
    google_maps_url: str
    navigation_timeout: int
    viewport_width: int
    viewport_height: int
    excel_file_name: str
    csv_file_name: str
    json_file_name: str
    log_level: str
    input_prompt: str
    base_dir: Path

    @property
    def output_dir(self) -> Path:
        """Return the resolved output directory path."""

        return self._resolve_directory(self.output_folder)

    @property
    def log_dir(self) -> Path:
        """Return the resolved log directory path."""

        return self._resolve_directory(self.log_folder)

    @property
    def viewport(self) -> dict[str, int]:
        """Return the configured viewport in Playwright-compatible format."""

        return {
            "width": self.viewport_width,
            "height": self.viewport_height,
        }

    def _resolve_directory(self, value: str) -> Path:
        """Resolve a directory from either an absolute or relative path."""

        raw_path = Path(value)
        if raw_path.is_absolute():
            return raw_path
        return self.base_dir / raw_path

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build an application configuration object from environment variables."""

        base_dir = Path(__file__).resolve().parent.parent

        return cls(
            headless=_parse_bool(os.getenv("HEADLESS", "False"), default=False),
            timeout=_parse_int(
                os.getenv("TIMEOUT", str(DEFAULT_TIMEOUT)),
                default=DEFAULT_TIMEOUT,
            ),
            retry_count=_parse_int(os.getenv("RETRY_COUNT", "3"), default=3),
            scroll_delay=_parse_int(
                os.getenv("SCROLL_DELAY", str(DEFAULT_SCROLL_DELAY)),
                default=DEFAULT_SCROLL_DELAY,
            ),
            click_delay=_parse_int(os.getenv("CLICK_DELAY", "1"), default=1),
            output_folder=os.getenv("OUTPUT_FOLDER", "output"),
            log_folder=os.getenv("LOG_FOLDER", "logs"),
            max_scroll_attempts=_parse_int(
                os.getenv("MAX_SCROLL_ATTEMPTS", str(DEFAULT_MAX_SCROLL_ATTEMPTS)),
                default=DEFAULT_MAX_SCROLL_ATTEMPTS,
            ),
            max_retries=_parse_int(os.getenv("MAX_RETRIES", "3"), default=3),
            playwright_browser=os.getenv("PLAYWRIGHT_BROWSER", "chromium"),
            user_agent=os.getenv(
                "USER_AGENT",
                (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            ),
            google_maps_url=os.getenv("GOOGLE_MAPS_URL", GOOGLE_MAPS_URL),
            navigation_timeout=_parse_int(
                os.getenv("NAVIGATION_TIMEOUT", str(DEFAULT_NAVIGATION_TIMEOUT)),
                default=DEFAULT_NAVIGATION_TIMEOUT,
            ),
            viewport_width=_parse_int(
                os.getenv("VIEWPORT_WIDTH", str(DEFAULT_VIEWPORT["width"])),
                default=DEFAULT_VIEWPORT["width"],
            ),
            viewport_height=_parse_int(
                os.getenv("VIEWPORT_HEIGHT", str(DEFAULT_VIEWPORT["height"])),
                default=DEFAULT_VIEWPORT["height"],
            ),
            excel_file_name=os.getenv("EXCEL_FILE_NAME", "google_maps_results.xlsx"),
            csv_file_name=os.getenv("CSV_FILE_NAME", "google_maps_results.csv"),
            json_file_name=os.getenv("JSON_FILE_NAME", "google_maps_results.json"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            input_prompt=os.getenv(
                "INPUT_PROMPT",
                "Enter a Google Maps search keyword: ",
            ),
            base_dir=base_dir,
        )
