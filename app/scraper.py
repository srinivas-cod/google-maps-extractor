"""Scraper workflow placeholders for future Google Maps automation."""

from __future__ import annotations

import logging
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser import BrowserManager
from app.config import AppConfig
from app.exceptions import SearchError
from app.extractor import BusinessExtractor
from app.models import Business
from app.selectors import Selectors


class ProcessedBusinessRecord(dict[str, str | float | int | None]):
    """Dictionary-like processed business record with exporter compatibility."""

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Map extracted field names to the Business export schema."""

        return {
            "name": self.get("business_name"),
            "category": self.get("category"),
            "rating": self.get("rating"),
            "reviews": self.get("review_count"),
            "address": self.get("address"),
            "phone": self.get("phone"),
            "website": self.get("website"),
            "hours": self.get("opening_hours"),
            "google_maps_url": self.get("google_maps_url"),
            "latitude": self.get("latitude"),
            "longitude": self.get("longitude"),
        }


class Scraper:
    """Coordinate browser automation, result traversal, and detail extraction."""

    def __init__(
        self,
        keyword: str,
        config: AppConfig,
        logger: logging.Logger | None = None,
        extractor: BusinessExtractor | None = None,
    ) -> None:
        """Initialize scraper dependencies and runtime state."""

        self.keyword = keyword
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = extractor or BusinessExtractor(logger=self.logger)
        self.browser_manager = BrowserManager(config=config, logger=self.logger)
        self._results_panel: Locator | None = None
        self._discovered_businesses: list[str] = []
        self._processed_businesses: list[ProcessedBusinessRecord] = []

    def search(self) -> list[ProcessedBusinessRecord]:
        """Perform a Google Maps search and return processed business records."""

        page = self.browser_manager.page
        if page is None:
            raise SearchError("Browser page is not available for search execution.")

        self.logger.info("Starting search for keyword='%s'.", self.keyword)

        try:
            self.logger.info("Locating search box.")
            search_box = page.locator(Selectors.SEARCH_BOX)
            search_box.wait_for(state="visible", timeout=self.config.timeout)

            self.logger.info("Entering keyword into search box.")
            search_box.fill("")
            search_box.fill(self.keyword)

            self.logger.info("Submitting search.")
            search_box.press("Enter")

            self.logger.info("Waiting for results.")
            result_panel = page.locator(Selectors.RESULTS_PANEL).first
            result_panel.wait_for(
                state="visible",
                timeout=self.config.navigation_timeout,
            )
            page.wait_for_function(
                """
                ([panel_selector, keyword]) => {
                    const panel = document.querySelector(panel_selector);
                    if (!panel || !(panel.offsetWidth || panel.offsetHeight || panel.getClientRects().length)) {
                        return false;
                    }

                    const normalizedKeyword = keyword.trim().toLowerCase();
                    const panelLabel = (panel.getAttribute("aria-label") || "").toLowerCase();
                    const hasKeywordInPanelLabel = normalizedKeyword
                        ? panelLabel.includes(normalizedKeyword)
                        : true;
                    const hasResultArticles = panel.querySelectorAll('[role="article"]').length > 0;
                    const hasPlaceLinks = panel.querySelectorAll('a[href*="/place/"]').length > 0;
                    const hasResultsHeading = Array.from(document.querySelectorAll("h1")).some((heading) => {
                        const text = (heading.textContent || "").trim().toLowerCase();
                        const isVisible = heading.offsetWidth || heading.offsetHeight || heading.getClientRects().length;
                        return isVisible && text === "results";
                    });

                    return hasKeywordInPanelLabel && hasResultArticles && hasPlaceLinks && hasResultsHeading;
                }
                """,
                arg=[Selectors.RESULTS_PANEL, self.keyword],
                timeout=self.config.navigation_timeout,
            )

            current_value = search_box.input_value().strip()
            if current_value.lower() != self.keyword.strip().lower():
                raise SearchError("Google Maps search box value does not match the keyword.")

            self._detect_results_panel()
            processed_businesses = self._process_businesses()
            self.logger.info("Discovered businesses: %s", len(self._discovered_businesses))
            self.logger.info("Search results successfully loaded.")
            return processed_businesses

        except SearchError:
            self.logger.exception("Search verification failed.")
            raise
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            self.logger.exception("Search execution failed.")
            raise SearchError("Failed to complete the Google Maps search workflow.") from error

    def _detect_results_panel(self) -> Locator:
        """Locate, validate, and return the Google Maps results panel."""

        page = self.browser_manager.page
        if page is None:
            raise SearchError("Browser page is not available for results panel detection.")

        try:
            self.logger.info("Locating results panel...")
            results_panel = page.locator(Selectors.RESULTS_PANEL).first
            results_panel.wait_for(
                state="visible",
                timeout=self.config.navigation_timeout,
            )
            self.logger.info("Results panel found.")
            self.logger.info("Panel is visible.")

            panel_metrics = results_panel.evaluate(
                """
                (element) => ({
                    clientHeight: element.clientHeight,
                    scrollHeight: element.scrollHeight,
                    scrollTop: element.scrollTop,
                })
                """
            )

            client_height = int(panel_metrics["clientHeight"])
            scroll_height = int(panel_metrics["scrollHeight"])
            scroll_top = int(panel_metrics["scrollTop"])

            if client_height <= 0:
                raise SearchError("Results panel is visible but has an invalid clientHeight.")
            if scroll_height <= client_height:
                raise SearchError("Results panel was found but does not appear scrollable.")

            self.logger.info("clientHeight=%s", client_height)
            self.logger.info("scrollHeight=%s", scroll_height)
            self.logger.info("scrollTop=%s", scroll_top)
            self.logger.info("Results panel ready.")
            self._results_panel = results_panel
            return results_panel

        except SearchError:
            raise
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to detect the Google Maps results panel.") from error

    def _read_results_panel_metrics(self) -> dict[str, int]:
        """Read scroll metrics from the detected results panel for diagnostics."""

        results_panel = self._results_panel
        if results_panel is None:
            raise SearchError("Results panel is unavailable for diagnostic metric collection.")

        try:
            panel_metrics = results_panel.evaluate(
                """
                (element) => ({
                    scrollTop: element.scrollTop,
                    scrollHeight: element.scrollHeight,
                    clientHeight: element.clientHeight,
                })
                """
            )
            return {
                "scrollTop": int(panel_metrics["scrollTop"]),
                "scrollHeight": int(panel_metrics["scrollHeight"]),
                "clientHeight": int(panel_metrics["clientHeight"]),
            }
        except PlaywrightError as error:
            raise SearchError("Failed to read results panel metrics.") from error

    def _get_visible_business_names(self) -> list[str]:
        """Return the currently visible business names from the results panel."""

        return [
            business_snapshot["name"]
            for business_snapshot in self._get_visible_business_snapshots()
            if business_snapshot["name"] is not None
        ]

    def _get_visible_business_snapshots(self) -> list[dict[str, str | None]]:
        """Return a snapshot of currently visible businesses and their stable identities."""

        results_panel = self._results_panel
        if results_panel is None:
            raise SearchError("Results panel is unavailable for visible business discovery.")

        try:
            business_cards = results_panel.locator(Selectors.BUSINESS_CARD)
            business_card_count = business_cards.count()
            visible_businesses: list[dict[str, str | None]] = []

            for index in range(business_card_count):
                business_card = business_cards.nth(index)
                business_name = self._extract_business_name_from_card(business_card)
                place_href = self._extract_place_href_from_card(business_card)
                if business_name:
                    visible_businesses.append(
                        {
                            "name": business_name,
                            "place_href": place_href,
                        }
                    )

            return visible_businesses
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to collect visible business names.") from error

    def _extract_business_name_from_card(self, business_card: Locator) -> str | None:
        """Extract a reliable business name from a Google Maps result card."""

        try:
            business_card_link = business_card.locator(Selectors.BUSINESS_CARD_LINK).first
            if business_card_link.count() > 0:
                aria_label = business_card_link.get_attribute("aria-label")
                if aria_label:
                    normalized_label = aria_label.strip()
                    if normalized_label and normalized_label.lower() != "sponsored":
                        return normalized_label

                link_text = (business_card_link.text_content() or "").strip()
                if link_text and link_text.lower() != "sponsored":
                    return link_text

            card_text = business_card.inner_text(timeout=self.config.timeout)
            visible_lines = [line.strip() for line in card_text.splitlines() if line.strip()]
            return next(
                (
                    line
                    for line in visible_lines
                    if line.lower() != "sponsored" and any(character.isalnum() for character in line)
                ),
                None,
            )
        except (PlaywrightError, PlaywrightTimeoutError):
            return None

    def _extract_place_href_from_card(self, business_card: Locator) -> str | None:
        """Extract the Google Maps place href from a result card when available."""

        try:
            business_card_link = business_card.locator(Selectors.BUSINESS_CARD_LINK).first
            if business_card_link.count() == 0:
                return None
            href = business_card_link.get_attribute("href")
        except (PlaywrightError, PlaywrightTimeoutError):
            return None
        return href.strip() if href else None

    def _scroll_results_to_top(self) -> None:
        """Return the results panel to the top before opening the first business."""

        page = self.browser_manager.page
        results_panel = self._results_panel

        if page is None:
            raise SearchError("Browser page is unavailable for resetting the results panel.")
        if results_panel is None:
            raise SearchError("Results panel is unavailable for resetting scroll position.")

        try:
            results_panel.evaluate("(element) => element.scrollTo({ top: 0, behavior: 'auto' })")
            page.wait_for_function(
                """
                (panel_selector) => {
                    const panel = document.querySelector(panel_selector);
                    return !!panel && panel.scrollTop === 0;
                }
                """,
                arg=Selectors.RESULTS_PANEL,
                timeout=self.config.navigation_timeout,
            )
            page.wait_for_timeout(self.config.scroll_delay * 1000)
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to reset the results panel to the top.") from error

    def _count_business_cards(self, log_card_preview: bool = True) -> int:
        """Count the currently loaded business cards inside the detected results panel."""

        results_panel = self._results_panel
        if results_panel is None:
            raise SearchError("Results panel is not available for business card counting.")

        try:
            self.logger.info("Locating business cards...")
            business_cards = results_panel.locator(Selectors.BUSINESS_CARD)
            business_card_count = business_cards.count()

            if business_card_count <= 0:
                raise SearchError("No business cards were found inside the results panel.")

            self.logger.info("Business cards found: %s", business_card_count)

            if log_card_preview:
                # TODO: Replace temporary business-name diagnostics with stable Google Maps Place URLs in a later phase.
                for index, business_name in enumerate(self._get_visible_business_names(), start=1):
                    self.logger.info("Card %s: %s", index, business_name)

            self.logger.info("Business card counting completed.")
            return business_card_count

        except SearchError:
            raise
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to count business cards inside the results panel.") from error

    def _scroll_results_once(self) -> None:
        """Scroll the results panel downward one visible panel height and wait for settling."""

        page = self.browser_manager.page
        results_panel = self._results_panel

        if page is None:
            raise SearchError("Browser page is not available for scrolling the results panel.")
        if results_panel is None:
            raise SearchError("Results panel is unavailable for scrolling.")

        try:
            panel_metrics = results_panel.evaluate(
                """
                (element) => ({
                    scrollTop: element.scrollTop,
                    clientHeight: element.clientHeight,
                })
                """
            )
            current_scroll_top = int(panel_metrics["scrollTop"])
            client_height = int(panel_metrics["clientHeight"])

            if client_height <= 0:
                raise SearchError("Results panel has an invalid clientHeight for scrolling.")

            self.logger.info("Scrolling results panel...")
            self.logger.info(
                "Current panel position before scroll | scrollTop=%s | clientHeight=%s",
                current_scroll_top,
                client_height,
            )

            results_panel.evaluate(
                "(element, scroll_delta) => element.scrollBy({ top: scroll_delta, behavior: 'auto' })",
                client_height,
            )

            page.wait_for_function(
                """
                ([panel_selector, previous_scroll_top]) => {
                    const panel = document.querySelector(panel_selector);
                    return !!panel && panel.scrollTop > previous_scroll_top;
                }
                """,
                arg=[Selectors.RESULTS_PANEL, current_scroll_top],
                timeout=self.config.navigation_timeout,
            )

            self.logger.info("Scroll completed.")
            self.logger.info("Waiting for additional businesses...")
            page.wait_for_timeout(self.config.scroll_delay * 1000)

        except SearchError:
            raise
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to scroll the Google Maps results panel.") from error

    def _process_businesses(self) -> list[ProcessedBusinessRecord]:
        """Stream business extraction while businesses are visible in the results panel."""

        self._processed_businesses = []
        self._discovered_businesses = []
        seen_businesses: set[str] = set()
        failed_businesses = 0
        no_change_counter = 0
        scroll_iteration = 0
        detail_check_timeout = min(1000, self.config.timeout)

        while no_change_counter < 3:
            scroll_iteration += 1
            self._recover_results_panel()
            visible_business_snapshots = self._deduplicate_business_snapshots(
                self._get_visible_business_snapshots()
            )
            new_businesses_on_screen = [
                business_snapshot
                for business_snapshot in visible_business_snapshots
                if self._build_business_identity(business_snapshot) not in seen_businesses
            ]

            self.logger.info("--------------------------------")
            self.logger.info("Current scroll iteration: %s", scroll_iteration)
            self.logger.info(
                "Number of new businesses found on that screen: %s",
                len(new_businesses_on_screen),
            )
            self.logger.info(
                "Number of businesses extracted so far: %s",
                len(self._processed_businesses),
            )

            if new_businesses_on_screen:
                no_change_counter = 0
            else:
                no_change_counter += 1
                self.logger.info("No-change counter: %s", no_change_counter)

            for business_snapshot in new_businesses_on_screen:
                business_name = business_snapshot["name"] or "Unknown Business"
                business_identity = self._build_business_identity(business_snapshot)
                seen_businesses.add(business_identity)
                self._discovered_businesses.append(business_name)
                business_opened = False

                self.logger.info("--------------------------------")
                self.logger.info(
                    "Processing discovered business %s",
                    len(self._discovered_businesses),
                )
                self.logger.info("Business: %s", business_name)

                try:
                    self._recover_results_panel()
                    self._open_business(
                        business_name=business_name,
                        place_href=business_snapshot["place_href"],
                    )
                    business_opened = True
                    self.logger.info("Extracting business details...")
                    extracted_business = ProcessedBusinessRecord(
                        self.extractor.extract(self.browser_manager.page)
                    )
                    self._processed_businesses.append(extracted_business)
                    self.logger.info("Extraction successful.")
                except (SearchError, PlaywrightError, PlaywrightTimeoutError):
                    failed_businesses += 1
                    self.logger.exception(
                        "Failed to process business '%s'. Continuing with the next business.",
                        business_name,
                    )
                finally:
                    if business_opened or self._is_business_detail_panel_open(
                        timeout=detail_check_timeout
                    ):
                        try:
                            self.logger.info("Returning to results...")
                            self._back_to_results()
                            self._wait_for_results_panel()
                        except SearchError:
                            self.logger.exception(
                                "Failed to restore the results panel after processing '%s'.",
                                business_name,
                            )
                    else:
                        try:
                            self._recover_results_panel()
                        except SearchError:
                            self.logger.exception(
                                "Results panel recovery failed after processing '%s'.",
                                business_name,
                            )

            if no_change_counter >= 3:
                self.logger.info("Stopping scrolling after three consecutive iterations with no new businesses.")
                break

            self.logger.info("Scrolling...")
            self._scroll_results_once()

        self.logger.info("--------------------------------")
        self.logger.info("Discovered Businesses: %s", len(self._discovered_businesses))
        self.logger.info("Successfully Processed: %s", len(self._processed_businesses))
        self.logger.info("Failed: %s", failed_businesses)
        self.logger.info("Exported Records: %s", len(self._processed_businesses))
        return self._processed_businesses

    def _recover_results_panel(self) -> Locator:
        """Ensure the Google Maps search results panel is available for processing."""

        page = self.browser_manager.page
        if page is None:
            raise SearchError("Browser page is unavailable while restoring the results panel.")

        try:
            if self._is_results_panel_ready():
                return self._wait_for_results_panel()

            back_button = page.locator(Selectors.BACK_BUTTON).first
            if back_button.count() > 0 and back_button.is_visible():
                self._back_to_results()
                return self._wait_for_results_panel()

            return self._wait_for_results_panel()
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Failed to restore the Google Maps results panel.") from error

    def _is_results_panel_ready(self) -> bool:
        """Return whether the search results panel is currently active and usable."""

        page = self.browser_manager.page
        if page is None:
            return False

        try:
            return bool(
                page.evaluate(
                    """
                    ([results_selector, detail_selector]) => {
                        const resultsPanel = document.querySelector(results_selector);
                        const detailPanel = document.querySelector(detail_selector);
                        const resultsVisible = !!resultsPanel && !!(resultsPanel.offsetWidth || resultsPanel.offsetHeight || resultsPanel.getClientRects().length);
                        const detailVisible = !!detailPanel && !!(detailPanel.offsetWidth || detailPanel.offsetHeight || detailPanel.getClientRects().length);
                        const resultsCount = resultsPanel ? resultsPanel.querySelectorAll('[role="article"]').length : 0;
                        return resultsVisible && !detailVisible && resultsCount > 0;
                    }
                    """,
                    [Selectors.RESULTS_PANEL, Selectors.DETAIL_PANEL],
                )
            )
        except PlaywrightError:
            return False

    def _build_business_identity(self, business_snapshot: dict[str, str | None]) -> str:
        """Build the stable identity used for duplicate protection."""

        place_href = business_snapshot["place_href"]
        business_name = business_snapshot["name"]
        if place_href:
            return place_href
        if business_name:
            return business_name
        raise SearchError("Business snapshot is missing both place href and name.")

    def _deduplicate_business_snapshots(
        self,
        business_snapshots: list[dict[str, str | None]],
    ) -> list[dict[str, str | None]]:
        """Deduplicate visible business snapshots using place href first, then name."""

        unique_snapshots: list[dict[str, str | None]] = []
        seen_snapshot_identities: set[str] = set()

        for business_snapshot in business_snapshots:
            business_identity = self._build_business_identity(business_snapshot)
            if business_identity in seen_snapshot_identities:
                continue
            seen_snapshot_identities.add(business_identity)
            unique_snapshots.append(business_snapshot)

        return unique_snapshots

    def _find_business_card(self, business_name: str, place_href: str | None = None) -> Locator:
        """Locate a currently visible business card by re-querying the results panel."""

        self._wait_for_results_panel()
        visible_business_card = self._find_visible_business_card(
            business_name=business_name,
            place_href=place_href,
        )
        if visible_business_card is None:
            raise SearchError(
                f"Business card for '{business_name}' is no longer visible in the current results panel."
            )
        return visible_business_card

    def _find_visible_business_card(
        self,
        business_name: str,
        place_href: str | None = None,
    ) -> Locator | None:
        """Return a currently visible business card matching the provided business name."""

        page = self.browser_manager.page
        results_panel = self._results_panel
        if page is None:
            raise SearchError("Browser page is unavailable for visible business lookup.")
        if results_panel is None:
            raise SearchError("Results panel is unavailable for visible business lookup.")

        if place_href:
            matching_cards = results_panel.locator(Selectors.BUSINESS_CARD).filter(
                has=page.locator(f'{Selectors.BUSINESS_CARD_LINK}[href="{place_href}"]')
            )
        else:
            matching_cards = results_panel.locator(Selectors.BUSINESS_CARD).filter(
                has_text=business_name
            )
        matching_count = matching_cards.count()

        for index in range(matching_count):
            candidate_card = matching_cards.nth(index)
            try:
                if candidate_card.is_visible():
                    return candidate_card
            except PlaywrightError:
                continue

        return None

    def _open_business(self, business_name: str, place_href: str | None = None) -> None:
        """Open a single discovered business from the results panel."""

        page = self.browser_manager.page

        if page is None:
            raise SearchError("Browser page is unavailable for opening a business.")

        attempt_labels = [
            "Attempt 1: Normal click",
            "Attempt 2: Retry click",
            "Attempt 3: JavaScript click",
            "Attempt 4: Keyboard Enter",
        ]

        for attempt_index, attempt_label in enumerate(attempt_labels, start=1):
            try:
                # On retries, navigate back to the results panel first.
                # Do NOT call this on attempt 1 — the caller already ensures the panel is ready,
                # and calling it here would reset any panel state the click may have triggered.
                if attempt_index > 1:
                    self._recover_results_panel()

                target_business_card = self._find_business_card(
                    business_name=business_name,
                    place_href=place_href,
                )
                target_business_card.scroll_into_view_if_needed(
                    timeout=self.config.navigation_timeout
                )
                target_business_card.wait_for(
                    state="visible",
                    timeout=self.config.navigation_timeout,
                )
                target_business_card.hover(timeout=self.config.navigation_timeout)

                business_card_link = target_business_card.locator(
                    Selectors.BUSINESS_CARD_LINK
                ).first
                if business_card_link.count() == 0:
                    raise SearchError(f"Business link for '{business_name}' could not be found.")

                business_card_link.scroll_into_view_if_needed(
                    timeout=self.config.navigation_timeout
                )
                business_card_link.wait_for(
                    state="visible",
                    timeout=self.config.navigation_timeout,
                )

                self.logger.info(attempt_label)

                if attempt_index in (1, 2):
                    business_card_link.click(timeout=self.config.navigation_timeout)
                elif attempt_index == 3:
                    business_card_link.evaluate("(element) => element.click()")
                else:
                    business_card_link.focus()
                    page.keyboard.press("Enter")

                # Allow Google Maps time to begin the panel transition before checking.
                page.wait_for_timeout(1500)

                if self._is_business_detail_panel_open(timeout=self.config.navigation_timeout):
                    self.logger.info("Business opened successfully.")
                    return
            except SearchError:
                if attempt_index == len(attempt_labels):
                    break
            except (PlaywrightError, PlaywrightTimeoutError):
                if attempt_index == len(attempt_labels):
                    break

        self.logger.error("Failed to open business after all retry methods.")
        raise SearchError(f"Failed to open business '{business_name}'.")

    def _is_business_detail_panel_open(self, timeout: int) -> bool:
        """Return whether the Google Maps business detail panel is visibly open."""

        page = self.browser_manager.page
        if page is None:
            return False

        try:
            page.wait_for_function(
                """
                (detail_selector) => {
                    const isVisible = (element) =>
                        !!element && !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);

                    const detailPanel = document.querySelector(detail_selector);
                    if (!isVisible(detailPanel)) return false;

                    // Confirm a business name heading has loaded inside the panel
                    const heading = detailPanel.querySelector('h1');
                    return !!heading && heading.textContent.trim().length > 0;
                }
                """,
                arg=Selectors.DETAIL_PANEL,
                timeout=timeout,
            )
            return True
        except (PlaywrightError, PlaywrightTimeoutError):
            return False

    def _back_to_results(self) -> None:
        """Return from the open business detail panel back to the search results."""

        page = self.browser_manager.page
        if page is None:
            raise SearchError("Browser page is unavailable for returning to the results.")

        try:
            self.logger.info("Attempting history navigation to close detail panel.")
            page.evaluate("window.history.back()")
            
            # Wait a small moment to let the history state pop before proceeding
            # to _wait_for_results_panel.
            page.wait_for_timeout(500)
                
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            self.logger.warning("History back failed. Attempting keyboard Escape.")
            page.keyboard.press("Escape")

    def _wait_for_results_panel(self) -> Locator:
        """Wait until the Google Maps search results panel is restored."""

        page = self.browser_manager.page
        if page is None:
            raise SearchError("Browser page is unavailable while waiting for results.")

        try:
            results_panel = page.locator(Selectors.RESULTS_PANEL).first
            results_panel.wait_for(
                state="visible",
                timeout=self.config.navigation_timeout,
            )
            page.wait_for_function(
                """
                (results_selector) => {
                    const resultsPanel = document.querySelector(results_selector);
                    const resultsVisible = !!resultsPanel && !!(resultsPanel.offsetWidth || resultsPanel.offsetHeight || resultsPanel.getClientRects().length);
                    const resultsCount = resultsPanel ? resultsPanel.querySelectorAll('[role="article"]').length : 0;
                    return resultsVisible && resultsCount > 0;
                }
                """,
                arg=Selectors.RESULTS_PANEL,
                timeout=self.config.navigation_timeout,
            )
            self._results_panel = results_panel
            self.logger.info("Results panel restored.")
            return results_panel
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            raise SearchError("Results panel did not reappear after returning.") from error

    def scroll_results(self) -> None:
        """Scroll the result panel to load additional businesses."""

        # TODO: Continuously scroll the results panel until limits are reached.
        self.logger.info("Result scrolling placeholder reached.")

    def open_business(self, business_card: Any) -> None:
        """Open a business detail view from a card element."""

        # TODO: Click the provided business card and wait for the detail panel.
        self.logger.debug("Business open placeholder reached for card=%s", business_card)

    def collect_business_cards(self) -> list[Any]:
        """Collect raw business card elements from the results panel."""

        # TODO: Query the DOM for all currently loaded business cards.
        self.logger.info("Business card collection placeholder reached.")
        return []

    def extract_business(self, business_card: Any) -> Business:
        """Extract a single business record from a raw business card reference."""

        # TODO: Open the business detail panel and delegate field parsing.
        self.logger.debug("Business extraction placeholder reached for card=%s", business_card)
        return self.extractor.extract_all(context=business_card)

    def run(self) -> list[ProcessedBusinessRecord]:
        """Execute the end-to-end scraping workflow and return processed records."""

        self.logger.info("Starting scraper workflow for keyword='%s'.", self.keyword)

        try:
            self.browser_manager.start()
            processed_businesses = self.search()
            self.logger.info(
                "Multi-business navigation verification completed successfully."
            )
            self.logger.info(
                "Returning %s processed business records to main.py",
                len(processed_businesses),
            )
            return processed_businesses
        finally:
            self.browser_manager.close()
