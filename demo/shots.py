"""Capture light-mode screenshots of every page for the product walkthrough PDF."""

import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

WORK = Path(os.environ.get("GRIDSHIFT_DEMO_WORK", "E:/demos/gridshift"))
OUT = WORK / "walkthrough" / "shots"
BASE = "http://127.0.0.1:8100"
THEME = sys.argv[1] if len(sys.argv) > 1 else "light"
ADMIN = ("Sharan Kumar", "sharan@cementworks.example", "Laegerdorf-2026!")
ANNA = ("Anna Weber", "anna.weber@cementworks.example", "Schicht-Plan-7")
INIT = f"try {{ localStorage.setItem('gridshift-theme', '{THEME}') }} catch (e) {{}}"


def card(page, title: str):
    return page.locator("div.rounded-xl", has=page.get_by_role("heading", name=title, exact=True)).last


def card_re(page, pattern: str):
    return page.locator("div.rounded-xl", has=page.get_by_role("heading", name=re.compile(pattern))).last


async def settle(page, seconds: float = 2.2) -> None:
    await page.wait_for_load_state("networkidle")
    await page.mouse.move(5, 895)
    await page.wait_for_timeout(seconds * 1000)


async def view(page, name: str) -> None:
    await settle(page)
    await page.screenshot(path=str(OUT / f"{name}.png"))


async def element(page, loc, name: str, max_h: float | None = None) -> None:
    await loc.scroll_into_view_if_needed()
    await settle(page, 1.6)
    box = await loc.bounding_box()
    if max_h and box["height"] > max_h:
        await page.evaluate("y => window.scrollBy(0, y)", box["y"] - 70)
        await page.wait_for_timeout(500)
        box = await loc.bounding_box()
        await page.screenshot(path=str(OUT / f"{name}.png"), clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": max_h})
    else:
        await loc.screenshot(path=str(OUT / f"{name}.png"))


async def go(page, path: str) -> None:
    await page.goto(BASE + path, wait_until="networkidle")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--hide-scrollbars"])
        opts = {"locale": "en-GB", "timezone_id": "Europe/Berlin", "device_scale_factor": 2}
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, **opts)
        await ctx.add_init_script(INIT)
        page = await ctx.new_page()
        page.set_default_timeout(60000)

        await go(page, "/")
        await page.get_by_label("Your name").fill(ADMIN[0])
        await page.get_by_label("Work email").fill(ADMIN[1])
        await page.get_by_label("Password", exact=True).fill(ADMIN[2])
        await page.get_by_label("Confirm password").fill(ADMIN[2])
        await page.get_by_role("button", name="Create admin account").click()
        await page.get_by_role("button", name="Create first plan").click()
        await page.get_by_text("Saved this week").wait_for(timeout=240000)

        await go(page, "/users")
        await page.get_by_role("button", name="Invite user").click()
        dialog = page.get_by_role("dialog")
        await dialog.get_by_label("Email").fill(ANNA[1])
        await dialog.get_by_label("Name").fill(ANNA[0])
        await dialog.get_by_label("Role").click()
        await page.get_by_role("option", name="Planner").click()
        await dialog.get_by_role("button", name="Send invitation").click()
        await page.wait_for_timeout(1500)
        await page.get_by_role("dialog").get_by_role("button", name="Done").click()

        await go(page, "/")
        await view(page, "02-overview-top")
        await element(page, card_re(page, r"peak charge$"), "03-overview-peak")
        await element(page, card(page, "Daily energy cost"), "04-overview-daily")
        await element(page, card(page, "Tomorrow"), "05-overview-tomorrow")
        await element(page, card(page, "7-day outlook"), "06-overview-outlook")
        await element(page, card(page, "Price paid per machine"), "07-overview-machines")
        await page.evaluate("window.scrollTo(0, 0)")
        export = page.get_by_role("button", name="Export")
        b = await export.bounding_box()
        await export.click()
        menu = page.get_by_role("menu")
        await menu.wait_for()
        await page.wait_for_timeout(600)
        m = await menu.bounding_box()
        x0, y0 = min(m["x"], b["x"]) - 24, b["y"] - 16
        await page.screenshot(path=str(OUT / "21-export-menu.png"), clip={"x": x0 - 220, "y": y0, "width": m["x"] + m["width"] + 24 - x0 + 220, "height": m["y"] + m["height"] + 20 - y0})
        await page.keyboard.press("Escape")

        await go(page, "/forecast")
        await view(page, "08-forecast-top")
        tabs = page.locator("div.rounded-xl", has=page.get_by_role("tablist")).first
        await element(page, tabs, "09b-price-chart")
        await page.get_by_role("tab", name=re.compile("^Sunlight")).click()
        await element(page, tabs, "09b-sunlight-chart")
        await page.get_by_role("tab", name=re.compile("^Wind")).click()
        await element(page, tabs, "10b-wind-chart")
        await page.get_by_role("tab", name=re.compile("^Price")).click()
        await element(page, card(page, "On-site generation and factory load"), "11-forecast-load")
        await element(page, card(page, "Battery"), "12-forecast-battery")

        await go(page, "/schedule")
        await element(page, card(page, "Machine schedule"), "13b-schedule-gantt")
        await element(page, card(page, "Run blocks by day"), "14-schedule-blocks", max_h=900)

        await go(page, "/email")
        await view(page, "15-email")
        await go(page, "/site")
        await view(page, "16-site-top")
        await element(page, card(page, "Machines"), "17-site-machines")
        await go(page, "/guide")
        await view(page, "18-guide")
        await go(page, "/users")
        await view(page, "19-users")
        await go(page, "/audit")
        await view(page, "20-audit")

        phone = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, storage_state=await ctx.storage_state(), **opts)
        await phone.add_init_script(INIT)
        mobile = await phone.new_page()
        await go(mobile, "/")
        await view(mobile, "22-mobile")

        anon = await browser.new_context(viewport={"width": 1440, "height": 900}, **opts)
        await anon.add_init_script(INIT)
        login = await anon.new_page()
        await go(login, "/login")
        await view(login, "01-signin")
        await browser.close()
    print("shots in", OUT)


if __name__ == "__main__":
    asyncio.run(main())
