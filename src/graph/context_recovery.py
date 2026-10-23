"""Recover oversized model requests without replaying tools or changing graph history.

This is reactive recovery for the shared orchestration/ReAct node factory. Custom
agent harnesses (including DeepAgents) manage their own model calls. Only explicit
provider context-overflow errors are eligible; other bad requests propagate.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
import openai
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    messages_to_dict,
)

_PROVIDER_BAD_REQUESTS = (openai.BadRequestError, anthropic.BadRequestError)
_PLAN_ROLES = {"planner_agent", "recruiter_agent", "evaluator_agent"}
_OVERFLOW_TEXT = re.compile(
    r"maximum context length|context (?:length|window)(?: limit)? (?:is )?exceeded"
    r"|exceeds? (?:the |this model.s )?(?:maximum )?context (?:length|window)"
    r"|(?:prompt|input) is too long",
    re.IGNORECASE,
)


def is_context_overflow(error: BaseException) -> bool:
    """Recognize context overflow without treating other provider 400s as recoverable."""
    if not isinstance(error, _PROVIDER_BAD_REQUESTS):
        return False
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        body = body.get("error", body)
    code = body.get("code") if isinstance(body, dict) else None
    if code == "context_length_exceeded" or getattr(error, "code", None) == (
        "context_length_exceeded"
    ):
        return True
    detail = body.get("message", "") if isinstance(body, dict) else ""
    return bool(_OVERFLOW_TEXT.search(f"{error} {detail}"))


def _request_size(messages: list[BaseMessage]) -> int:
    """Measure serialized characters to require progress, without claiming a token count."""
    return len(json.dumps(messages_to_dict(messages), ensure_ascii=False))


def _shorten_text(text: str) -> str:
    """Keep both ends of long output and explicitly mark the omitted middle."""
    if len(text) <= 1000:
        return text
    limit = max(1000, min(4000, len(text) // 2))
    notice = "\n[Middle omitted for context recovery; full content retained in the trace.]\n"
    head = (limit - len(notice)) // 2
    tail = limit - len(notice) - head
    return text[:head] + notice + text[-tail:]


def _shorten_content(content: str | list) -> str | list:
    """Shorten text only; preserve images and other structured content blocks."""
    if isinstance(content, str):
        return _shorten_text(content)
    result = []
    for block in content:
        if isinstance(block, str):
            result.append(_shorten_text(block))
        elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
            text = block.get("text")
            result.append({**block, "text": _shorten_text(text)} if isinstance(text, str)
                          else block)
        else:
            result.append(block)
    return result


def compact_context(messages: list[BaseMessage]) -> list[BaseMessage] | None:
    """Shorten execution history while protecting instructions and tool-call pairing.

    System and human messages, the latest final Planner/Recruiter/Evaluator outputs,
    and the last message (unless it is a tool result) remain verbatim. Older complete
    tool exchanges are removed as units, retaining the newest exchange. Long tool
    results and unprotected assistant text are excerpted. Tool arguments are never
    rewritten. Return None when nothing can safely be shortened.
    """
    protected = {
        i for i, message in enumerate(messages)
        if isinstance(message, (SystemMessage, HumanMessage))
    }
    for role in _PLAN_ROLES:
        finals = [i for i, message in enumerate(messages)
                  if isinstance(message, AIMessage) and message.name == role
                  and not message.tool_calls]
        if finals:
            protected.add(finals[-1])
    if messages and not isinstance(messages[-1], ToolMessage):
        protected.add(len(messages) - 1)

    # Collect only complete adjacent exchanges, including parallel tool calls.
    exchanges: list[list[int]] = []
    for i, message in enumerate(messages):
        if not isinstance(message, AIMessage) or not message.tool_calls:
            continue
        expected = [call["id"] for call in message.tool_calls]
        end = i + 1
        while end < len(messages) and isinstance(messages[end], ToolMessage):
            end += 1
        observed = [message.tool_call_id for message in messages[i + 1:end]]
        group = list(range(i, end))
        if sorted(expected) == sorted(observed) and not protected.intersection(group):
            exchanges.append(group)
    removable = exchanges[:-1]
    drop = {i for group in removable[:(len(removable) + 1) // 2] for i in group}

    result: list[BaseMessage] = []
    for i, message in enumerate(messages):
        if i in drop:
            if i == min(drop):
                result.append(HumanMessage(
                    content=("[Older completed tool exchanges omitted to fit the context window. "
                             "The full execution trace is retained; omitted outputs are not "
                             "included in this request.]"),
                    name="context_recovery",
                ))
            continue
        if i not in protected and (
            isinstance(message, ToolMessage)
            or (isinstance(message, AIMessage) and not message.tool_calls
                and not message.additional_kwargs.get("tool_calls"))
        ):
            message = message.model_copy(update={"content": _shorten_content(message.content)})
        result.append(message)

    return result if _request_size(result) < _request_size(messages) else None


def invoke_with_context_recovery(
    model: Any,
    messages: list[BaseMessage],
    *,
    node_name: str,
    max_retries: int = 2,
) -> Any:
    """Retry only the failed model call, with a shorter input, at most twice by default.

    No sleep is needed for context overflow. Existing provider-rate-limit wrappers
    still handle transient failures. Shared state and caller messages stay intact.
    If protected content cannot fit, or the retry budget is exhausted, propagate
    the provider error through the existing error handler.
    """
    current = list(messages)
    for attempt in range(max_retries + 1):
        try:
            return model.invoke(current)
        except _PROVIDER_BAD_REQUESTS as error:
            if not is_context_overflow(error) or attempt >= max_retries:
                raise
            shortened = compact_context(current)
            if shortened is None:
                logging.warning("%s: context overflow; protected input cannot be shortened",
                                node_name)
                raise
            logging.warning(
                "%s: context overflow; retry %d/%d with %d -> %d serialized characters",
                node_name, attempt + 1, max_retries, _request_size(current),
                _request_size(shortened),
            )
            current = shortened
    raise RuntimeError("Context recovery retry loop fell through")
