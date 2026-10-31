"""The offline checklist: used when AI is switched off (MOCK_EXTERNALS) or fails, so the demo never breaks.

It is tailored from the wedding itself: its functions, guest count, city and the vendors already chosen.
Each task is (title, description, category, days from the first wedding day, priority, function name or None).
"""

BASE = [
    ("Sign the planning agreement and collect the booking deposit", "Confirm the guest count, rate per extra guest and payment schedule in writing.", "Admin", -180, "HIGH"),
    ("Finalise the wedding budget with the couple", "Agree a budget per category and what happens when a category overruns.", "Budget", -175, "HIGH"),
    ("Confirm the wedding dates with the family priest", "Check muhurat timings for every ceremony and share them with the team.", "Rituals", -170, "HIGH"),
    ("Shortlist and visit venues", "Compare capacity, parking, power backup, rooms and sound-time restrictions.", "Venue", -165, "HIGH"),
    ("Book the venue and sign the contract", "Get the cancellation terms and payment dates in writing.", "Venue", -150, "HIGH"),
    ("Request three caterer quotations", "Send the same menu brief to each caterer so the quotes can be compared.", "Catering", -140, "HIGH"),
    ("Hold a menu tasting with the couple", "Note dietary needs: Jain, vegan, allergies and live counters.", "Catering", -120, "MEDIUM"),
    ("Book the decorator and approve the mood board", "Agree themes, florals, stage and mandap designs for each function.", "Decor", -130, "HIGH"),
    ("Book the photographer and videographer", "Share the shot list and confirm the second shooter and album delivery date.", "Photography", -125, "MEDIUM"),
    ("Book the DJ and sound team", "Confirm equipment, backup systems and the do-not-play list.", "Entertainment", -110, "MEDIUM"),
    ("Book makeup artists and hair stylists", "Schedule trials and timings for every function day.", "Beauty", -100, "MEDIUM"),
    ("Design and print the invitations", "Proof the wording, dates and venue map twice before printing.", "Invitations", -95, "MEDIUM"),
    ("Send save-the-dates and digital invitations", "Use the guest list to track who has been invited.", "Invitations", -90, "MEDIUM"),
    ("Finalise the guest list and collect RSVPs", "Keep a running count: it drives food, seating and extra-guest charges.", "Guests", -45, "HIGH"),
    ("Book accommodation for out-of-town guests", "Block rooms early and share check-in details with the family.", "Guests", -80, "MEDIUM"),
    ("Arrange guest and family transport", "Airport pickups, shuttles between venues and baraat vehicles.", "Logistics", -60, "MEDIUM"),
    ("Confirm all vendors in writing", "Send each vendor the final schedule, venue access time and contact person.", "Vendors", -30, "HIGH"),
    ("Collect advance payments due to vendors", "Check the payment plan and clear advances before the due dates.", "Finance", -30, "HIGH"),
    ("Prepare the run sheet for every function", "Minute-by-minute schedule with who is responsible for each item.", "Operations", -21, "HIGH"),
    ("Brief the on-ground team", "Share the run sheet, vendor arrival times and escalation contacts.", "Operations", -7, "HIGH"),
    ("Arrange the welcome kits for guests", "Include the schedule, local tips and helpline numbers.", "Guests", -14, "LOW"),
    ("Do a full venue walkthrough with the decorator and caterer", "Check power points, kitchen space, entry gates and load-in route.", "Venue", -10, "HIGH"),
    ("Pay final instalments to vendors", "Clear the final balance as agreed, and keep every receipt.", "Finance", -3, "HIGH"),
    ("Prepare a vendor tip and thank-you envelope list", "Cash envelopes for the helpers, drivers and venue staff.", "Finance", -5, "LOW"),
    ("Send the final bill and extra-guest invoice", "Compare the actual guest count with the contracted number and invoice any extras.", "Finance", 2, "MEDIUM"),
    ("Collect the final payment from the couple", "Follow up until every invoice is paid.", "Finance", 7, "HIGH"),
    ("Collect feedback and rate the vendors", "Record punctuality, quality and pricing while it is fresh.", "Vendors", 5, "LOW"),
]

