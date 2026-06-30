"""Browser lifecycle abstractions for future Playwright integration."""

from __future__ import annotations

import logging
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from app.config import AppConfig
from app.exceptions import BrowserCloseError, BrowserLaunchError, ConfigurationError


class BrowserManager:
    """Manage browser startup and teardown responsibilities."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the browser manager with shared dependencies."""

        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        """Return the currently managed browser page."""

        return self._page

    def start(self) -> Page:
        """Initialize the full browser stack and return the active page."""

        if self._page is not None:
            self.logger.info("Browser page already initialized. Reusing existing page.")
            return self._page

        self.logger.info("Starting Playwright browser lifecycle.")
        try:
            self._start_playwright()
            self._launch_browser()
            self.create_context()
            self.create_page()
            self._goto_google_maps()
        except (BrowserLaunchError, ConfigurationError):
            self.logger.exception("Browser initialization failed.")
            self._close_after_start_failure()
            raise
        except PlaywrightError as error:
            self.logger.exception("Playwright failed during browser initialization.")
            self._close_after_start_failure()
            raise BrowserLaunchError(
                "Failed to initialize the Playwright browser stack."
            ) from error

        if self._page is None:
            self._close_after_start_failure()
            raise BrowserLaunchError("Browser page was not created successfully.")

        return self._page

    def create_context(self) -> BrowserContext:
        """Create and configure an isolated browser context."""

        if self.context is not None:
            self.logger.info("Browser context already exists. Reusing existing context.")
            return self.context

        self.context = self._create_context()
        return self.context

    def create_page(self) -> Page:
        """Create and configure a new browser page."""

        if self._page is not None:
            self.logger.info("Browser page already exists. Reusing existing page.")
            return self._page

        self._page = self._create_page()
        return self._page

    def close(self) -> None:
        """Close all browser-related resources safely."""

        self.logger.info("Closing browser resources.")
        close_errors: list[Exception] = []

        for resource_name, resource in (
            ("page", self._page),
            ("context", self.context),
            ("browser", self.browser),
        ):
            if resource is None:
                continue

            try:
                resource.close()
                self.logger.info("%s closed successfully.", resource_name.capitalize())
            except PlaywrightError as error:
                self.logger.exception("Failed to close %s cleanly.", resource_name)
                close_errors.append(error)
            finally:
                if resource_name == "page":
                    self._page = None
                elif resource_name == "context":
                    self.context = None
                elif resource_name == "browser":
                    self.browser = None

        if self.playwright is not None:
            try:
                self.playwright.stop()
                self.logger.info("Playwright stopped successfully.")
            except PlaywrightError as error:
                self.logger.exception("Failed to stop Playwright cleanly.")
                close_errors.append(error)
            finally:
                self.playwright = None

        if close_errors:
            raise BrowserCloseError(
                "One or more browser resources could not be closed cleanly."
            ) from close_errors[0]

        self.logger.info("Browser closed successfully.")

    def _start_playwright(self) -> Playwright:
        """Start the Playwright driver."""

        if self.playwright is not None:
            return self.playwright

        self.logger.info("Starting Playwright.")
        try:
            self.playwright = sync_playwright().start()
        except PlaywrightError as error:
            raise BrowserLaunchError("Failed to start Playwright.") from error

        self.logger.info("Playwright started successfully.")
        return self.playwright

    def _launch_browser(self) -> Browser:
        """Launch the configured browser engine."""

        if self.browser is not None:
            return self.browser

        playwright = self.playwright or self._start_playwright()
        browser_type = self._get_browser_type(playwright)

        self.logger.info("Launching %s.", self.config.playwright_browser)
        try:
            self.browser = browser_type.launch(headless=self.config.headless)
        except PlaywrightError as error:
            raise BrowserLaunchError(
                f"Failed to launch browser '{self.config.playwright_browser}'."
            ) from error

        self.logger.info("Browser launched successfully.")
        return self.browser

    def _create_context(self) -> BrowserContext:
        """Create a configured browser context."""

        if self.browser is None:
            raise BrowserLaunchError("Browser must be launched before creating a context.")

        self.logger.info("Creating Browser Context.")
        try:
            context = self.browser.new_context(
                viewport=self.config.viewport,
                user_agent=self.config.user_agent,
            )
            context.set_default_timeout(self.config.timeout)
            context.set_default_navigation_timeout(self.config.navigation_timeout)
        except PlaywrightError as error:
            raise BrowserLaunchError("Failed to create browser context.") from error

        self.logger.info("Browser Context created.")
        return context

    def _create_page(self) -> Page:
        """Create a configured browser page."""

        if self.context is None:
            raise BrowserLaunchError("Browser context must exist before creating a page.")

        self.logger.info("Creating Browser Page.")
        try:
            page = self.context.new_page()
            page.set_default_timeout(self.config.timeout)
            page.set_default_navigation_timeout(self.config.navigation_timeout)
        except PlaywrightError as error:
            raise BrowserLaunchError("Failed to create browser page.") from error

        self.logger.info("Page created.")
        return page

    def _goto_google_maps(self) -> Page:
        """Navigate the active page to Google Maps and wait for it to load."""

        if self._page is None:
            raise BrowserLaunchError("Browser page must exist before navigation.")

        self.logger.info("Opening Google Maps.")
        try:
            self._page.goto(
                self.config.google_maps_url,
                wait_until="domcontentloaded",
                timeout=self.config.navigation_timeout,
            )
            self._page.wait_for_load_state(
                "load",
                timeout=self.config.navigation_timeout,
            )
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise BrowserLaunchError("Failed to open Google Maps.") from error

        self.logger.info("Google Maps loaded successfully.")
        return self._page

    def _get_browser_type(self, playwright: Playwright) -> Any:
        """Resolve the configured Playwright browser type."""

        browser_name = self.config.playwright_browser.strip().lower()
        browser_types: dict[str, Any] = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit,
        }

        if browser_name not in browser_types:
            raise ConfigurationError(
                "Unsupported browser type configured. "
                "Supported values are: chromium, firefox, webkit."
            )

        return browser_types[browser_name]

    def _close_after_start_failure(self) -> None:
        """Best-effort cleanup used during startup failures."""

        try:
            self.close()
        except BrowserCloseError:
            self.logger.exception(
                "Browser cleanup encountered additional errors after startup failure."
            )
