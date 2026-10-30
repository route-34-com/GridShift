"""Drive the GridShift dashboard through the demo story and capture timestamped frames."""

import asyncio
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from email import message_from_bytes
from email.policy import default
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path

import pypdfium2
from playwright.async_api import async_playwright

HERE = Path(__file__).parent
WORK = Path(os.environ.get("GRIDSHIFT_DEMO_WORK", "E:/demos/gridshift"))
APP = WORK / "app"
FRAMES = WORK / "frames"
MAIL = APP / "data" / "mail"
BASE = "http://127.0.0.1:8100"
THEME = os.environ.get("GRIDSHIFT_DEMO_THEME", "dark")
VIEW = {"width": 1600, "height": 900}
SCALE = 1.2
NARR = json.loads((WORK / "narration.json").read_text(encoding="utf-8"))
LINES, FIG = NARR["lines"], NARR["figures"]
ADMIN = ("Sharan Kumar", "sharan@cementworks.example", "Laegerdorf-2026!")
ANNA = ("Anna Weber", "anna.weber@cementworks.example", "Schicht-Plan-7")
MANAGER = "energy.manager@example.com"

frames: list[tuple[float, str]] = []
marks: list[tuple[str, float]] = []
report_pages: list[bytes] = []


def now() -> float:
    return time.time()


async def sleep(seconds: float) -> None:
    await asyncio.sleep(max(0.0, seconds))


@asynccontextmanager
async def say(key: str, tail: float = 0.45):
    start = now()
    marks.append((key, start))
    yield
    await sleep(start + LINES[key]["dur"] + tail - now())


def mailbox_html(to: str, open_index: int | None, highlight: int | None) -> str:
    mails = []
    for path in sorted(MAIL.glob("*.eml")):
        msg = message_from_bytes(path.read_bytes(), policy=default)
        if to.lower() not in str(msg["To"]).lower():
            continue
        body = msg.get_body(preferencelist=("html", "plain"))
        mails.append({"from": str(msg["From"]), "subject": str(msg["Subject"]), "date": parsedate_to_datetime(msg["Date"]) if msg["Date"] else None, "html": body.get_content() if body else ""})
    mails.reverse()
    rows = []
    for i, m in enumerate(mails):
        sender = html.escape(m["from"].split("<")[0].strip() or m["from"])
        when = m["date"].astimezone().strftime("%H:%M") if m["date"] else ""
        cls = "row hl" if i == highlight else "row"
        rows.append(f'<a class="{cls}" id="mail{i}" href="/__mailbox?to={to}&open={i}"><b>{sender}</b><span>{html.escape(m["subject"])}</span><em>{when}</em></a>')
    viewer = ""
    if open_index is not None and open_index < len(mails):
        doc = mails[open_index]["html"].replace("<head>", '<head><base target="_top">', 1)
        if "<base" not in doc:
            doc = '<base target="_top">' + doc
        viewer = f'<div class="open"><h2>{html.escape(mails[open_index]["subject"])}</h2><p class="meta">From {html.escape(mails[open_index]["from"])} · To {html.escape(to)}</p><iframe id="mail" srcdoc="{html.escape(doc, quote=True)}"></iframe></div>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Mailbox</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#eef1f0;font-family:'IBM Plex Sans',system-ui,sans-serif;color:#142019}}
