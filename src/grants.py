"""Short-lived local authority for the personal models capability."""

import secrets
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from uuid import uuid4


def exact_origin(origin):
    if not isinstance(origin, str) or len(origin) > 512 or not origin.isascii():
        raise ValueError("invalid_request")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(c.isspace() or ord(c) < 32 or c in "\\*%" for c in origin)
        or origin != f"https://{parsed.netloc}"
        or parsed.port == 443
    ):
        raise ValueError("invalid_request")
    return origin


@dataclass
class Grant:
    origin: str
    profiles: frozenset
    calls: int
    tokens: int
    ends: float
    lifetime: int
    connection: str = field(default_factory=lambda: uuid4().hex)
    used: set = field(default_factory=set)
    cancelled: set = field(default_factory=set)


class Grants:
    def __init__(self):
        self.lock = threading.RLock()
        self.tickets = {}
        self.active = {}

    def _purge(self):
        for entries in (self.tickets, self.active):
            for token in [key for key, grant in entries.items() if grant.ends <= time.monotonic()]:
                del entries[token]

    def issue(self, origin, profiles, calls, tokens, lifetime):
        exact_origin(origin)
        if not (0 < calls <= 1024 and 0 < tokens <= 2**31 and 0 < lifetime <= 86400):
            raise ValueError("invalid_request")
        with self.lock:
            self._purge()
            if len(self.tickets) + len(self.active) >= 32:
                raise ValueError("busy")
            ticket = secrets.token_urlsafe(32)
            self.tickets[ticket] = Grant(
                origin,
                frozenset(profiles),
                calls,
                tokens,
                time.monotonic() + min(120, lifetime),
                lifetime,
            )
            return ticket

    def permits_origin(self, origin):
        with self.lock:
            self._purge()
            return any(
                g.origin == origin
                for entries in (self.tickets, self.active)
                for g in entries.values()
            )

    def pair(self, origin, ticket):
        with self.lock:
            self._purge()
            grant = self.tickets.get(ticket)
            if not grant or grant.origin != origin:
                raise ValueError("denied")
            del self.tickets[ticket]
            token = secrets.token_urlsafe(32)
            grant.ends = time.monotonic() + grant.lifetime
            self.active[token] = grant
            return {
                "grant": token,
                "connectionId": grant.connection,
                "expiresInSeconds": grant.lifetime,
            }

    def get(self, origin, token):
        with self.lock:
            self._purge()
            grant = self.active.get(token)
            if not grant or grant.origin != origin:
                raise ValueError("denied")
            return grant

    def revoke(self, connection):
        with self.lock:
            for entries in (self.active, self.tickets):
                for token, grant in list(entries.items()):
                    if grant.connection == connection:
                        del entries[token]
                        return
            raise ValueError("denied")

    def claim(self, origin, token, payload, max_tokens=None):
        with self.lock:
            grant = self.get(origin, token)
            if grant.connection != payload["connectionId"]:
                raise ValueError("denied")
            key = (payload["operationId"], payload["callId"])
            if max_tokens is None:
                if key not in grant.used and key not in grant.cancelled:
                    if not grant.calls:
                        raise ValueError("busy")
                    grant.calls -= 1
                grant.cancelled.add(key)
            else:
                if key in grant.used or key in grant.cancelled:
                    raise ValueError("conflict")
                if not grant.calls or max_tokens > grant.tokens:
                    raise ValueError("busy")
                grant.calls -= 1
                grant.tokens -= max_tokens
                grant.used.add(key)
            return grant
