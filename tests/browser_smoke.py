"""Headless browser acceptance check for the Agent/Bio static site switch."""

from __future__ import annotations

import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("DAB_BASE_URL", "http://127.0.0.1:8080")
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main() -> None:
    console_errors: list[str] = []
    payload = json.loads((Path(__file__).resolve().parents[1] / "docs" / "bio" / "data" / "index.json").read_text())
    total = payload["total"]
    main_entries = payload["entries"]
    methodology_count = sum(entry["contribution_type"] == "methodology" for entry in main_entries)
    experiment_count = sum(entry["topic"] == "experiment_agent" for entry in main_entries)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME_PATH)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.get_by_role("link", name="Bio & Medical").click()
        page.wait_for_url(f"{BASE_URL}/bio/")
        page.wait_for_selector(".bio-row")

        assert page.locator(".hero__stats b").first.text_content() == str(total)
        assert page.locator(".bio-row").count() == min(24, len(main_entries))
        assert page.get_by_role("button", name="P0", exact=True).count() == 0
        assert page.get_by_text("Watchlist", exact=True).count() == 0
        page.screenshot(path="/private/tmp/daily-agent-benchmarks-bio-home.png", full_page=True)

        page.get_by_role("button", name="Methodology", exact=True).click()
        assert page.locator(".bio-row").count() == min(24, methodology_count)

        page.get_by_role("button", name="All", exact=True).nth(0).click()
        page.locator("[data-topic='experiment_agent']").click()
        assert page.locator(".bio-row").count() == min(24, experiment_count)

        page.locator("[data-topic='all']").click()
        page.locator("#bio-q").fill("LAB-Bench")
        page.wait_for_timeout(250)
        assert page.locator(".bio-row").count() >= 1
        assert "LAB-Bench" in page.locator(".bio-row h3").first.text_content()

        page.get_by_role("button", name="中文").click()
        assert "生物与医学" in page.locator("#bio-hero h1").text_content()

        page.locator(".bio-row h3 a").first.click()
        page.wait_for_selector(".evidence-card")
        assert page.locator(".bio-definition").is_visible()
        assert page.get_by_role("link", name="Agent").is_visible()

        page.screenshot(path="/private/tmp/daily-agent-benchmarks-bio-detail.png", full_page=True)
        browser.close()

    if console_errors:
        raise AssertionError(f"browser console errors: {console_errors}")


if __name__ == "__main__":
    main()
