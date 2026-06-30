"""Centralized selector placeholders for future Playwright integration."""

from __future__ import annotations


class Selectors:
    """Store all DOM selectors in one place to avoid scattered hardcoding."""

    BUSINESS_CARD = '[role="article"]'
    BUSINESS_CARD_LINK = 'a[href*="/place/"]'
    DETAIL_PANEL = 'div[role="main"][aria-label]'
    DETAIL_PANEL_NAME = "h1.DUwDvf.lfPIob"
    DETAIL_PANEL_HEADER = "div.lMbq3e"
    BUSINESS_NAME = DETAIL_PANEL_NAME
    PHONE = 'button[data-item-id^="phone:tel:"]'
    ADDRESS = '[data-item-id="address"]'
    WEBSITE = 'a[data-item-id="authority"]'
    CATEGORY = "button.DkEaL"
    RATING = 'span.ZkP5Je[role="img"][aria-label*="stars"]'
    # Review count: try jsaction attribute (stable) and the aria-label pattern on the rating block
    REVIEWS = 'button[jsaction*="pane.rating.moreReviews"]'
    REVIEWS_ARIA = '[aria-label*="review" i][role="button"]'
    REVIEWS_LEGACY = 'button[aria-label*="review" i]:not([aria-label*="Write" i])'
    HOURS = 'button[aria-label*="Copy open hours"]'
    BACK_BUTTON = 'button[jsaction*="pane.place.backToList"], button[aria-label="Back"], button[aria-label="Close"]'
    RESULTS_PANEL = 'div[role="feed"]'
    RESULT_PANEL = RESULTS_PANEL
    SEARCH_BOX = 'input[name="q"][role="combobox"]'
    SEARCH_BUTTON = "TODO_SEARCH_BUTTON_SELECTOR"
