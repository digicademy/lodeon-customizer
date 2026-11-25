"""Bounded in-memory model connections for one locally configured instance."""

import secrets
import threading
import time
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Grant:
    origin: str
    models_allowed: bool
    profiles: frozenset
    ends: float
    connection: str = field(default_factory=lambda: uuid4().hex)
    instance_models: dict | None = None
    used: set = field(default_factory=set)
    cancelled: set = field(default_factory=set)


class Grants:
    def __init__(self, origin, profiles, *, calls=1024, tokens=2**31, lifetime=86400):
        self.lock = threading.RLock()
        self.origin = origin
        self.profiles = frozenset(profiles)
        self.calls = calls
        self.tokens = tokens
        self.lifetime = lifetime
        self.active = {}

    def permits_origin(self, origin):
        return self.origin is not None and self.origin == origin

    def connect(self, origin, *, models):
        with self.lock:
            if not self.permits_origin(origin):
                raise ValueError("denied")
            now = time.monotonic()
            self.active = {k: v for k, v in self.active.items() if v.ends > now}
            if len(self.active) >= 32 or (models and (self.calls <= 0 or self.tokens <= 0)):
                raise ValueError("busy")
            token = secrets.token_urlsafe(32)
            grant = Grant(origin, models, self.profiles if models else frozenset(), now + self.lifetime)
            self.active[token] = grant
            return {"grant": token, "connectionId": grant.connection, "expiresInSeconds": self.lifetime}

    def get(self, origin, token):
        with self.lock:
            grant = self.active.get(token)
            if not grant or grant.ends <= time.monotonic() or grant.origin != origin:
                raise ValueError("denied")
            return grant

    def share_models(self, origin, token, models):
        with self.lock:
            self.get(origin, token).instance_models = models

    def connected(self):
        with self.lock:
            now = time.monotonic()
            return any(grant.ends > now for grant in self.active.values())

    def visible_models(self):
        with self.lock:
            for grant in reversed(self.active.values()):
                if grant.ends > time.monotonic() and grant.instance_models is not None:
                    return grant.instance_models
        return {}

    def revoke(self, connection):
        with self.lock:
            for token, grant in self.active.items():
                if grant.connection == connection:
                    del self.active[token]
                    return
            raise ValueError("denied")

    def close(self):
        with self.lock:
            self.origin = None
            self.active.clear()

    def claim(self, origin, token, payload, max_tokens=None):
        with self.lock:
            grant = self.get(origin, token)
            if grant.connection != payload["connectionId"]:
                raise ValueError("denied")
            key = (payload["operationId"], payload["callId"])
            if max_tokens is None:
                if key not in grant.used and key not in grant.cancelled:
                    if not self.calls:
                        raise ValueError("busy")
                    self.calls -= 1
                grant.cancelled.add(key)
            else:
                if key in grant.used or key in grant.cancelled:
                    raise ValueError("conflict")
                if not self.calls or max_tokens > self.tokens:
                    raise ValueError("busy")
                self.calls -= 1
                self.tokens -= max_tokens
                grant.used.add(key)
            return grant
