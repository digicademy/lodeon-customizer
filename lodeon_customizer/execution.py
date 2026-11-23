"""Execute one trusted local request and return a closed, credential-free result."""

import os

from lodeon_model_runtime.completion import read_completion
from lodeon_model_runtime.contracts import ModelMessage
from lodeon_model_runtime.errors import classify_litellm_error
from lodeon_model_runtime.wire import validate_payload

from .configuration import ConfigError
from .profiles import LocalModels


def _call_provider(kwargs):
    # This process owns personal calls. Keep LiteLLM's auxiliary cost lookup and logging local.
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    import litellm

    litellm.suppress_debug_info = True
    litellm.turn_off_message_logging = True
    return litellm.completion(**kwargs, num_retries=0)


def execute_model(
    models: LocalModels,
    profile_id: str,
    *,
    operation_id: str,
    connection_id: str,
    call_id: str,
    messages: list[ModelMessage],
    tools: list[dict],
    generation: dict,
    bounds: dict[str, int],
) -> dict:
    """Execute a prepared call locally. Only a validated terminal envelope may leave this boundary."""
    ids = {"operationId": operation_id, "connectionId": connection_id, "callId": call_id}
    if not all(isinstance(value, str) and value.strip() for value in ids.values()):
        raise ValueError("invalid_request")
    try:
        request = models.prepare(profile_id, generation, bounds, messages, tools)
    except ConfigError:
        return {**ids, "error": {"code": "assistant.model.unavailable"}}
    except (TypeError, ValueError, RecursionError) as error:
        code = str(error)
        if code not in {"conflict", "denied", "assistant.model.context_limit_exceeded"}:
            code = "invalid_request"
        return {**ids, "error": {"code": code}}

    try:
        response = _call_provider(request.kwargs)
    except Exception as error:
        return {**ids, "error": {"code": classify_litellm_error(error)}}

    try:
        parsed = read_completion(request.provider, response, reported_only=True)
        completion = {"content": parsed.content, "toolCalls": parsed.tool_calls}
        if parsed.finish_reason is not None:
            completion["finishReason"] = parsed.finish_reason
        if parsed.usage is not None:
            completion["usage"] = parsed.usage
        result = {**ids, "completion": completion}
        validate_payload("result", result)
        return result
    except (AttributeError, TypeError, ValueError, RecursionError, OverflowError):
        return {**ids, "error": {"code": "assistant.model.request_failed"}}
