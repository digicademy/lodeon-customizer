"""Loopback listener for local settings and the origin-bound model capability."""

import json
import os
import socket
from threading import RLock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lodeon_model_runtime.wire import validate_payload
from .desktop import local_action, page
from .execution import execute_model
from .grants import Grants


ROUTES = {
    "connect": "POST",
    "catalog": "GET",
    "targets": "GET",
    "broker": "POST",
    "invoke": "POST",
    "cancel": "POST",
    "disconnect": "POST",
}
BODY = {"broker", "invoke", "cancel"}
STATUS = {
    "denied": 403,
    "invalid_request": 400,
    "conflict": 409,
    "routing_prompt_unavailable": 409,
    "closed": 410,
    "busy": 429,
    "unsupported_version": 404,
}
IDS = {"operationId", "connectionId", "callId"}
TASKS = {"plan", "query", "retry", "propose", "answer", "probe", "suggest", "route"}


def _closed(value, required, optional=()):
    if not isinstance(value, dict) or not required <= value.keys() <= required.union(optional):
        raise ValueError("invalid_request")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _messages(messages, tools):
    if not isinstance(messages, list) or not messages or not isinstance(tools, list):
        raise ValueError("invalid_request")
    for msg in messages:
        _closed(msg, {"role", "content"}, {"name", "tool_calls", "tool_call_id"})
        if msg["role"] not in ("system", "assistant", "user", "tool"):
            raise ValueError("invalid_request")
        if not isinstance(msg["content"], str):
            # A hosted page cannot ask the local adapter to resolve files or URLs.
            if not isinstance(msg["content"], list):
                raise ValueError("invalid_request")
            for block in msg["content"]:
                _closed(block, {"type", "text"})
                if block["type"] != "text" or not isinstance(block["text"], str):
                    raise ValueError("invalid_request")
        for key in ("name", "tool_call_id"):
            if key in msg and not _text(msg[key]):
                raise ValueError("invalid_request")
        if "tool_calls" in msg and not isinstance(msg["tool_calls"], list):
            raise ValueError("invalid_request")
        for call in msg.get("tool_calls", []):
            _closed(call, {"type", "id", "function"})
            _closed(call["function"], {"name", "arguments"})
            if (
                call["type"] != "function"
                or not _text(call["id"])
                or not _text(call["function"]["name"])
                or not isinstance(call["function"]["arguments"], str)
            ):
                raise ValueError("invalid_request")
    for tool in tools:
        _closed(tool, {"type", "function"})
        _closed(tool["function"], {"name", "parameters"}, {"description", "strict"})
        if (
            tool["type"] != "function"
            or not _text(tool["function"]["name"])
            or not isinstance(tool["function"]["parameters"], dict)
            or not isinstance(tool["function"].get("description", ""), str)
            or not isinstance(tool["function"].get("strict", False), bool)
        ):
            raise ValueError("invalid_request")


class ModelService(ThreadingHTTPServer):
    allow_reuse_address = os.name != "nt"
    allow_reuse_port = False

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, models, *, data=None, identity=None):
        self.data = data
        self.identity = identity
        self.settings_lock = RLock()
        self.set_models(models)
        super().__init__(address, ModelHandler)
        self.hosts = {f"127.0.0.1:{self.server_port}", f"localhost:{self.server_port}"}

    def set_models(self, models):
        if hasattr(self, "grants"):
            self.grants.close()
        self.models = models
        self.grants = Grants(models.origin, set(models.profile_ids) | set(models.brokers))


class ModelHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        pass

    def _reply(self, status, value=None, *, origin=None, extra=()):
        body = b"" if value is None else json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self, route):
        sizes = self.headers.get_all("Content-Length", [])
        if "Transfer-Encoding" in self.headers or len(sizes) > 1:
            raise ValueError("invalid_request")
        length = sizes[0] if sizes else "0"
        if not length.isascii() or not length.isdecimal() or len(length) > 8:
            raise ValueError("invalid_request")
        size = int(length)
        if route not in BODY or self.command == "OPTIONS":
            if size:
                raise ValueError("invalid_request")
            return None
        if not 0 < size <= 2_097_152 or self.headers.get_content_type() != "application/json":
            raise ValueError("invalid_request")
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def _handle(self):
        origin = None
        try:
            if (
                len(self.headers.get_all("Host", [])) != 1
                or self.headers["Host"] not in self.server.hosts
            ):
                raise ValueError("denied")
            if self.command == "GET" and self.path == "/" and "Origin" not in self.headers:
                return page(self)
            if self.command == "POST" and self.path in ("/instance", "/quit"):
                return local_action(self)
            with self.server.settings_lock:
                grants, models = self.server.grants, self.server.models
            origin_header = self.headers.get("Origin")
            if len(
                self.headers.get_all("Origin", [])
            ) != 1 or not grants.permits_origin(origin_header):
                raise ValueError("denied")
            origin = origin_header
            route = self.path.removeprefix("/v1/")
            if not self.path.startswith("/v1/") or route not in ROUTES:
                raise ValueError("unsupported_version")
            if self.command == "OPTIONS":
                allowed_headers = (
                    {"authorization", "content-type"} if route in BODY else {"authorization"}
                )
                requested = {
                    v.strip().lower()
                    for v in self.headers.get("Access-Control-Request-Headers", "").split(",")
                    if v.strip()
                }
                if (
                    self.headers.get("Access-Control-Request-Method") != ROUTES[route]
                    or requested - allowed_headers
                ):
                    raise ValueError("denied")
                self._body(route)
                return self._reply(
                    204,
                    origin=origin,
                    extra=[
                        ("Access-Control-Allow-Methods", ROUTES[route]),
                        ("Access-Control-Allow-Headers", ", ".join(sorted(allowed_headers))),
                    ],
                )
            if self.command != ROUTES[route]:
                raise ValueError("invalid_request")
            if route == "connect":
                self._body(route)
                return self._reply(200, grants.connect(origin), origin=origin)
            auth = self.headers.get("Authorization", "")
            if len(self.headers.get_all("Authorization", [])) != 1 or not auth.startswith("Bearer "):
                raise ValueError("denied")
            token = auth[7:]
            grant = grants.get(origin, token)
            body = self._body(route)
            if route == "catalog":
                result = models.catalog(grant.profiles.intersection(models.profile_ids))
            elif route == "targets":
                result = models.targets(grant.profiles)
            elif route == "broker":
                _closed(body, {"revision", "target"})
                if body["revision"] != models.revision:
                    raise ValueError("conflict")
                result = models.selected_broker(body["target"], grant.profiles)
            elif route == "disconnect":
                grants.revoke(grant.connection)
                return self._reply(204, origin=origin)
            else:
                result = self._call(route, body, origin, token, grant, grants, models)
            return self._reply(204 if result is None else 200, result, origin=origin)
        except (ValueError, TypeError, RecursionError) as error:
            code = str(error) if str(error) in STATUS else "invalid_request"
            self._reply(STATUS[code], {"error": {"code": code}}, origin=origin)

    def _call(self, route, body, origin, token, grant, grants, models):
        fields = (
            set()
            if route == "cancel"
            else {"revision", "target", "generation", "bounds", "messages", "tools", "task"}
        )
        _closed(body, IDS | fields)
        if not all(_text(body[k]) and len(body[k]) <= 256 for k in IDS):
            raise ValueError("invalid_request")
        if route == "cancel":
            grants.claim(origin, token, body)
            return None
        validate_payload("target", body["target"])
        profile = body["target"]["profileId"]
        if (
            profile not in models.profile_ids
            or profile not in grant.profiles
            or body["target"] != models.target(profile)
        ):
            raise ValueError("denied")
        if models.revision != body["revision"]:
            raise ValueError("conflict")
        validate_payload("bounds", body["bounds"])
        validate_payload("generation", body["generation"])
        _messages(body["messages"], body["tools"])
        if body["task"] not in TASKS:
            raise ValueError("invalid_request")
        grants.claim(origin, token, body, body["bounds"]["maxOutputTokens"])
        result = execute_model(
            models,
            profile,
            operation_id=body["operationId"],
            connection_id=grant.connection,
            call_id=body["callId"],
            **{k: body[k] for k in ("messages", "tools", "bounds", "generation")},
        )
        with grants.lock:
            grants.get(origin, token)
            if (body["operationId"], body["callId"]) in grant.cancelled:
                raise ValueError("closed")
        return result

    do_GET = do_POST = do_OPTIONS = _handle