.top{{background:#1f2522;color:#fff;padding:14px 28px;font-size:15px;display:flex;gap:14px;align-items:center}}
.top b{{font-size:17px}} .top span{{opacity:.75}}
.wrap{{max-width:1180px;margin:26px auto;padding:0 20px}}
.list{{background:#fff;border-radius:12px;border:1px solid #dfe5e2;overflow:hidden}}
.row{{display:grid;grid-template-columns:200px 1fr 70px;gap:18px;padding:16px 22px;border-bottom:1px solid #eef1f0;text-decoration:none;color:inherit;font-size:15px}}
.row:last-child{{border-bottom:0}} .row span{{color:#33413a}} .row em{{font-style:normal;color:#55645d;text-align:right}}
.row.hl{{background:#fffbea}}
.open{{margin-top:22px;background:#fff;border-radius:12px;border:1px solid #dfe5e2;padding:22px 26px}}
.open h2{{margin:0 0 4px;font-size:20px}} .meta{{margin:0 0 16px;color:#55645d;font-size:14px}}
iframe{{width:100%;height:1500px;border:0;border-radius:8px;background:#f4f6f5}}
</style></head><body><div class="top"><b>✉ Mailbox</b><span>{html.escape(to)}</span></div>
<div class="wrap"><div class="list">{''.join(rows) or '<p style="padding:20px">No mail yet.</p>'}</div>{viewer}</div></body></html>"""


def report_html() -> str:
    pages = "".join(f'<img src="/__report/p{i}.png">' for i in range(len(report_pages)))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Plan report</title>
<style>body{{margin:0;background:#525659;font-family:system-ui,sans-serif}}
.bar{{position:sticky;top:0;background:#323639;color:#eee;padding:12px 24px;font-size:14px;z-index:5}}
img{{display:block;width:1180px;margin:24px auto;box-shadow:0 6px 24px rgba(0,0,0,.4);background:#fff}}</style></head>
<body><div class="bar">GridShift plan report.pdf · {len(report_pages)} pages</div>{pages}</body></html>"""


async def route_mailbox(route):
    from urllib.parse import parse_qs, urlparse

    q = parse_qs(urlparse(route.request.url).query)
    to = q.get("to", [""])[0]
    open_index = int(q["open"][0]) if "open" in q else None
    highlight = int(q["hl"][0]) if "hl" in q else open_index
    await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=mailbox_html(to, open_index, highlight))


async def route_report(route):
    url = route.request.url
    if url.endswith(".png"):
        index = int(url.rsplit("/p", 1)[1].split(".")[0])
        await route.fulfill(status=200, content_type="image/png", body=report_pages[index])
    else:
        await route.fulfill(status=200, content_type="text/html; charset=utf-8", body=report_html())


class Director:
    """Cursor, focus ring, callouts and captions over the live page."""

    def __init__(self, page, cdp):
        self.page, self.cdp = page, cdp

    async def screencast(self) -> None:
        try:
            await self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})
        except Exception:
            pass

    async def goto(self, path: str) -> None:
        await self.page.goto(BASE + path, wait_until="networkidle")
        await self.screencast()
        await sleep(0.4)

    async def js(self, script: str, arg=None):
        return await self.page.evaluate(script, arg)

    async def card(self, kicker: str, title: str, sub: str = "", logo: bool = False) -> None:
        await self.js("([k,t,s,l]) => { __demo.hideCursor(true); __demo.clear(); __demo.caption(''); __demo.card(k,t,s,l) }", [kicker, title, sub, logo])
        await sleep(0.7)

    async def uncard(self) -> None:
        await self.js("() => { __demo.hideCard(); __demo.hideCursor(false) }")
        await sleep(0.7)

    async def caption(self, text: str = "") -> None:
        await self.js("t => __demo.caption(t)", text)

    async def clear(self) -> None:
        await self.js("() => __demo.clear()")
        await sleep(0.3)

    async def center(self, loc) -> tuple[float, float]:
        box = await loc.bounding_box()
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    async def reveal(self, loc, block: str = "center") -> None:
        await loc.evaluate(f"el => el.scrollIntoView({{behavior:'smooth', block:'{block}'}})")
        await sleep(0.9)

    async def scroll_to(self, top: float) -> None:
        await self.js("y => window.scrollTo({top: y, behavior: 'smooth'})", top)
        await sleep(1.0)

    async def move(self, x: float, y: float, ms: int = 700) -> None:
        await self.js("([x,y,ms]) => __demo.move(x,y,ms)", [x, y, ms])
        await self.page.mouse.move(x, y, steps=8)
        await sleep(ms / 1000 + 0.08)

    async def hover(self, loc, dx: float = 0, dy: float = 0) -> None:
        x, y = await self.center(loc)
        await self.move(x + dx, y + dy)

    async def click(self, loc, settle: float = 0.5) -> None:
        await loc.scroll_into_view_if_needed()
        x, y = await self.center(loc)
        await self.move(x, y)
        await self.js("() => __demo.click()")
        await self.page.mouse.click(x, y)
        await sleep(settle)

    async def type(self, loc, text: str, delay: int = 55) -> None:
        await self.click(loc, 0.2)
        await loc.press_sequentially(text, delay=delay)
        await sleep(0.25)

    async def focus(self, loc, text: str = "", side: str = "auto", dim: bool = True, pad: int = 6, width: int = 340) -> None:
        box = await loc.bounding_box()
        await self.focus_rect(box, text, side, dim, pad, width)

    async def focus_rect(self, box: dict, text: str = "", side: str = "auto", dim: bool = True, pad: int = 6, width: int = 340) -> None:
        rect = {"x": box["x"] - pad, "y": box["y"] - pad, "w": box["width"] + 2 * pad, "h": box["height"] + 2 * pad}
        await self.js("([r,t,o]) => __demo.focus(null, t, Object.assign(o, {rect: r}))", [rect, text, {"side": side, "dim": dim, "width": width}])
        await sleep(0.6)

    def card_of(self, title: str):
        return self.page.locator("div.rounded-xl", has=self.page.get_by_role("heading", name=title, exact=True)).last

    def card_re(self, pattern: str):
        return self.page.locator("div.rounded-xl", has=self.page.get_by_role("heading", name=re.compile(pattern))).last

    async def nav(self, label: str) -> None:
        await self.clear()
        await self.click(self.page.get_by_role("navigation", name="Main").get_by_role("link", name=label, exact=True).first, 0.2)
        await sleep(1.4)


def union(*boxes) -> dict:
    x0 = min(b["x"] for b in boxes)
    y0 = min(b["y"] for b in boxes)
    x1 = max(b["x"] + b["width"] for b in boxes)
    y1 = max(b["y"] + b["height"] for b in boxes)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def daily_job() -> subprocess.Popen:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen([sys.executable, "-m", "backend.jobs"], cwd=APP, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


async def story(d: Director) -> None:
    page = d.page
    order, order_base = round(FIG["order"]), round(FIG["order_base"])

    await d.card("", "GridShift", "Smart energy scheduling for industry", True)
    await d.screencast()
    async with say("intro", 0.8):
        pass
    await d.card("STEP 1", "First start", "The first account is created on the computer running GridShift.")
    async with say("s1", 1.2):
        pass
    await d.uncard()

    async with say("setup"):
        await d.caption("The very first time GridShift is opened, it asks for the admin account")
        await d.focus(page.get_by_role("heading", name="Create the admin account"), "Only possible on the computer where GridShift is installed, so nobody else can take over a new installation.", "right", width=330, pad=10)
        await sleep(2.0)
        await d.clear()
        await d.type(page.get_by_label("Your name"), ADMIN[0])
        await d.type(page.get_by_label("Work email"), ADMIN[1], 40)
    async with say("setup_pw"):
        await d.type(page.get_by_label("Password", exact=True), ADMIN[2], 80)
        await d.focus(page.get_by_role("list", name="Password rules"), "Rules are checked as you type.", "right", dim=False)
        await d.clear()
        await d.type(page.get_by_label("Confirm password"), ADMIN[2], 45)
    await d.caption("")
    await d.click(page.get_by_role("button", name="Create admin account"), 0.3)
    await page.wait_for_url(BASE + "/")
    await page.get_by_role("button", name="Create first plan").wait_for()
    await sleep(0.8)

    await d.card("STEP 2", "The first plan", "Prices, weather and the plant's own load, turned into a 7-day plan.")
    async with say("s2", 1.0):
        pass
    await d.uncard()
    first = page.get_by_role("button", name="Create first plan")
    async with say("empty", 0.2):
        await d.focus(page.locator("header").filter(has=page.get_by_text("Germany")).first, "Site, sample data, and the time in Germany.", "bottom", dim=False, width=360)
        await sleep(3.5)
        await d.focus(first, "No plan yet. One click creates it.", "right")
    async with say("run"):
        await d.clear()
        await d.click(first, 0.2)
        await d.caption("Fetching day-ahead prices and the weather forecast, then optimizing…")
        await page.get_by_text("Saved this week").wait_for(timeout=240000)
        await d.caption("")
        await sleep(1.0)

    await d.card("STEP 3", "The overview", "Cost, savings, peak and renewable use for the next 7 days.")
    async with say("s3", 1.0):
        pass
    await d.uncard()
    async with say("coverage"):
        await d.focus(d.card_of("Price data in this plan"), "Real market prices, then estimates, and when the next prices come out.", "bottom", width=420)
    stats = page.locator("div.grid", has=page.get_by_text("Saved this week")).first
    async with say("stats"):
        await d.clear()
        await d.reveal(stats)
        await d.focus(stats, f"€{FIG['savings_eur']:,.0f} saved this week, {FIG['savings_pct']:.0%} below running every machine as early as possible.", "bottom", width=420)
        await sleep(5.0)
        await d.focus(page.locator("div.rounded-xl", has=page.get_by_text("On-site renewable share")).last, "Share of energy from the site's own solar and wind.", "bottom")
    peak = d.card_re(r"peak charge$")
    async with say("peak"):
        await d.clear()
        await d.reveal(peak)
        await d.focus(peak, "This year's 15-minute record, from meter data. The plan stays under it.", "bottom", width=400)
    chart = d.card_of("Daily energy cost")
    async with say("chart"):
        await d.clear()
        await d.reveal(chart)
        await d.focus(chart, "GridShift plan vs. run-as-needed, every day of the week.", "right", dim=False)
        await d.clear()
        box = await chart.bounding_box()
        for fx in (0.25, 0.48, 0.7):
            await d.move(box["x"] + box["width"] * fx, box["y"] + box["height"] * 0.62, 600)
            await sleep(0.9)
        await d.move(box["x"] + box["width"] + 60, box["y"] - 30, 600)
    async with say("tomorrow"):
        await d.focus(d.card_of("Tomorrow"), "Tomorrow's cost, grid price, outlook, battery plan and data sources.", "left")
    outlook = d.card_of("7-day outlook")
    async with say("outlook"):
        await d.clear()
        await d.reveal(outlook)
        await d.focus(outlook, "Weather-driven view of the week. Days 2–7 use estimated prices.", "top", width=420)
    table = d.card_of("Price paid per machine")
    async with say("machines"):
        await d.clear()
        await d.reveal(table)
        row = table.locator("tr", has=page.get_by_text("Special order CEM III/A grinding"))
        await d.focus(row, f"Special order pays €{order}/MWh instead of €{order_base}/MWh.", "top", width=360)
    await d.clear()
    await d.scroll_to(0)

    await d.nav("Forecast")
    await d.card("STEP 4", "The forecast", "Hourly prices, weather, on-site output, plant load and battery.")
    async with say("s4", 1.0):
        pass
    await d.uncard()
    tabs = page.locator("div.rounded-xl", has=page.get_by_role("tablist")).first
    async with say("price"):
        await d.reveal(tabs)
        await d.focus(tabs, "Now, already past, published, estimated, and when the next prices come out.", "top", dim=False, width=420)
        await d.clear()
        box = await page.locator("#forecast-panel").bounding_box()
        for fx in (0.08, 0.2, 0.55):
            await d.move(box["x"] + box["width"] * fx, box["y"] + box["height"] * 0.55, 700)
            await sleep(1.2)
        await d.move(box["x"] + box["width"] * 0.6, box["y"] - 60, 600)
    async with say("weather"):
        await d.reveal(tabs)
        await d.click(page.get_by_role("tab", name=re.compile("^Sunlight")), 1.0)
        await sleep(2.6)
        await d.click(page.get_by_role("tab", name=re.compile("^Wind")), 1.0)
        await sleep(2.4)
        await d.click(page.get_by_role("tab", name=re.compile("^Price")), 0.5)
    energy = d.card_of("On-site generation and factory load")
    async with say("energy"):
        await d.reveal(energy)
        await d.focus(energy, "Red line: this year's peak record. Grid draw stays under it.", "top", dim=False, width=380)
        await d.clear()
        box = await energy.bounding_box()
        await d.move(box["x"] + box["width"] * 0.37, box["y"] + box["height"] * 0.55, 800)
        await sleep(1.5)
    battery = d.card_of("Battery")
    async with say("battery"):
        await d.reveal(battery)
        await d.focus(battery, "Charges on surplus or cheap hours, discharges at the peaks.", "top", dim=False)
        await d.clear()
        box = await battery.bounding_box()
        await d.move(box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.55, 800)
    await d.scroll_to(0)

    await d.nav("Schedule")
    await d.card("STEP 5", "The machine schedule", "When each flexible machine runs over the next 7 days, and why.")
    async with say("s5", 1.0):
        pass
    await d.uncard()
    strips = union(await page.get_by_role("img", name="Hourly grid price from cheap (green) to expensive (red)").bounding_box(), await page.get_by_role("img", name="Hourly on-site renewable output").bounding_box())
    async with say("gantt"):
        await d.focus_rect(strips, "Grid price, cheap (green) to expensive (red), and on-site solar + wind below.", "bottom", width=400)
        await sleep(3.5)
    async with say("hover"):
        await d.clear()
        for name, nth in (("Special order CEM III/A grinding", 1), ("Cement mill 1 (ball mill)", 4), ("Limestone crusher (quarry)", 2)):
            await d.hover(page.locator(f"button[aria-label^='{name}']").nth(nth))
            await sleep(2.4)
        await d.move(800, 120)
    async with say("baseline"):
        await d.click(page.get_by_role("radio", name="Run-as-needed"), 0.8)
        await d.focus(d.card_of("Machine schedule"), "Run-as-needed: everything starts as early as allowed, whatever the price.", "bottom", dim=False, width=380)
        await sleep(2.0)
        await d.clear()
        await d.click(page.get_by_role("radio", name="GridShift plan"), 0.6)
    blocks = d.card_of("Run blocks by day")
    async with say("blocks"):
        await d.reveal(blocks, "start")
        await d.focus(blocks.locator("div.grid > div").first, "Each block with its time and reason.", "right", dim=False)
    await d.clear()
    await d.scroll_to(0)

    await d.nav("Site & machines")
    await d.card("STEP 6", "Site and machines", "The plant, its machines and the history the planner learns from.")
    async with say("s6", 1.0):
        pass
    await d.uncard()
    async with say("site"):
        await d.focus(d.card_re(r"peak charge$"), "Peak record from 15-minute meter data.", "bottom", width=360)
        await sleep(2.5)
        specs = page.locator("div.grid", has=page.get_by_role("heading", name="Solar", exact=True)).first
        await d.reveal(specs)
        await d.focus(specs, "Solar, wind turbine, battery and grid connection with its fees.", "top", width=380)
    async with say("machines_cfg"):
        machines = d.card_of("Machines")
        await d.clear()
        await d.reveal(machines)
        await d.focus(machines, "Always on, daily quota or deadline job, with a shortest run.", "top", width=380)
    await d.clear()
    await d.scroll_to(0)
    switch = page.get_by_role("switch", name="Sample data")
    async with say("own"):
        await d.focus(switch, "Switch sample data off to set up your own plant.", "right", dim=False)
        await sleep(1.2)
        await d.clear()
        await d.click(switch, 0.2)
        await page.get_by_role("heading", name="Set up your site").wait_for()
        await d.screencast()
        await sleep(0.8)
        setup = d.card_of("Set up your site")
        await d.focus(setup, "Site details, machines, a week of load history. Meter data optional.", "bottom", width=420)
        await sleep(4.0)
        await d.clear()
        await d.click(page.get_by_role("button", name="Add site details"), 1.2)
        await sleep(2.5)
        await page.keyboard.press("Escape")
        await sleep(0.6)
        await d.click(page.get_by_role("button", name="Add machine").first, 1.2)
        await sleep(2.5)
        await page.keyboard.press("Escape")
        await sleep(0.6)
    async with say("back"):
        await d.click(page.get_by_role("switch", name="Sample data"), 0.2)
        await page.get_by_text("You're looking at the Holcim sample").wait_for()
        await d.screencast()
        await sleep(0.6)

    await d.nav("Daily email")
    await d.card("STEP 7", "The daily email", "The plan lands in the plant team's inbox every afternoon.")
    async with say("s7", 1.0):
        pass
    await d.uncard()
    async with say("email"):
        await d.focus(d.card_of("Daily plan email"), "Sent after each daily run, once tomorrow's prices are out.", "bottom")
        await d.clear()
        await d.scroll_to(420)
        await sleep(1.2)
        await d.scroll_to(900)
    job = daily_job()
    async with say("replan"):
        await d.scroll_to(0)
        button = page.get_by_role("button", name="Re-plan now")
        await d.focus(button, "Re-plan with the latest prices and weather.", "bottom", dim=False)
        await d.clear()
        await d.click(button, 0.3)
        await d.caption("Re-planning…")
        await sleep(1.0)
        await page.get_by_role("button", name="Re-plan now").wait_for(timeout=240000)
        await d.caption("")
    async with say("job"):
        await d.caption("Meanwhile, at 13:30 the scheduled daily job runs on the server…")
        await asyncio.to_thread(job.wait)
    await page.route("**/__mailbox*", route_mailbox)
    await d.goto(f"/__mailbox?to={MANAGER}&hl=0")
    await d.caption("…and the plan arrives in the energy manager's inbox")
    async with say("inbox"):
        await d.focus(page.locator("#mail0"), "The daily plan, with tomorrow's cost and the week's savings in the subject.", "bottom", width=400)
        await sleep(1.5)
        await d.clear()
        await d.caption("")
        await d.click(page.locator("#mail0"), 0.2)
        await page.wait_for_load_state("networkidle")
        await d.screencast()
        await sleep(1.5)
        await d.scroll_to(260)
        await sleep(2.5)
        await d.scroll_to(780)
        await sleep(2.5)
        await d.scroll_to(1250)

    await d.goto("/")
    await d.nav("Users")
    await d.card("STEP 8", "Users and access", "Invite your team by email. Each person's role decides what they can see and change.")
    async with say("s8", 1.0):
        pass
    await d.uncard()
    async with say("roles"):
        await d.click(page.get_by_role("button", name="Invite user"), 0.8)
        role = page.get_by_role("dialog").get_by_label("Role")
        await d.focus(role.locator("xpath=.."), "Admin, Planner or Viewer.", "right")
        await d.click(role, 0.6)
        for name in ("Admin", "Viewer"):
            await d.hover(page.get_by_role("option", name=name))
            await sleep(1.0)
        await d.click(page.get_by_role("option", name="Planner"), 1.2)
    async with say("invite"):
        await d.clear()
        dialog = page.get_by_role("dialog")
        await d.type(dialog.get_by_label("Email"), ANNA[1], 40)
        await d.type(dialog.get_by_label("Name"), ANNA[0])
        await d.focus(dialog.get_by_role("button", name="Send invitation"), "Sends a single-use link by email.", "top", dim=False)
        await d.clear()
        await d.click(dialog.get_by_role("button", name="Send invitation"), 1.2)
    await sleep(1.0)
    await d.click(page.get_by_role("dialog").get_by_role("button", name="Done"), 0.6)
    await d.goto(f"/__mailbox?to={ANNA[1]}&hl=0")
    await d.caption("Meanwhile, in Anna's inbox…")
    async with say("invite_mail"):
        await d.focus(page.locator("#mail0"), "The invitation from GridShift has arrived.", "bottom")
        await d.clear()
        await d.click(page.locator("#mail0"), 0.2)
        await page.wait_for_load_state("networkidle")
        await d.screencast()
        link = page.frame_locator("#mail").get_by_role("link").first
        await d.focus(link, "Single-use link, valid for 7 days.", "right")
    await d.caption("")
    await d.clear()
    await d.click(link, 0.3)
    await page.wait_for_url("**/invite**")
    await page.get_by_role("button", name="Activate account").wait_for()
    await d.screencast()
    await sleep(0.8)
    async with say("accept"):
        await d.focus(page.get_by_role("heading", name="Join GridShift"), "Anna sets up her own account.", "right")
        await d.clear()
        name = page.get_by_label("Your name")
        if not await name.input_value():
            await d.type(name, ANNA[0])
        await d.type(page.get_by_label("Password", exact=True), ANNA[2], 70)
        await d.type(page.get_by_label("Confirm password"), ANNA[2], 40)
        await d.click(page.get_by_role("button", name="Activate account"), 0.3)
        await page.get_by_text("Saved this week").wait_for()
        await sleep(0.8)
    async with say("anna"):
        await d.focus(page.locator("aside nav"), "Planners see every plan and can re-plan. No Admin section.", "right", width=330)
        await sleep(1.0)
        await d.focus(page.locator("aside").get_by_role("button").filter(has_text="planner"), "Signed in as Anna, planner.", "right", dim=False)
    await d.clear()
    await d.click(page.locator("aside").get_by_role("button").filter(has_text="planner"), 0.5)
    await d.click(page.get_by_role("menuitem", name="Sign out"), 0.3)
    await page.wait_for_url("**/login")
    await d.screencast()
    await d.caption("Back to Sharan, the admin")
    async with say("login"):
        await d.type(page.get_by_label("Email"), ADMIN[1], 40)
        await d.type(page.get_by_label("Password", exact=True), "Laegerdorf-2025", 70)
        await d.click(page.get_by_role("button", name="Sign in"), 1.0)
        await page.locator("form [role=alert]").wait_for()
        await sleep(0.4)
        await d.focus(page.locator("form [role=alert]"), "Wrong password refused. 5 wrong attempts lock the email for 15 minutes.", "right", dim=False, width=360)
        await sleep(2.5)
        await d.clear()
        await page.get_by_label("Password", exact=True).fill("")
        await d.type(page.get_by_label("Password", exact=True), ADMIN[2], 60)
    await d.caption("")
    await d.click(page.get_by_role("button", name="Sign in"), 0.3)
    await page.get_by_text("Saved this week").wait_for()
    await sleep(0.8)

    await d.card("STEP 9", "Exports", "PDF, Excel and CSV from every page. Every download is recorded.")
    async with say("s9", 1.0):
        pass
    await d.uncard()
    async with say("export"):
        await d.click(page.get_by_role("button", name="Export"), 0.7)
        await d.focus(page.get_by_role("menu"), "Full report, daily summary, price per machine.", "left", dim=False)
        async with page.expect_download() as info:
            await d.clear()
            await d.click(page.get_by_role("menuitem", name="PDF (.pdf)").first, 0.3)
        download = await info.value
        target = WORK / "downloads" / download.suggested_filename
        target.parent.mkdir(exist_ok=True)
        await download.save_as(target)
        await sleep(0.8)
        toast = page.get_by_text("Downloaded").first
        await d.focus(toast, "", dim=False)
    await d.clear()
    pdf = pypdfium2.PdfDocument(str(target))
    for p in pdf:
        img = p.render(scale=2.2).to_pil()
        buf = BytesIO()
        img.save(buf, "PNG")
        report_pages.append(buf.getvalue())
    await page.route("**/__report**", route_report)
    await d.goto("/__report")
    async with say("report"):
        total = await page.evaluate("document.body.scrollHeight - innerHeight")
        steps = 6
        for i in range(1, steps + 1):
            await d.scroll_to(total * i / steps)
            await sleep(1.4)

    await d.goto("/")
    await d.nav("Audit log")
    await d.card("STEP 10", "The audit log", "Who did what, when, and from where.")
    async with say("s10", 1.0):
        pass
    await d.uncard()
    table = page.locator("div.rounded-xl", has=page.locator("table")).last
    async with say("audit"):
        await d.focus(table, "Every sign-in, account change, data switch, planning run, export and email.", "top", width=380)
    async with say("audit_detail"):
        await d.clear()
        run_row = page.locator("tr", has=page.get_by_text("plan.run", exact=True)).first
        await d.click(run_row, 1.0)
        detail = run_row.locator("xpath=following-sibling::tr[1]")
        await d.reveal(run_row, "start")
        await d.focus_rect(union(await run_row.bounding_box(), await detail.bounding_box()), "Cost, savings, trigger and data sources of this run.", "top", dim=False)
    async with say("audit_filter"):
        await d.clear()
        await d.scroll_to(0)
        outcome = page.get_by_label("Outcome")
        await d.focus(outcome, "Only failures.", "bottom", dim=False)
        await d.clear()
        await d.click(outcome, 0.6)
        await d.click(page.get_by_role("option", name="Failure"), 1.4)
        await d.focus(page.locator("tbody tr").first, "The wrong password from a minute ago.", "bottom", dim=False)
        await sleep(2.0)
        await d.focus(page.get_by_role("button", name="Export filtered"), "Export exactly what you filtered.", "left", dim=False)
    await d.clear()

    await d.nav("Units & terms")
    async with say("guide"):
        await d.focus(page.get_by_role("heading", name="Units & terms"), "Every unit, label and chart symbol, with examples.", "right", dim=False)
        await sleep(2.5)
        await d.clear()
        await d.type(page.get_by_label("Search units and terms"), "peak", 120)
        await sleep(2.0)
    other = "dark" if THEME == "light" else "light"
    async with say(other):
        await d.nav("Overview")
        await d.click(page.get_by_role("button", name=f"Switch to {other} mode").first, 0.8)
        await sleep(1.0)
        await d.scroll_to(600)
        await sleep(1.2)
        await d.scroll_to(0)
    await d.card("", "GridShift", "Lower energy cost · More of your own solar and wind · No new peaks · Every quota and deadline met", True)
    async with say("outro", 2.5):
        pass


async def main() -> None:
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--hide-scrollbars", "--font-render-hinting=none"])
        context = await browser.new_context(viewport=VIEW, device_scale_factor=SCALE, accept_downloads=True, locale="en-GB", timezone_id="Europe/Berlin", color_scheme="light")
        await context.add_init_script(path=str(HERE / "overlay.js"))
        await context.add_init_script(f"try {{ if (!sessionStorage.getItem('demo-theme')) {{ localStorage.setItem('gridshift-theme', '{THEME}'); sessionStorage.setItem('demo-theme', '1') }} }} catch (e) {{}}")
        page = await context.new_page()
        page.set_default_timeout(30000)
        cdp = await context.new_cdp_session(page)
        last = {"t": 0.0}

        def on_frame(params):
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]}))
            stamp = params["metadata"].get("timestamp") or now()
            if stamp <= last["t"]:
                return
            last["t"] = stamp
            name = f"{len(frames):06d}.jpg"
            (FRAMES / name).write_bytes(base64.b64decode(params["data"]))
            frames.append((stamp, name))

        cdp.on("Page.screencastFrame", on_frame)
        d = Director(page, cdp)
        await page.goto(BASE + "/", wait_until="networkidle")
        await page.get_by_role("button", name="Create admin account").wait_for()
        try:
            await story(d)
        finally:
            end = now()
            await sleep(0.3)
            (WORK / "timeline.json").write_text(json.dumps({"frames": frames, "marks": marks, "end": end}), encoding="utf-8")
            await page.screenshot(path=str(WORK / "last.png"))
            await browser.close()
    print(f"{len(frames)} frames, {end - frames[0][0]:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
