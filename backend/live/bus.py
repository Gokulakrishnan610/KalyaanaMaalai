"""The event bus behind live updates.

Anything that happens (a task moves, a vendor arrives, a payment is recorded) is published here as a small
event. Every open browser reads the events through the stream in live/views.py (Server-Sent Events).

- Production and development: Redis. `publish` is one fast Redis command, so it never slows a request down.
- Tests: an in-memory list, so no Redis is needed (LIVE_BACKEND=memory).
- If Redis is down, `publish` logs a warning and carries on: a live update is never worth failing a save.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import redis
import redis.asyncio as aredis
from django.conf import settings

logger = logging.getLogger(__name__)

CHANNEL = "live:events"
RECENT = "live:recent"  # the last few events, so a browser that reconnects can catch up
SEQUENCE = "live:seq"
KEEP_RECENT = 200
_last_warning = 0.0


class MemoryBus:
    """Used by the tests. Keeps every published event in `events`."""

    def __init__(self):
        self.events: list[dict] = []

    def publish(self, event: dict) -> dict:
        event["id"] = len(self.events) + 1
        self.events.append(event)
        return event

    async def listen(self, after_id: int = 0):
        seen = after_id
        while True:
            fresh = [e for e in self.events if e["id"] > seen]
            for event in fresh:
                seen = event["id"]
                yield event
            if not fresh:
                yield None
                await asyncio.sleep(0.05)


class RedisBus:
    def __init__(self, url: str):
        self.url = url
        self._sync = None

    def _client(self):
        if self._sync is None:
            self._sync = redis.Redis.from_url(self.url, socket_connect_timeout=0.3, socket_timeout=0.5)
        return self._sync

    def publish(self, event: dict) -> dict:
        client = self._client()
        event["id"] = client.incr(SEQUENCE)
        payload = json.dumps(event, default=str)
        pipe = client.pipeline(transaction=False)
        pipe.lpush(RECENT, payload)
        pipe.ltrim(RECENT, 0, KEEP_RECENT - 1)
        pipe.publish(CHANNEL, payload)
        pipe.execute()
        return event

    async def listen(self, after_id: int = 0):
        """Yields events as they arrive, or None every ~15 seconds (so the stream can send a keep-alive)."""
        client = aredis.Redis.from_url(self.url)
        pubsub = client.pubsub()
        await pubsub.subscribe(CHANNEL)  # subscribe first, then replay, so nothing is missed in between
        try:
            seen = after_id
            if after_id:
                missed = [json.loads(raw) for raw in await client.lrange(RECENT, 0, -1)]
                for event in sorted((e for e in missed if e["id"] > after_id), key=lambda e: e["id"]):
                    seen = event["id"]
                    yield event
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
                if message is None:
                    yield None
                    continue
                event = json.loads(message["data"])
                if event["id"] > seen:  # skip anything the replay already sent
                    seen = event["id"]
                    yield event
        finally:
            await pubsub.aclose()
            await client.aclose()


_bus = None


def get_bus():
    global _bus
    if _bus is None:
        _bus = MemoryBus() if settings.LIVE_BACKEND == "memory" else RedisBus(settings.REDIS_URL)
    return _bus


def publish(event_type: str, data: dict | None = None, audience: dict | None = None) -> dict | None:
    """Send an event to everyone who may see it.

    `audience` limits who: {"roles": ["PLANNER"]} (the founder always sees role events) or {"users": [3]}.
    Leave it out to send to every logged-in user.
    """
    event = {"type": event_type, "data": data or {}, "audience": audience,
             "at": datetime.now(timezone.utc).isoformat()}
    try:
        return get_bus().publish(event)
    except Exception as error:  # noqa: BLE001 - never fail a save because the live feed is down
        global _last_warning
        if time.monotonic() - _last_warning > 60:
            _last_warning = time.monotonic()
            logger.warning("Live update not sent (%s). Is Redis running?", type(error).__name__)
        return None
