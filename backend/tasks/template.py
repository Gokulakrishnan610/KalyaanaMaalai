"""The standard to-do list for a wedding. Plain Python data, no database.

`due_offset_days` is counted from the wedding's first day: negative = days before, 0 = the day itself,
positive = days after. `default_role` is a TeamMember.role_label; the task goes to whoever holds that role.
"""
from dataclasses import dataclass

LEAD_PLANNER = "LEAD_PLANNER"
COORDINATOR = "COORDINATOR"
DECOR_LEAD = "DECOR_LEAD"
VENDOR_LEAD = "VENDOR_LEAD"


@dataclass(frozen=True)
class TaskDraft:
    title: str
    description: str
    category: str
    due_offset_days: int
    priority: str  # LOW / MEDIUM / HIGH
    default_role: str


TEMPLATE: list[TaskDraft] = [
    TaskDraft("Finalize venue", "Confirm the venue, sign the contract and pay the booking advance.",
              "Venue", -150, "HIGH", LEAD_PLANNER),
    TaskDraft("Book caterer", "Shortlist caterers, compare quotes and book one.",
              "Catering", -140, "HIGH", VENDOR_LEAD),
    TaskDraft("Book decorator", "Choose the decorator and agree the theme and budget.",
              "Decor", -135, "HIGH", DECOR_LEAD),
    TaskDraft("Book DJ/sound", "Book the DJ and sound system for the sangeet and reception.",
              "Entertainment", -120, "MEDIUM", VENDOR_LEAD),
    TaskDraft("Hire photographer", "Book the photographer and agree the shot list and deliverables.",
              "Media", -130, "HIGH", VENDOR_LEAD),
    TaskDraft("Hire videographer", "Book the videographer and agree the film and highlights package.",
              "Media", -130, "MEDIUM", VENDOR_LEAD),
    TaskDraft("Book makeup artist", "Book bridal makeup and hair, including a trial.",
              "Beauty", -100, "MEDIUM", COORDINATOR),
    TaskDraft("Book mehendi artist", "Book the mehendi artists for the bride and family.",
              "Beauty", -90, "MEDIUM", COORDINATOR),
    TaskDraft("Design invitations", "Agree the invitation design, wording and languages.",
              "Invitations", -110, "MEDIUM", COORDINATOR),
    TaskDraft("Print invitations", "Approve the proof and print the invitations.",
              "Invitations", -80, "MEDIUM", COORDINATOR),
    TaskDraft("Send invitations", "Send printed and digital invitations to every guest.",
              "Invitations", -60, "HIGH", COORDINATOR),
    TaskDraft("Finalize guest list", "Lock the guest list with both families.",
              "Guests", -90, "HIGH", LEAD_PLANNER),
    TaskDraft("Track RSVPs", "Follow up with guests and keep the confirmed count up to date.",
              "Guests", -30, "MEDIUM", COORDINATOR),
    TaskDraft("Arrange guest accommodation", "Block hotel rooms and share the room list with guests.",
              "Logistics", -75, "HIGH", COORDINATOR),
    TaskDraft("Arrange transport and valet", "Book cars, shuttles and valet parking.",
              "Logistics", -45, "MEDIUM", COORDINATOR),
    TaskDraft("Obtain permits and licences", "Music, alcohol, fireworks and venue permits.",
              "Legal", -60, "HIGH", LEAD_PLANNER),
    TaskDraft("Finalize outfits", "Confirm outfits, fittings and alterations for the couple and families.",
              "Personal", -45, "LOW", COORDINATOR),
    TaskDraft("Confirm priest/pandit", "Confirm the priest, the muhurat and the list of puja items.",
              "Rituals", -100, "HIGH", LEAD_PLANNER),
    TaskDraft("Design stage and mandap", "Approve the stage, mandap and entrance designs.",
              "Decor", -75, "HIGH", DECOR_LEAD),
    TaskDraft("Arrange lighting", "Plan lighting for the venue, stage and entrance.",
              "Decor", -40, "MEDIUM", DECOR_LEAD),
    TaskDraft("Plan baraat arrangements", "Horse, band, dhol and route for the baraat.",
              "Rituals", -30, "MEDIUM", VENDOR_LEAD),
    TaskDraft("Arrange return gifts", "Choose, order and pack return gifts for guests.",
              "Guests", -35, "LOW", COORDINATOR),
    TaskDraft("Finalize playlist", "Agree the playlist and must-play / do-not-play songs with the DJ.",
              "Entertainment", -15, "LOW", COORDINATOR),
    TaskDraft("Conduct menu tasting", "Tasting with the family; lock the final menu.",
              "Catering", -50, "MEDIUM", VENDOR_LEAD),
    TaskDraft("Finalize seating plan", "Prepare the seating plan from the confirmed RSVPs.",
              "Guests", -10, "MEDIUM", COORDINATOR),
    TaskDraft("Prepare vendor payment schedule", "List every vendor's advance and balance with due dates.",
              "Finance", -45, "HIGH", LEAD_PLANNER),
    TaskDraft("Prepare emergency kit", "Safety pins, first aid, sewing kit, snacks, chargers and spares.",
              "Day-of", -2, "LOW", COORDINATOR),
    TaskDraft("Conduct day-of briefing", "Brief the team and vendors on the run sheet and who does what.",
              "Day-of", -1, "HIGH", LEAD_PLANNER),
    TaskDraft("Complete post-event settlement", "Settle vendor balances, extra-guest charges and return deposits.",
              "Finance", 7, "HIGH", LEAD_PLANNER),
    TaskDraft("Collect feedback", "Ask the family and vendors for feedback and ratings.",
              "Follow-up", 10, "LOW", COORDINATOR),
]
