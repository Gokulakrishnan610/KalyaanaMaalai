"""Helpers for alerts that must reach certain roles."""
from accounts.models import Role, User
from notifications.services import notify


def notify_roles(message: str, roles=(Role.PLANNER,), severity: str = "info", key: str | None = None,
                 channel: str = "inapp") -> int:
    """Save one notification per planner (and the founder). Returns how many were created.

    The bell and the live toast come from the saved notification. With a `key`, each person gets each alert once.
    """
    created = 0
    users = User.objects.filter(role__in=[*roles, Role.FOUNDER], is_active=True)
    for index, user in enumerate(users):
        # only the first copy goes to Telegram, so a group chat is not told once per person
        copy_channel = channel if index == 0 else "inapp"
        if notify(message, channel=copy_channel, user_id=user.id, severity=severity,
                  dedupe_key=f"{key}:{user.id}" if key else None):
            created += 1
    return created
