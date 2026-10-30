"""Narration lines for every beat of the GridShift demo video."""


def eur(v: float) -> str:
    return f"{round(v):,} euros"


def mw(kw: float) -> str:
    return f"{kw / 1000:.1f} megawatts"


def lines(n: dict) -> dict[str, str]:
    """Return narration text per beat id, filled with figures from the pre-run plan."""
    pct = round(n["savings_pct"] * 100)
    return {
        "intro": "This is GridShift. It plans when a plant's heavy machines should run, when to charge its battery, and when to use its own solar and wind, so the plant pays as little as possible for electricity. We'll use the built-in sample: an illustrative cement plant, modelled on the size of a Holcim works in northern Germany. Let's start from the very first launch.",
        "s1": "Step one. First start.",
        "setup": "The very first time GridShift opens, it asks for the admin account. This only works on the computer where GridShift is installed, so nobody else can take over a new installation.",
        "setup_pw": "The password rules are checked as you type, and passwords are stored as a secure hash, never as plain text.",
        "s2": "Step two. The first plan.",
        "empty": "The top bar shows the site, that sample data is switched on, and the time in Germany, where the power market runs. There's no plan yet, so let's create one.",
        "run": "With one click, GridShift fetches the German day-ahead electricity prices, a seven-day weather forecast for the site, and the plant's load history. Then an optimizer finds the cheapest schedule that still meets every machine's quota and deadline, and keeps the grid draw under this year's peak. It takes a few seconds.",
        "s3": "Step three. The overview.",
        "coverage": "First, which prices are real. Today and tomorrow use published market prices. The days after are estimated from the weather, and the plan says exactly when the next prices come out.",
        "stats": f"Here's the week at a glance. Compared with simply running every machine as early as possible, this plan saves {eur(n['savings_eur'])} this week. That's {pct} percent off the energy bill. And {round(n['renewable_share'] * 100)} percent of the energy comes from the site's own solar and wind.",
        "peak": f"New in this version: peak charge protection. The grid operator bills the year's highest fifteen-minute draw, at {round(n['peak_rate'])} euros per kilowatt. GridShift reads the record from the plant's meter data, and plans the whole week to stay under it.",
        "chart": "This chart compares the daily cost of the GridShift plan with the run-as-needed baseline, day by day.",
        "tomorrow": "Tomorrow's card gives the plant manager what matters most: the planned cost, the average grid price, a short outlook, what the battery will do, and where every input came from.",
        "outlook": "The seven-day outlook flags strong or weak solar and wind, cheap or expensive grid days, and when flexible jobs are moved to better days.",
        "machines": f"And here is the payoff per machine. The special cement order pays about {round(n['order'])} euros per megawatt hour instead of {round(n['order_base'])}, because GridShift moves it into the cheapest hours before its deadline.",
        "s4": "Step four. The forecast.",
        "price": "The forecast page shows the hourly detail. The white line marks now. Grey is already past, solid orange is the published price, and dashed orange is the estimate. The blue line marks when the next day's prices are published.",
        "weather": "Two more tabs show the weather behind the plan: sunlight on the panels with cloud cover, and wind speed at the turbine's hub height.",
        "energy": "Here is on-site solar and wind against the planned plant load. The red line is this year's peak record. The planned grid draw stays at or below it all week.",
        "battery": "And the battery. It charges from surplus renewables or in cheap hours, and discharges at the expensive peaks.",
        "s5": "Step five. The machine schedule.",
        "gantt": "The schedule shows when every flexible machine runs. The strip at the top is the grid price, from cheap in green to expensive in red, with on-site solar and wind underneath.",
        "hover": "Hover any block to see why it was placed there. For example, its average price against the day's average.",
        "baseline": "Switch to run-as-needed to see the naive schedule. Every machine starts as early as it can, whatever the price.",
        "blocks": "Below, every run block is listed by day, in German time, with its reason.",
        "s6": "Step six. Site and machines.",
        "site": "This is the plant the planner works with. The peak charge card with the meter data, then the solar array, the wind turbine, the battery, and the grid connection with its fees.",
        "machines_cfg": "Each machine has a power rating and a rule. Always on, a daily quota of hours, or a deadline job, with a shortest run once it starts.",
        "own": "To plan for a real plant, an admin switches sample data off. GridShift then walks through three steps: the site details, the machines, and at least a week of load history. Meter data from the grid operator is optional, and sets the peak record. Everything is entered right here in the dashboard. No files to edit.",
        "back": "We'll switch back to the sample for the rest of the tour.",
        "s7": "Step seven. The daily email.",
        "email": "Every afternoon, once the next day's prices are published, GridShift re-plans and emails the plant team. This is the preview of exactly what they receive.",
        "replan": "Planners can also re-plan at any moment, for example after a forecast changes.",
        "job": "Meanwhile, the scheduled daily job runs on the server, and sends the plan by email.",
        "inbox": "Here it is in the energy manager's inbox. Tomorrow's machine blocks, the battery plan, the expected cost and savings, and any alerts right at the top.",
        "s8": "Step eight. Users and access.",
        "roles": "GridShift has three roles. Admins can do everything. Planners can re-plan and export. Viewers can look and export.",
        "invite": "Let's invite Anna, the shift planner. Her role decides what she can see and change.",
        "invite_mail": "Anna gets an invitation with a single-use link. It's valid for seven days.",
        "accept": "She chooses her own name and password. Nobody else ever knows it.",
        "anna": "As a planner, Anna sees every plan and can re-plan, but the admin pages are hidden from her.",
        "login": "Back to Sharan, the admin. A wrong password is refused, and five wrong attempts lock that email for fifteen minutes.",
        "s9": "Step nine. Exports.",
        "export": "Every page can be exported. The full plan report comes as a designed PDF, or as an Excel workbook.",
        "report": "Headline figures, the daily cost chart, the week's outlook, the machines and the full schedule. Ready to forward to management.",
        "s10": "Step ten. The audit log.",
        "audit": "The audit log records who did what, when, and from where. Sign-ins and failed attempts, invitations, data switches, planning runs with their savings, exports and emails.",
        "audit_detail": "Open any entry to see the full detail. Here, a planning run with its cost, its savings and its data sources.",
        "audit_filter": "Filter by activity, user, outcome or date. Here are only the failures, including that wrong password. And the filtered list can be exported too.",
        "guide": "If a unit or a chart symbol is ever unclear, the units and terms page explains every one of them, with examples. And it's searchable.",
        "light": "The dashboard is built dark for the control room, and there's a light mode for the office.",
        "dark": "And for the control room, there's a dark mode, built for screens that stay on all day.",
        "outro": "GridShift. Lower energy bills, more of your own solar and wind, no new peak charges, and every quota and deadline met. Ready to run on your plant's data.",
    }
