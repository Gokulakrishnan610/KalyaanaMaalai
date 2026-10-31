"""Member 2's demo data on top of the Aarav & Meera wedding: venue, team, template tasks spread over the
board, a Sangeet run sheet and two vendor check-ins. Safe to run twice (everything is get_or_create)."""
from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from tasks.models import Stage, Task
from tasks.services import create_tasks_from_template
from vendors.models import Vendor, VendorCategory
from weddings.models import ScheduleItem, TeamMember, VendorArrival, Venue, Wedding, WeddingFunction

TEAM = [("planner@shaandaar.demo", "LEAD_PLANNER"), ("staff@shaandaar.demo", "COORDINATOR"),
        ("founder@shaandaar.demo", "VENDOR_LEAD")]

# time inside the Sangeet, title, who is responsible (email) -- two overlap on purpose to show the warning
SANGEET = [
    ((18, 0), (18, 45), "Guests arrive, welcome drinks", "staff@shaandaar.demo"),
    ((18, 45), (19, 30), "Sound check and stage ready", "planner@shaandaar.demo"),
    ((19, 30), (20, 30), "Family dance performances", "planner@shaandaar.demo"),
    ((20, 0), (20, 30), "Dinner counters open", "staff@shaandaar.demo"),
    ((20, 30), (22, 30), "DJ set and open dance floor", "planner@shaandaar.demo"),
    ((22, 30), (23, 0), "Last songs and send-off", "staff@shaandaar.demo"),
]


def _vendor(name, category):
    """Same vendors (and categories) that demo_data/vendors_and_quotations.py uses, so nothing is duplicated
    whichever file runs first."""
    category, _ = VendorCategory.objects.get_or_create(name=category)
    vendor, _ = Vendor.objects.get_or_create(name=name, defaults=dict(category=category, city="Jaipur"))
    return vendor


def load():
    wedding = Wedding.objects.filter(title="Aarav & Meera - Jaipur").first()
    if wedding is None:
        return  # the starter wedding was not loaded

    venue, _ = Venue.objects.get_or_create(name="Rambagh Lawns", city="Jaipur",
                                           defaults=dict(capacity=600, address="Bhawani Singh Road, Jaipur"))
    sangeet = WeddingFunction.objects.get(wedding=wedding, name="Sangeet")
    if sangeet.venue_id is None:
        sangeet.venue = venue
        sangeet.save(update_fields=["venue"])

    for email, role in TEAM:
        user = User.objects.filter(email=email).first()
        if user:
            TeamMember.objects.get_or_create(wedding=wedding, user=user, defaults=dict(role_label=role))
    # the starter file gave the planner an old free-text label; use the supported one
    TeamMember.objects.filter(wedding=wedding, user__email="planner@shaandaar.demo").exclude(
        role_label="LEAD_PLANNER").update(role_label="LEAD_PLANNER")

    created = create_tasks_from_template(wedding.id)
    if created:  # spread them over the board only the first time, so later runs do not undo the user's changes
        _spread_over_board(wedding)

    _schedule(sangeet)
    _checkins(wedding, sangeet)


def _spread_over_board(wedding):
    """Early tasks are done, the next few in progress or ready, the rest still to plan."""
    tasks = list(Task.objects.filter(wedding=wedding).exclude(title__in=["Finalise venue"]).order_by("due_date", "id"))
    columns = {Stage.TO_PLAN: [], Stage.IN_PROGRESS: [], Stage.READY: [], Stage.DONE: []}
    for index, task in enumerate(tasks):
        if index < 7:
            stage = Stage.DONE
        elif index < 12:
            stage = Stage.READY
        elif index < 18:
            stage = Stage.IN_PROGRESS
        else:
            stage = Stage.TO_PLAN
        columns[stage].append(task)
    for stage, members in columns.items():
        for position, task in enumerate(members):
            Task.objects.filter(pk=task.pk).update(stage=stage, position=position)


def _schedule(sangeet):
    day = timezone.localtime(sangeet.starts_at).date()
    for (sh, sm), (eh, em), title, email in SANGEET:
        starts = timezone.make_aware(timezone.datetime(day.year, day.month, day.day, sh, sm))
        ends = timezone.make_aware(timezone.datetime(day.year, day.month, day.day, eh, em))
        ScheduleItem.objects.get_or_create(
            function=sangeet, title=title,
            defaults=dict(starts_at=starts, ends_at=ends, responsible=User.objects.filter(email=email).first()))


def _checkins(wedding, sangeet):
    now = timezone.now()
    caterer = _vendor("Rasoi Royale", "Caterer")
    dj = _vendor("DJ Rhythm Raj", "DJ & Sound")
    # arrived on time
    VendorArrival.objects.get_or_create(
        wedding=wedding, vendor=caterer, function=sangeet,
        defaults=dict(expected_at=now - timedelta(hours=2), arrived_at=now - timedelta(hours=2, minutes=5),
                      status=VendorArrival.Status.ON_TIME, grace_minutes=15))
    # expected 40 minutes ago and has not turned up: the next run of `make jobs` marks it LATE and alerts once
    VendorArrival.objects.get_or_create(
        wedding=wedding, vendor=dj, function=sangeet,
        defaults=dict(expected_at=now - timedelta(minutes=40), grace_minutes=15))
