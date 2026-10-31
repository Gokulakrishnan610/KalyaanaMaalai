"""Who may do what. The founder can do everything; other roles are listed per view.

    permission_classes = [allow_roles(Role.PLANNER)]   # planners and the founder
    permission_classes = [allow_roles()]               # founder only
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Role  # noqa: F401  (re-exported for views)


def allow_roles(*roles):
    allowed = {Role.FOUNDER, *roles}

    class AllowRoles(BasePermission):
        message = "You do not have permission to do this."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.role in allowed)

    return AllowRoles


def read_for_all_write_for(*roles):
    """Any logged-in user may look; only the listed roles (and the founder) may change things."""
    allowed = {Role.FOUNDER, *roles}

    class ReadForAllWriteFor(BasePermission):
        message = "You do not have permission to change this."

        def has_permission(self, request, view):
            user = request.user
            if not (user and user.is_authenticated):
                return False
            return request.method in SAFE_METHODS or user.role in allowed

    return ReadForAllWriteFor