BY_FUNCTION = {
    "mehendi": [
        ("Book the mehendi artists", "Allow one artist per 10 guests plus bridal artists.", "Entertainment", -90, "HIGH"),
        ("Plan the mehendi seating and cushions", "Low seating clusters near the artists, plus a rest area for elders.", "Decor", -40, "MEDIUM"),
        ("Order mehendi cones, snacks and chai counters", "Keep guests comfortable while they wait.", "Catering", -20, "LOW"),
    ],
    "sangeet": [
        ("Hire a choreographer and schedule rehearsals", "Plan family performances and share the song list.", "Entertainment", -60, "HIGH"),
        ("Hold a sound check and stage rehearsal", "Test mics, LED wall and the cue sheet on site.", "Entertainment", -2, "HIGH"),
    ],
    "reception": [
        ("Plan the reception stage, entry and receiving line", "Agree the couple entry, photo queue and gift handling.", "Operations", -25, "MEDIUM"),
        ("Arrange the cake, toast and speeches", "Confirm who speaks and the timing of each item.", "Operations", -20, "LOW"),
    ],
    "haldi": [
        ("Arrange haldi supplies and a changing area", "Turmeric paste, flowers, towels and a place to freshen up.", "Rituals", -15, "MEDIUM"),
    ],
    "wedding": [
        ("Coordinate the baraat and vidai logistics", "Horse, band, route permission and car decor.", "Operations", -20, "HIGH"),
    ],
    "engagement": [
        ("Order rings and prepare the exchange ceremony", "Confirm sizes and a safe handover.", "Rituals", -60, "MEDIUM"),
    ],
}

CROWD = [
    ("Plan crowd flow and entry gates", "Separate entries for guests, vendors and the family; add signage.", "Operations", -21, "HIGH"),
    ("Arrange parking and valet", "Estimate vehicles at about one per four guests and mark overflow parking.", "Logistics", -21, "HIGH"),
]
LARGE = [
    ("Hire security and crowd marshals", "Guest list checks at the gate and a lost-and-found desk.", "Operations", -14, "HIGH"),
    ("Arrange a medical desk and first-aid kit", "Include an ambulance contact for large gatherings.", "Operations", -14, "MEDIUM"),
]
OUTSTATION = [
    ("Plan city welcome and travel desk", "Hotel check-in help and a local guide for out-of-town guests.", "Guests", -20, "MEDIUM"),
    ("Check local permissions and noise-curfew timings", "Music, fireworks and baraat routes may need permits.", "Admin", -60, "MEDIUM"),
]


def _function_key(name: str) -> str | None:
    lowered = name.lower()
    return next((key for key in BY_FUNCTION if key in lowered), None)


def build_template(wedding, function_names: list[str], vendor_names: list[str]) -> list[dict]:
    """Returns task dicts (title, description, category, due_offset_days, priority, function_name)."""
    rows = [(*row, None) for row in BASE]
    seen_keys = set()
    for name in function_names:
        key = _function_key(name)
        if key and key not in seen_keys:
            seen_keys.add(key)
            rows += [(*row, name) for row in BY_FUNCTION[key]]
    guests = wedding.guest_count
    if guests >= 300:
        rows += [(*row, None) for row in CROWD]
    if guests >= 500:
        rows += [(*row, None) for row in LARGE]
    if wedding.city:
        rows += [(title.replace("city", wedding.city) if "city" in title else title, desc, cat, off, pri, None)
                 for title, desc, cat, off, pri in OUTSTATION]
    for vendor in vendor_names[:6]:
        rows.append((f"Confirm arrival time and contact person with {vendor}",
                     "Share the run sheet and agree the load-in slot.", "Vendors", -7, "HIGH", None))
    if len(function_names) > 2:
        rows.append((f"Plan outfit changes and travel between {len(function_names)} functions",
                     "Build buffer time between functions in the run sheet.", "Operations", -18, "MEDIUM", None))
    if wedding.budget_paise:
        budget = f"Rs {wedding.budget_paise // 100:,}"
        rows.append((f"Review spend against the {budget} budget every two weeks",
                     "Flag any category that is more than 10% over.", "Budget", -90, "MEDIUM", None))
    tasks = [{"title": t, "description": d, "category": c, "due_offset_days": o, "priority": p, "function_name": f}
             for t, d, c, o, p, f in rows]
    return tasks[:40]
