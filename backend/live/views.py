"""The live stream: one long-lived request per open browser tab (Server-Sent Events).

The browser sends its login token in the Authorization header, so the stream is read with `fetch`
(see frontend/src/live/stream.ts). It needs an ASGI server such as uvicorn (`make run` uses it).
"""
import json

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, User
from live.bus import get_bus


async def _user_for(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        token = AccessToken(header[7:])
        return await User.objects.aget(pk=token["user_id"], is_active=True)
    except (TokenError, User.DoesNotExist, KeyError):
        return None


def visible_to(user, event: dict) -> bool:
    """Who may receive an event. Founder-level role alerts also reach the founder; personal ones do not."""
    audience = event.get("audience")
    if not audience:
        return True
    if user.id in audience.get("users", []):
        return True
    roles = audience.get("roles", [])
    return bool(roles) and (user.role == Role.FOUNDER or user.role in roles)


def _frame(event: dict) -> str:
    body = {k: event[k] for k in ("id", "type", "data", "at")}
    return f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(body, default=str)}\n\n"


async def stream(request):
    user = await _user_for(request)
    if user is None:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    try:
        last_id = int(request.headers.get("Last-Event-ID") or 0)
    except ValueError:
        last_id = 0

    async def body():
        yield "retry: 3000\n\n: connected\n\n"
        async for event in get_bus().listen(after_id=last_id):
            if event is None:
                yield ": keep-alive\n\n"  # stops proxies and browsers closing an idle connection
            elif visible_to(user, event):
                yield _frame(event)

    response = StreamingHttpResponse(body(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # tells nginx not to hold the events back
    return response
