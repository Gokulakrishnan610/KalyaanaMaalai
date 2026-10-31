"""Who may do what. The founder can do everything; other roles are listed per view.

    permission_classes = [allow_roles(Role.PLANNER)]   # planners and the founder
    permission_classes = [allow_roles()]               # founder only
"""
from rest_framework.permissions import BasePermission

from accounts.models import Role


def allow_roles(*roles):
    allowed = {Role.FOUNDER, *roles}

    class AllowRoles(BasePermission):
        message = "You do not have permission to do this."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.role in allowed)

    return AllowRoles
